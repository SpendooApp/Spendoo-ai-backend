from .models import CategorizationRequest, TransactionExtractionResponse
from spendoo.categorization.service import CategorizationService
from fastapi import APIRouter
service = CategorizationService()
router = APIRouter(prefix="/categorization", tags=["categorization"])

@router.post('/categorize')
def categorize(request: CategorizationRequest):
    result = service.extract(request.text)
    return TransactionExtractionResponse(**result)

# http://127.0.0.1:8000/categorization/categorize

