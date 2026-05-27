import uuid
from spendoo.core.services import ServiceContainer
from sqlalchemy.orm import Session
from spendoo.categorization.service import CategorizationService

class ReceiptPipeline:

    def __init__(self):

        self.ocr = ServiceContainer.get_ocr_service()

    def process_receipt(self, image_bytes, db: Session, user_id: uuid.UUID):

        # Step 1: OCR
        receipt_text = self.ocr.extract_text(image_bytes)

        # Step 2: LLM extraction
        categorization_service = CategorizationService(db)
        structured_data = categorization_service.extract(str(receipt_text), user_id)

        return structured_data