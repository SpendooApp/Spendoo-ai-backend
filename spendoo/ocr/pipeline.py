from spendoo.ocr.service import OCRService
from spendoo.categorization.service import CategorizationService
import base64

class ReceiptPipeline:

    def __init__(self):

        self.ocr = OCRService()
        self.extractor = CategorizationService()

    def process_receipt(self, image_bytes):

        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        # Step 1: OCR
        receipt_text = self.ocr.extract_text(base64_image)

        # Step 2: LLM extraction
        structured_data = self.extractor.extract(receipt_text)

        return structured_data