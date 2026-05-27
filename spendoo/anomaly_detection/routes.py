from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])

@router.post("/detect")
async def detect_anomalies(data: UploadFile):
    ext = data.filename.split(".")[-1].lower()
    if ext not in ["csv", "xlsx"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")
    