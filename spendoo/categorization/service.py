# spendoo/categorization/service.py

from fastapi import HTTPException
import json
from spendoo.core.llm_client import LLMClient
from spendoo.categorization.models import category_block
import re

def clean_json_response(response: str):
    # Remove ```json and ``` wrappers
    cleaned = re.sub(r"```json|```", "", response).strip()
    return cleaned

class CategorizationService:

    def __init__(self):
        self.llm = LLMClient()
        self.model_name = "openai/gpt-oss-20b"

    def extract(self, text: str):

        prompt = f"""
        You are a financial receipt parser.

        Extract all transaction items from the text below.

        For each item return:
        - id (incremental starting from 1 in order of appearance)
        - item_name
        - quantity (if not mentioned assume 1)
        - unit_price
        - total_price (quantity × unit_price)
        - category_id (choose one id from the list below)

        Available categories:
        {category_block}


        Also calculate grand_total (sum of total_price).

        If no suitable category exists return null.

        Return strictly valid JSON in this format:

        {{
            "items": [
                {{
                    "id": 1,
                    "item_name": "...",
                    "quantity": 1,
                    "unit_price": 0,
                    "total_price": 0,
                    "category": "...",
                    "category_id": null
                }}
            ],
            "grand_total": 0
        }}

        Receipt/Text:
        {text.strip()}
        """

        response = self.llm.generate(prompt, self.model_name)

        try:
            cleaned_json_response = clean_json_response(response)
            data = json.loads(cleaned_json_response)
        except json.JSONDecodeError:
            print("LLM response was not valid JSON:", cleaned_json_response)
            raise HTTPException(
                status_code=422,
                detail="Model returned invalid JSON"
            )

        for idx, item in enumerate(data["items"], start=1):
            item["id"] = idx
            
        return data


