from fastapi import FastAPI, APIRouter
from spendoo.categorization.routes import router as categorization_router
from spendoo.voice.routes import router as voice_router
from spendoo.ocr.routes import router as ocr_router
from spendoo.core.routes import router as core_router
from spendoo.forecasting.routes import router as forecasting_router
from spendoo.chatbot.routes import router as chatbot_router
from spendoo.anomaly_detection.routes import router as anomaly_router
from spendoo.statistics.routes import router as statistics_router
from spendoo.core.hmac_middleware import HMACSigningMiddleware

import os
from fastapi.responses import RedirectResponse

def create_app(config: dict = None) -> FastAPI:
    app = FastAPI(title="Spendoo API")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/docs")

    app.add_middleware(HMACSigningMiddleware)

    # Versioned API router
    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(categorization_router)
    api_v1_router.include_router(voice_router)
    api_v1_router.include_router(core_router)
    api_v1_router.include_router(ocr_router)
    api_v1_router.include_router(forecasting_router)
    api_v1_router.include_router(chatbot_router)
    api_v1_router.include_router(anomaly_router)
    api_v1_router.include_router(statistics_router)

    app.include_router(api_v1_router)
    return app

app = create_app()