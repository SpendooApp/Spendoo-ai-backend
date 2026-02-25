# spendoo/categorization/service.py

from fastapi import HTTPException
import json
from spendoo.core.llm_client import LLMClient
from spendoo.categorization.models import CATEGORY_ID_MAP, CategoryEnum
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

        From the text below, extract all transaction items.

        For each item return:
        - item_name
        - quantity (if not mentioned assume 1)
        - unit_price
        - total_price (quantity × unit_price)
        - category from {', '.join([c.value for c in CategoryEnum])}

        Also calculate grand_total (sum of total_price).

        If no suitable category exists return null.

        Return strictly valid JSON in this format:

        {{
            "items": [
                {{
                    "item_name": "...",
                    "quantity": 1,
                    "unit_price": 0,
                    "total_price": 0,
                    "category": null
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

        # Add incremental IDs safely
        for idx, item in enumerate(data["items"], start=1):
            item["id"] = idx
            category_name = item.get("category")
            if category_name is None:
                item["category_id"] = None
            else:
                item["category_id"] = CATEGORY_ID_MAP.get(category_name.lower(), None)

        return data


# When saving transaction:

# transaction = Transaction(
#     user_id=user_id,
#     item_name=item["item_name"],
#     quantity=item["quantity"],
#     unit_price=item["unit_price"],
#     total_price=item["total_price"],
#     category_id=item["category_id"]
# )