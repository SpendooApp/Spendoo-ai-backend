import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")   
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
    VOICE_ALLOWED_EXTENSIONS: set[str] = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}
    VOICE_MAX_SIZE: int = 25 * 1024 * 1024
    
settings = Settings()