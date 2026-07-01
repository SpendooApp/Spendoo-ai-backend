import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    
    _github_tokens_str = os.getenv("GITHUB_TOKENS", "")
    GITHUB_TOKENS: list[str] = [t.strip() for t in _github_tokens_str.split(",") if t.strip()]

    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    AZURE_ENDPOINT: str = os.getenv("AZURE_ENDPOINT")
    AZURE_KEY: str = os.getenv("AZURE_KEY")
    GEMINI_OCR_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
    ]
    OCR_PROMPT = """
    Extract all line items from this receipt. Return ONLY a valid JSON array, no markdown, no explanation.
    Format: [{"name": "item name (keep Arabic as-is)", "price": 12.50 (total price for that line, not per unit)}]
    Return total amount paid if given and DO NOT include it as a line item.
    Format: {"items": [...], "total": 12.50}
    """

    VOICE_ALLOWED_EXTENSIONS: set[str] = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}
    VOICE_MAX_SIZE: int = 25 * 1024 * 1024
    
settings = Settings()