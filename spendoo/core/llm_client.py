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
        
    def _advance_github_token(self):
        global _github_token_idx
        _github_token_idx += 1

    def _execute_with_fallback(self, kwargs: dict, original_model: str):
        tokens = settings.GITHUB_TOKENS
        max_attempts = len(tokens) if tokens else 1
        
        kwargs["model"] = original_model
        
        # Try GitHub models first
        for attempt in range(max_attempts):
            try:
                gh_client = self._get_github_client()
                response = gh_client.chat.completions.create(**kwargs)
                return response.choices[0].message
            except OpenAIError:
                if attempt < max_attempts - 1:
                    self._advance_github_token()
                else:
                    break
                    
        # Fallback to Groq / OSS
        kwargs["model"] = self.fallback_model
        
        # Groq doesn't support json mode combined with tools
        if "tools" in kwargs and "response_format" in kwargs:
            del kwargs["response_format"]
        
        reasoning_prompt = "Use concise reasoning effort. Limit yourself to a maximum of 3 reasoning steps before executing a tool. "
        messages = kwargs.get("messages", [])
        if messages:
            if messages[0].get("role") == "system":
                messages[0]["content"] = reasoning_prompt + messages[0]["content"]
            else:
                messages.insert(0, {"role": "system", "content": reasoning_prompt})
        kwargs["messages"] = messages
        
        response = self.groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def generate(self, prompt: str, model: str, **kwargs):
        messages = [{"role": "user", "content": prompt}]
        merged_kwargs = {"messages": messages, **kwargs}
        if "max_output_tokens" in merged_kwargs:
            merged_kwargs["max_tokens"] = merged_kwargs.pop("max_output_tokens")
        message = self._execute_with_fallback(merged_kwargs, model)
        return message.content

    def chat_with_tools(self, messages: list, tools: list = None, model: str = "gpt-4o-mini", json_mode: bool = False):
        kwargs = {
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        return self._execute_with_fallback(kwargs, model)
