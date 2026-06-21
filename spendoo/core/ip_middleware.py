# FastAPI middleware to restrict access by IP except for health endpoint
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


import os
import ipaddress

# Default to allowing localhost and standard Docker subnets, plus any env-defined IPs
ALLOWED_IPS_RAW = ["127.0.0.1", "172.17.0.0/16", "172.18.0.0/16"]
env_ips = os.getenv("SPENDOO_ALLOWED_IP")
if env_ips:
    ALLOWED_IPS_RAW.extend(env_ips.split(","))

ALLOWED_NETWORKS = []
for ip_str in ALLOWED_IPS_RAW:
    ip_str = ip_str.strip()
    if not ip_str:
        continue
    try:
        if "/" in ip_str:
            ALLOWED_NETWORKS.append(ipaddress.ip_network(ip_str, strict=False))
        else:
            ALLOWED_NETWORKS.append(ipaddress.ip_address(ip_str))
    except ValueError:
        pass


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
        client_ip_str = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
        try:
            client_ip = ipaddress.ip_address(client_ip_str)
            allowed = False
            for item in ALLOWED_NETWORKS:
                if isinstance(item, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                    if client_ip in item:
                        allowed = True
                        break
                else:
                    if client_ip == item:
                        allowed = True
                        break
            if not allowed:
                return JSONResponse(
                    status_code=403, content={"detail": f"Forbidden: IP {client_ip_str} not allowed"}
                )
        except ValueError:
            return JSONResponse(
                status_code=403, content={"detail": f"Forbidden: Invalid client IP {client_ip_str}"}
            )
        return await call_next(request)
