# spendoo/categorization/service.py

import json
from spendoo.core.llm_client import LLMClient
from spendoo.categorization.models import CategoryEnum

class CategorizationService:

    def __init__(self):
        self.llm = LLMClient()
        self.model_name = "openai/gpt-oss-20b"

    def extract(self, text: str):

        prompt = f"""
        You are a financial receipt parser.

        From the text below, extract all transaction items.

        For each item return:
        - item_name
        - quantity (if not mentioned assume 1)
        - unit_price
        - total_price (quantity × unit_price)
        - category from {', '.join([c.value for c in CategoryEnum])}

        Also calculate grand_total (sum of total_price).

        Return strictly valid JSON in this format:

        {{
            "items": [
                {{
                    "item_name": "...",
                    "quantity": 1,
                    "unit_price": 0,
                    "total_price": 0,
                    "category": "food"
                }}
            ],
            "grand_total": 0
        }}

        Receipt/Text:
        {text}
        """

        response = self.llm.generate(prompt, self.model_name)

        return json.loads(response)
