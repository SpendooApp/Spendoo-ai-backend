from spendoo.core.services import ServiceContainer

class ReceiptPipeline:

    def __init__(self):

        self.ocr = ServiceContainer.get_ocr_service()
        self.extractor = ServiceContainer.get_categorization_service()

    def process_receipt(self, image_bytes):

        # Step 1: OCR
        receipt_text = self.ocr.extract_text(image_bytes)

        # Step 2: LLM extraction
        structured_data = self.extractor.extract(str(receipt_text))

        return structured_data