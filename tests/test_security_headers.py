import asyncio
from types import SimpleNamespace

from starlette.responses import Response

from app.main import CONTENT_SECURITY_POLICY, aplicar_headers_seguranca


def _executar_middleware(path):
    async def call_next(_request):
        return Response("ok")

    request = SimpleNamespace(url=SimpleNamespace(path=path))
    return asyncio.run(aplicar_headers_seguranca(request, call_next))


def test_middleware_aplica_headers_de_seguranca_e_csp():
    resposta = _executar_middleware("/")

    assert resposta.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resposta.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )


def test_middleware_preserva_csp_compativel_com_swagger():
    for path in ("/docs", "/redoc", "/docs/oauth2-redirect"):
        resposta = _executar_middleware(path)
        assert "Content-Security-Policy" not in resposta.headers
        assert resposta.headers["X-Content-Type-Options"] == "nosniff"
