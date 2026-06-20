from spendoo.ocr.service import OCRService
from spendoo.categorization.service import CategorizationService
from spendoo.voice.service import VoiceService
from sqlalchemy.orm import Session
from spendoo.statistics.service import StatisticsService

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
    def get_statistics_service(cls, db: Session) -> StatisticsService:
        """Factory that creates a fresh StatisticsService bound to the provided DB session."""
        return StatisticsService(db)
