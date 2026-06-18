import uuid
from sqlalchemy.orm import Session
from .models import CategoryORM

class CategorizationRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_all_categories(self, user_id: uuid.UUID):
        rows = (
            self.db.query(CategoryORM)
            .filter(CategoryORM.is_deleted == False, 
                    CategoryORM.user_id == user_id
                    )
            .order_by(CategoryORM.category_name)
            .all()
            )
        return [
            {
                "id": str(r.id),
                "name": r.category_name
            }
            for r in rows
        ]

    def get_valid_ids(self, user_id: uuid.UUID):
        rows = (
            self.db.query(CategoryORM.id)
            .filter(CategoryORM.is_deleted == False, 
                    CategoryORM.user_id == user_id
                    )
            .all()
            )
        return [str(r.id) for r in rows]