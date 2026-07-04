# spendoo/core/llm_client.py

from openai import OpenAI, OpenAIError
from spendoo.core.config import settings

_github_token_idx = 0

class LLMClient:
    def __init__(self):
        self.groq_client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.fallback_model = "openai/gpt-oss-120b"
        
    def _get_github_client(self):
        tokens = settings.GITHUB_TOKENS
        if not tokens:
            raise ValueError("No GITHUB_TOKENS configured in environment.")
        
        token = tokens[_github_token_idx % len(tokens)]
        
        return OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=token
        )
        
    def _get_gemini_client(self):
        return OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
    def _advance_github_token(self):
        global _github_token_idx
        _github_token_idx += 1
        
    def _call_gemini_synthesis(self, messages: list) -> str:
        """
        Clean message conversion for Gemini synthesis call.
        Skips assistant/tool_call objects, handles None content.
        """
        system_parts  = []
        content_parts = []

        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content") or ""
            else:
                role = getattr(msg, "role", "")
                content = getattr(msg, "content", "") or ""

            if role == "assistant":
                continue                          # skip — has tool_calls, content=None
            elif role == "system" and content:
                system_parts.append(content)
            elif role == "user" and content:
                content_parts.append(content)
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "") if isinstance(msg, dict) else ""
                content_parts.append(f"Tool result [{tool_call_id}]: {content}")

        prompt = "\n\n".join(content_parts) or "Please provide a response."

        client = self._get_gemini_client()
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "\n".join(system_parts)},
                {"role": "user",   "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _execute_with_fallback(self, kwargs: dict, original_model: str, fallback_target: str):
        
        tokens = settings.GITHUB_TOKENS

        max_attempts = len(tokens) if tokens else 1
        kwargs["model"] = original_model

        for attempt in range(max_attempts):
            try:
                client   = self._get_github_client()
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message
            except OpenAIError as e:
                if attempt < max_attempts - 1:
                    self._advance_github_token()
                else:
                    break

        # ── Groq fallback ─────────────────────────────────────────────────────────
        kwargs["model"] = fallback_target

        # Strip everything Groq doesn't support
        for key in ("tools", "tool_choice", "response_format"):
            kwargs.pop(key, None)

        # Safely prepend reasoning prompt — handle both dict and object messages
        reasoning_prompt = "Use concise reasoning effort. Limit yourself to a maximum of 3 reasoning steps. "
        messages = kwargs.get("messages", [])

        # Normalize all messages to dicts first
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append(msg)
            else:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "") or ""
                if content:
                    normalized.append({"role": role, "content": content})

        if normalized and normalized[0].get("role") == "system":
            normalized[0]["content"] = reasoning_prompt + normalized[0]["content"]
        else:
            normalized.insert(0, {"role": "system", "content": reasoning_prompt})

        kwargs["messages"] = normalized

        response = self.groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message
    
    def generate(self, prompt: str, model: str, **kwargs):
        messages = [{"role": "user", "content": prompt}]
        merged_kwargs = {"messages": messages, **kwargs}
        if "max_output_tokens" in merged_kwargs:
            merged_kwargs["max_tokens"] = merged_kwargs.pop("max_output_tokens")
        message = self._execute_with_fallback(
            merged_kwargs, 
            original_model=model,
            fallback_target="openai/gpt-oss-120b" 
            )
        return message.content

    def chat_with_tools(self, messages: list, tools: list = None, model: str = "openai/gpt-4o-mini", json_mode: bool = False):
        kwargs = {
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        return self._execute_with_fallback(kwargs, original_model=model, fallback_target="openai/gpt-oss-120b")
        
    def synthesize(self, messages: list) -> str:
        """
        Final synthesis call — same cascade pattern as chat_with_tools.
        Gemini (Google) → gpt-4o-mini (GitHub) → gpt-oss-120b (Groq fallback)
        """
        # Step 1: Try Gemini with cleaned messages
        try:
            return self._call_gemini_synthesis(messages)
        except Exception:
            pass

        # Step 2: Try gpt-4o-mini on GitHub
        try:
            kwargs = {
                "messages": self._serialize_messages(messages),
                "response_format": {"type": "json_object"}
            }
            msg = self._execute_with_fallback(
                kwargs,
                original_model="openai/gpt-4o-mini",
                fallback_target="openai/gpt-oss-120b"
            )
            return msg.content
        except Exception as e:
            raise RuntimeError(f"All synthesis models failed. Last error: {e}")
        
    def _serialize_messages(self, messages: list) -> list:
        """
        Convert raw LLM response objects to plain dicts.
        Strips tool_call_id and converts tool messages to user messages
        so providers don't complain about orphaned tool results.
        """
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content") or ""

                if role == "assistant" and not content:
                    continue   

                if role == "tool":
                    serialized.append({
                        "role": "user",
                        "content": f"Tool result: {content}"
                    })
                else:
                    serialized.append({"role": role, "content": content})
            else:
                role = getattr(msg, "role", "assistant")
                content = getattr(msg, "content", "") or ""
                if content:
                    serialized.append({"role": role, "content": content})

        return serialized

