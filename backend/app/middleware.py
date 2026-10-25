import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id_var

logger = logging.getLogger("app.requests")


class RequestLogMiddleware:
    """Assigns a request ID (X-Request-ID) and logs one line per request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Accept a caller-provided ID (e.g. from a load balancer) if it looks sane
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex
        request_id_var.set(request_id)

        start = time.perf_counter()
        status_code = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            client = scope.get("client")
            level = logging.ERROR if status_code >= 500 else logging.INFO
            logger.log(
                level,
                "%s %s %s",
                scope["method"],
                scope["path"],
                status_code,
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                    "client_ip": client[0] if client else None,
                },
            )
