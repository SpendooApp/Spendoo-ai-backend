# spendoo/core/llm_client.py

from openai import OpenAI
from spendoo.core.config import settings

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

    def generate(self, prompt: str, model: str):
        response = self.client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text
