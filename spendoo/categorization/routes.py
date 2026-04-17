from spendoo.core.services import ServiceContainer
from .models import CategorizationRequest, TransactionExtractionResponse
from fastapi import APIRouter

service = ServiceContainer.get_categorization_service()
router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.post("/categorize")
def categorize(request: CategorizationRequest):
    result = service.extract(request.text)
    return TransactionExtractionResponse(**result)


# http://127.0.0.1:8000/api/v1/categorization/categorize


@router.get("/health")
def health():
    return {"status": "ok"}
