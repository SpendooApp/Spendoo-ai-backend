
class Settings():
    allowed_extensions: set[str] = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}
    max_size: int = 25 * 1024 * 1024

settings = Settings()