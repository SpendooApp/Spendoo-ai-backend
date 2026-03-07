from fastapi import FastAPI, APIRouter
from spendoo.categorization.routes import router as categorization_router


app = FastAPI(title="Spendoo API")

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(categorization_router)

app.include_router(api_v1_router)


