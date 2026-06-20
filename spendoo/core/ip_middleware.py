# FastAPI middleware to restrict access by IP except for health endpoint
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


import os

ALLOWED_IPS = os.getenv("SPENDOO_ALLOWED_IP", "127.0.0.1,172.17.0.1").split(",")


class IPRestrictionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow Swagger, OpenAPI, and any endpoint containing 'health' for everyone
        if (
            path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
            or "health" in path
        ):
            return await call_next(request)
        # Restrict other endpoints to ALLOWED_IPS
        client_ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0]
        if client_ip not in ALLOWED_IPS:
            return JSONResponse(
                status_code=403, content={"detail": f"Forbidden: IP {client_ip} not allowed"}
            )
        return await call_next(request)
