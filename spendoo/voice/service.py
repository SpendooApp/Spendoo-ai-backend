from groq import Groq
from spendoo.core.config import settings


class VoiceService:

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """
        Convert audio → text using Whisper
        """

        transcription = self.client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3",

            prompt="""
            Specify context and highlight on different languages used
            """,

            temperature=0
        )

        return transcription.text