import json, re, uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .repository import CategorizationRepository

from spendoo.core.llm_client import LLMClient

def clean_json_response(response: str):
    # Remove ```json and ``` wrappers
    cleaned = re.sub(r"```json|```", "", response).strip()
    return cleaned

class CategorizationService:

    def __init__(self, db: Session):
        self.llm = LLMClient()
        self.repo = CategorizationRepository(db)
        self.model_name = "gpt-4o-mini"

    def extract(self, text: str, user_id: uuid.UUID):

        categories = self.repo.get_all_categories(user_id)
        category_block = "\n".join(
            f'- id: "{c["id"]}", name: "{c["name"]}"'
            for c in categories
        )

        prompt = f"""
        You are a financial receipt parser.

        Extract all transaction items from the text below.

        For each item try to return:
        - id (incremental starting from 1 in order of appearance)
        - item_name exactly as it appears in the text (avoid interpreting it, just extract the name) but without any additional descriptions or measurements if they are mentioned in the same line.
        - price 
        - category (choose one category from the list below that best fits the item based on its description, if you are unsure make it null)
        - category_id (choose one id from the list below)

        Available categories:
        {category_block}


        Also calculate grand_total or extract it if it's explicitly mentioned in the text. If you can't find a clear grand total, sum up the item prices.

        If no suitable category exists return null.

        Return strictly valid JSON in this format:

        {{
            "items": [
                {{
                    "id": 1,
                    "item_name": "...",
                    "price": 0,
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

        valid_ids = self.repo.get_valid_ids(user_id)
        for item in data.get("items", []):
            if item["category_id"] not in valid_ids:
                print(f"Invalid category_id {item['category_id']} for item {item['item_name']}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Model returned invalid category_id {item['category_id']} for item {item['item_name']}"
                )
            

        return data


