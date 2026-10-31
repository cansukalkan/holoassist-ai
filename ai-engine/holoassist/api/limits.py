"""Bound request bodies before JSON parsing or endpoint side effects."""

from starlette.responses import JSONResponse

MAX_BODY_BYTES = 64 * 1024


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes=MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def reject(status, code):
            await JSONResponse(
                {"schema_version": "1.0", "code": code},
                status_code=status,
            )(scope, receive, send)

        lengths = [v for k, v in scope.get("headers", ()) if k.lower() == b"content-length"]
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                return await reject(400, "invalid_content_length")
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                return await reject(413, "request_too_large")
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
