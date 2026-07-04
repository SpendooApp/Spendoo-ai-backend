import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from spendoo.core.llm_client import LLMClient
from spendoo.chatbot.models import ChatRequest, ChatResponse
from spendoo.chatbot.tools import AVAILABLE_TOOLS

class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_client = LLMClient()
        
        # Build the dynamic tools registry
        self.tool_instances = {tool.schema["function"]["name"]: tool for tool in AVAILABLE_TOOLS}
        self.tool_schemas = [tool.schema for tool in AVAILABLE_TOOLS]
        
    def process_chat(self, request: ChatRequest) -> ChatResponse:
        system_prompt = (
            "You are a helpful financial assistant for Spendoo. "
            "You have access to tools that can fetch the data that help you answer the user's questions. "
            f"The current year is {datetime.now().year}. If the user asks about 'this month' or 'last week', use relative ISO dates based on the current date: {datetime.now().date().isoformat()}. "
            "You must respond ONLY in a valid JSON object format with the following keys:\n"
            "1. \"response\": A plain text answer to the user. Do not use markdown like bolding, asterisks, or markdown tables. Use standard newlines (represented as the \\n character) for formatting.\n"
            "2. \"chatSummary\": A concise (1-3 sentences) updated summary of the conversation so far, incorporating the latest user message and your response.\n\n"
            "Do not use markdown formatting inside the \"response\" text. Provide plain text only."
        )

        messages = [{"role": "system", "content": system_prompt}]

        if request.chatSummary:
            messages.append({"role": "system", "content": f"Previous conversation summary: {request.chatSummary}"})

        messages.append({"role": "user", "content": request.message})

        # ── First call: tool selection ────────────────────────────────────────────
        llm_response = self.llm_client.chat_with_tools(
            messages=messages,
            tools=self.tool_schemas,
            json_mode=True
        )

        # ── Execute tools if requested ────────────────────────────────────────────
        if getattr(llm_response, "tool_calls", None):
            messages.append(llm_response)

            for tool_call in llm_response.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool = self.tool_instances.get(function_name)

                if tool:
                    try:
                        result_data = tool.execute(self.db, request.userId, **args)
                    except Exception as e:
                        result_data = f"Error executing tool: {str(e)}"
                else:
                    result_data = f"Error: Unknown function '{function_name}'"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result_data)
                })

        # ── Final synthesis: Gemini → gpt-4o-mini → gpt-oss-120b ─────────────────
        raw_content = self.llm_client.synthesize(messages)

        # ── Parse JSON response ───────────────────────────────────────────────────
        try:
            data = json.loads(raw_content)
            assistant_response = data.get("response", "")
            new_summary = data.get("chatSummary", "")
        except Exception:
            assistant_response = raw_content
            new_summary = request.chatSummary or ""

        return ChatResponse(response=assistant_response, chatSummary=new_summary)