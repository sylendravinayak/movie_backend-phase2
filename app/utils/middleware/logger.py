import logging
import time
import uuid
import contextvars
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context var to store request id so any code during the request can fetch it
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Attach request_id to every LogRecord so formatter can include it."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """
    Basic logging setup. Call once at app startup (e.g. in main).
    This creates a StreamHandler with a formatter that includes the request_id.
    """
    root = logging.getLogger()
    if root.handlers:
        # Avoid adding duplicate handlers when reloading during development
        return

    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    handler.addFilter(RequestIdFilter())
    root.setLevel(level)
    root.addHandler(handler)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Simple request logger middleware.

    - Generates a request_id and sets it in a context var (available to log records).
    - Logs request start (method, path, client) and end (status, duration_ms).
    - Does NOT read request body by default to avoid interfering with downstream handlers.
      If you need body logging, request buffering is required (I can provide that if needed).
    """

    async def dispatch(self, request: Request, call_next):
        # Set request id for this request
        req_id = str(uuid.uuid4())
        token = request_id_ctx.set(req_id)

        logger = logging.getLogger("app.middleware")
        start = time.time()

        try:
            client_host = None
            if request.client:
                client_host = request.client.host

            logger.info(
                "request.start",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query),
                    "client": client_host,
                },
            )

            response = await call_next(request)

            duration_ms = int((time.time() - start) * 1000)
            logger.info(
                "request.end",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response

        except Exception:
            # Log unexpected errors with stack trace
            duration_ms = int((time.time() - start) * 1000)
            logger.exception(
                "request.error",
                extra={"duration_ms": duration_ms},
            )
            raise
        finally:
            # Clear the context var for safety
            request_id_ctx.reset(token)


# Optional: helper to get request id elsewhere in app
def get_request_id() -> Optional[str]:
    return request_id_ctx.get()