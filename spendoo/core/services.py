from spendoo.ocr.service import OCRService
from spendoo.categorization.service import CategorizationService
from spendoo.voice.service import VoiceService


class ServiceContainer:
    _voice_service = None
    _ocr_service = None
    _categorization_service = None
    @classmethod
    def get_voice_service(cls) -> VoiceService:
        if cls._voice_service is None:
            cls._voice_service = VoiceService()
        return cls._voice_service

    @classmethod
    def get_ocr_service(cls) -> OCRService:
        if cls._ocr_service is None:
            cls._ocr_service = OCRService()
        return cls._ocr_service

    @classmethod
    def get_categorization_service(cls) -> CategorizationService:
        if cls._categorization_service is None:
            cls._categorization_service = CategorizationService()
        return cls._categorization_service