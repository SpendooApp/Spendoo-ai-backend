from fastapi import FastAPI, APIRouter
from spendoo.categorization.routes import router as categorization_router
from spendoo.voice.routes import router as voice_router
from spendoo.ocr.routes import router as ocr_router
from spendoo.core.routes import router as core_router
from spendoo.forecasting.routes import router as forecasting_router
from spendoo.chatbot.routes import router as chatbot_router
from spendoo.anomaly_detection.routes import router as anomaly_router
from spendoo.core.ip_middleware import IPRestrictionMiddleware

import os


def create_app() -> FastAPI:
    app = FastAPI(title="Spendoo API")

    # Add IP restriction middleware (only in production)
    if os.getenv("SPENDOO_DEPLOY", "false").lower() == "true":
        app.add_middleware(IPRestrictionMiddleware)

    # Versioned API router
    api_v1_router = APIRouter(prefix="/api/v1")

    api_v1_router.include_router(categorization_router)
    api_v1_router.include_router(voice_router)
    api_v1_router.include_router(core_router)
    api_v1_router.include_router(ocr_router)
    api_v1_router.include_router(forecasting_router)
    api_v1_router.include_router(chatbot_router)
    api_v1_router.include_router(anomaly_router)

    app.include_router(api_v1_router)

    return app


app = create_app()
