class CategorizationRepository:

    def __init__(self):
        self._categories = [
            {"id": 1, "name": "Groceries"},
            {"id": 2, "name": "Entertainment"},
            {"id": 3, "name": "Utilities"},
            {"id": 4, "name": "Transportation"},
            {"id": 5, "name": "Food"},
            {"id": 6, "name": "Health"},
            {"id": 7, "name": "Education"},
            {"id": 8, "name": "Shopping"},
            {"id": 9, "name": "Drinks"},
            {"id": 10, "name": "Personal Care"},
            {"id": 11, "name": "Clothing"}
        ]

    def get_all_categories(self):
        return self._categories

    def get_valid_ids(self):
        return {c["id"] for c in self._categories}