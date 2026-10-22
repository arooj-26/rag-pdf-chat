"""Process-local bounded rate limiter and security headers (single-worker local app)."""
import time
from collections import OrderedDict, deque
from fastapi import Request
from fastapi.responses import JSONResponse
from config import get_settings

_buckets: OrderedDict = OrderedDict()


async def guard(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        maximum = get_settings().max_upload_size_bytes * 10 + 1024 * 1024 if request.url.path == "/api/upload" else 64 * 1024
        try:
            if int(request.headers.get("content-length", "0")) > maximum:
                return JSONResponse({"detail": "Request body is too large."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid content length."}, status_code=400)
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        key = (request.client.host if request.client else "unknown", "auth" if request.url.path.startswith("/api/auth/") else "api")
        now = time.monotonic()
        bucket = _buckets.setdefault(key, deque())
        _buckets.move_to_end(key)
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        limit = min(20, get_settings().requests_per_minute) if key[1] == "auth" and request.method == "POST" else get_settings().requests_per_minute
        if len(bucket) >= limit:
            return JSONResponse({"detail": "Too many requests. Try again shortly."}, status_code=429, headers={"Retry-After": "60"})
        bucket.append(now)
        if len(_buckets) > 10000:
            _buckets.popitem(last=False)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response
