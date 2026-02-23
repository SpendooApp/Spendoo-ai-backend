from spendoo import create_app
from fastapi import FastAPI
from spendoo.categorization.routes import router as categorization_router


app = FastAPI(title="Spendoo API")
app.include_router(categorization_router)

# in root path:
# uvicorn app:app --reload

# For Flask compatibility (if needed)
# flask_app = create_app()    

