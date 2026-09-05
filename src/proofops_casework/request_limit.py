import asyncio
import time
from .json_boundary import strict_json
from starlette.responses import JSONResponse


class CaseworkBodyLimit:
    """Bounds even chunked v2 bodies before JSON parsing. No credential logging."""
    def __init__(self, app, max_bytes: int = 65536):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/v2/"):
            await self.app(scope, receive, send)
            return
        parts = []
        size = 0
        deadline = time.monotonic() + 15
        while True:
            try:
                message = await asyncio.wait_for(receive(), timeout=max(0.001,deadline-time.monotonic()))
            except asyncio.TimeoutError:
                await JSONResponse(status_code=408,content={"error":"REQUEST_BODY_TIMEOUT","executable":False})(scope,receive,send)
                return
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > self.max_bytes:
                await JSONResponse(status_code=413, content={"error": "PAYLOAD_TOO_LARGE", "executable": False})(scope, receive, send)
                return
            parts.append(body)
            if not message.get("more_body", False):
                break
        raw = b"".join(parts)
        headers = {key.lower(): value for key,value in scope.get("headers", [])}
        media = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
        is_json = not media or media == b"application/json" or (media.startswith(b"application/") and media.endswith(b"+json"))
        if raw and is_json:
            try:
                strict_json(raw, max_bytes=self.max_bytes)
            except (ValueError, UnicodeError):
                await JSONResponse(status_code=422,content={"error":"AMBIGUOUS_OR_INVALID_JSON","executable":False})(scope,receive,send)
                return
        replayed = False

        async def bounded_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": raw, "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
