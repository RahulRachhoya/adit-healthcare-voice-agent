"""Application factory, security headers, and service wiring."""

from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from adit_voice_agent.config import get_settings
from adit_voice_agent.db.session import create_session_factory
from adit_voice_agent.services.calls import CallError, CallService
from adit_voice_agent.services.post_call import adapter_for
from adit_voice_agent.services.recording import RecordingService
from adit_voice_agent.web.auth import LoginGuard
from adit_voice_agent.web.routes import router


def create_app(settings=None, sessions=None, gateway=None, opik=None, recording=None):
    settings = settings or get_settings()
    if len(settings.session_secret.get_secret_value()) < 32 or not settings.present("admin_password_hash"):
        raise RuntimeError("Set SESSION_SECRET (32+ characters) and ADMIN_PASSWORD_HASH before starting.")
    app = FastAPI(title="Adit Voice Assessment", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(CallError)
    async def call_error_response(_request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    app.state.settings = settings
    app.state.sessions = sessions or create_session_factory(settings.database_url)
    app.state.calls = CallService(app.state.sessions, settings, gateway)
    app.state.opik = opik or adapter_for(settings)
    app.state.recording = recording or RecordingService(settings)
    app.state.login_guard = LoginGuard()
    folder = Path(__file__).parent
    app.state.templates = Jinja2Templates(directory=folder / "templates")
    app.add_middleware(
        SessionMiddleware, secret_key=settings.session_secret.get_secret_value(),
        session_cookie="adit_session", https_only=settings.cookie_secure, same_site="strict", max_age=3600,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[h.strip() for h in settings.allowed_hosts.split(",") if h.strip()],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        media_origin = urlparse(settings.supabase_url)
        allowed_media = f"{media_origin.scheme}://{media_origin.netloc}" if media_origin.netloc else ""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            f"media-src 'self' {allowed_media}; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    app.mount("/static", StaticFiles(directory=folder / "static"), name="static")
    app.include_router(router)
    return app
