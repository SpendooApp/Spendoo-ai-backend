# Spendoo

Modular Flask project skeleton for Spendoo with separate blueprint modules.

Quick start (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run with Flask CLI
$env:FLASK_APP = "spendoo:create_app"
flask run

# Or run directly
python app.py

# Run tests
pytest -q
```

