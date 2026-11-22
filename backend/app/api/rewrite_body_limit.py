from __future__ import annotations

from starlette.responses import JSONResponse


MAX_REWRITE_REQUEST_BODY_BYTES = 3 * 1024 * 1024


class RewriteBodyLimitMiddleware:
    """
    Enforce a maximum incoming body size exclusively for POST /rewrite.

    The request body is buffered only up to the configured limit.
    Other endpoints are not affected.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != "/rewrite"
        ):
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]

        if len(content_lengths) > 1:
            await self._reject(
                scope,
                receive,
                send,
                status_code=400,
                detail="Multiple Content-Length headers are not allowed.",
            )
            return

        content_length = None

        if content_lengths:
            raw_content_length = content_lengths[0]

            if not raw_content_length.isdigit():
                await self._reject(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    detail="Invalid Content-Length header.",
                )
                return

            try:
                content_length = int(raw_content_length)
            except ValueError:
                await self._reject(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    detail="Invalid Content-Length header.",
                )
                return

        if (
            content_length is not None
            and content_length > MAX_REWRITE_REQUEST_BODY_BYTES
        ):
            await self._reject(
                scope,
                receive,
                send,
                status_code=413,
                detail="Rewrite request body exceeds the 3 MiB limit.",
            )
            return

        chunks: list[bytes] = []
        total_bytes = 0

        while True:
            message = await receive()

            if message["type"] == "http.disconnect":
                return

            if message["type"] != "http.request":
                continue

            chunk = message.get("body", b"")
            total_bytes += len(chunk)

            if total_bytes > MAX_REWRITE_REQUEST_BODY_BYTES:
                await self._reject(
                    scope,
                    receive,
                    send,
                    status_code=413,
                    detail="Rewrite request body exceeds the 3 MiB limit.",
                )
                return

            chunks.append(chunk)

            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        body_sent = False

        async def replay_receive():
            nonlocal body_sent

            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }

            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope, receive, send, *, status_code: int, detail: str):
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
        )

        await response(scope, receive, send)