# Spendoo

Modular FastAPI project skeleton for Spendoo with separate router modules.

Quick start (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run with Uvicorn (recommended)
uvicorn app:app --reload

# Or run directly
python app.py

# Run tests
pytest -q
```

## API Documentation

Once running, access the interactive Swagger UI at:
http://127.0.0.1:8000/docs

Redoc documentation is available at:
http://127.0.0.1:8000/redoc