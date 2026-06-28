import json, re, uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .repository import CategorizationRepository

from spendoo.core.llm_client import LLMClient

def clean_json_response(response: str):
    match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()


class CategorizationService:

    def __init__(self, db: Session):
        self.llm = LLMClient()
        self.repo = CategorizationRepository(db)
        self.model_name = "openai/gpt-oss-120b"

    def extract(self, text: str, user_id: uuid.UUID):

        categories = self.repo.get_all_categories(user_id)
        category_mapping = {}
        category_block_lines = []
        for idx, c in enumerate(categories):
            idx_str = str(idx)
            category_mapping[idx_str] = c
            category_block_lines.append(f'- {idx_str}: "{c["name"]}"')
        category_block = "\n".join(category_block_lines)

        prompt = f"""
        You are a financial receipt parser.

        Extract all transaction items from the text below.

        For each item try to return:
        - id (incremental starting from 1 in order of appearance)
        - item_name exactly as it appears in the text (avoid interpreting it, just extract the name) but without any additional descriptions or measurements if they are mentioned in the same line.
        - price 
        - category_idx (the category index from the list below that best fits the item. If no category is suitable, make it null.)

        Available categories:
        {category_block}


        Also calculate grand_total or extract it if it's explicitly mentioned in the text. If you can't find a clear grand total, sum up the item prices.

        Return strictly valid JSON. To fit within token limits, format the output as MINIFIED JSON on a single line (no newlines, no indentation, no extra spaces).
        Format: {{"items":[{{"id":1,"item_name":"...","price":0,"category_idx":0}}],"grand_total":0}}


        Receipt/Text:
        {text.strip()}
        """

        response = self.llm.generate(prompt, self.model_name, max_output_tokens=4096)

        try:
            cleaned_json_response = clean_json_response(response)
            data = json.loads(cleaned_json_response)
        except json.JSONDecodeError:
            print("LLM response was not valid JSON:", repr(cleaned_json_response))
            raise HTTPException(
                status_code=422,
                detail="Model returned invalid JSON"
            )

        # Reconstruct the full category and category_id fields
        for item in data.get("items", []):
            idx_val = str(item.get("category_idx")) if item.get("category_idx") is not None else None
            if idx_val in category_mapping:
                cat_info = category_mapping[idx_val]
                item["category"] = cat_info["name"]
                item["category_id"] = cat_info["id"]
            else:
                item["category"] = None
                item["category_id"] = None
            item.pop("category_idx", None)


        valid_ids = self.repo.get_valid_ids(user_id)
        for item in data.get("items", []):
            if item["category_id"] is not None and item["category_id"] not in valid_ids:
                print(f"Invalid category_id {item['category_id']} for item {item['item_name']}")
                raise HTTPException(
                    status_code=422,
                    detail=f"Model returned invalid category_id {item['category_id']} for item {item['item_name']}"
                )
            

        return data
