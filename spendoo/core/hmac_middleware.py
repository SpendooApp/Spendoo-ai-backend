import os
import time
import hmac
import hashlib
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class HMACSigningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.getenv("SPENDOO_DEPLOY", "false").lower() != "true":
            return await call_next(request)

        path = request.url.path
        if (
            path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
            or "health" in path
        ):
            return await call_next(request)

        signature = request.headers.get("x-signature")
        timestamp_str = request.headers.get("x-timestamp")

        if not signature or not timestamp_str:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        current_time = int(time.time())
        if abs(current_time - timestamp) > 10:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        secret_key = os.getenv("HMAC_SECRET_KEY")
        if not secret_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        body = await request.body()
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        request._receive = receive

        message = timestamp_str.encode("utf-8") + body
        expected_sig = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)
