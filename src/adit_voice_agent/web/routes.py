"""Thin web routes; call lifecycle and provider logic belong to services."""

import asyncio
import secrets
from datetime import UTC, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from adit_voice_agent.db.models import utcnow
from adit_voice_agent.schemas import PatientInput
from adit_voice_agent.timezones import TIMEZONE_LABELS
from adit_voice_agent.web.auth import (
    csrf_token,
    password_matches,
    require_mutation,
    require_operator,
    verify_csrf,
)

router = APIRouter()


def render(request, name, **context):
    return request.app.state.templates.TemplateResponse(
        request=request, name=name,
        context={"csrf": csrf_token(request), "operator": request.session.get("operator"), **context},
    )


@router.api_route("/healthz", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("operator"):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", error=None)


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    verify_csrf(request, form.get("csrf"))
    request.app.state.login_guard.check(request.client.host if request.client else "unknown")
    settings = request.app.state.settings
    username = str(form.get("username", ""))[:100]
    password = str(form.get("password", ""))[:1000]
    matched = await asyncio.to_thread(
        password_matches, settings.admin_password_hash.get_secret_value(), password,
    )
    if not secrets.compare_digest(username, settings.admin_username) or not matched:
        response = render(request, "login.html", error="The username or password is incorrect.")
        response.status_code = 401
        return response
    request.session.clear()
    request.session["operator"] = settings.admin_username
    csrf_token(request)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    require_operator(request)
    form = await request.form()
    verify_csrf(request, form.get("csrf"))
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/")
async def dashboard(request: Request):
    if request.session.get("operator") != request.app.state.settings.admin_username:
        return RedirectResponse("/login", status_code=303)
    return render(request, "dashboard.html", timezones=TIMEZONE_LABELS)


@router.get("/calls/{call_id}", dependencies=[Depends(require_operator)])
async def detail_page(request: Request, call_id: str):
    await asyncio.to_thread(request.app.state.calls.raw, call_id)
    return render(request, "call_detail.html", call_id=call_id)


@router.get("/api/readiness", dependencies=[Depends(require_operator)])
async def readiness(request: Request):
    return request.app.state.settings.readiness()


@router.post("/api/calls", status_code=202, dependencies=[Depends(require_mutation)])
async def create_call(request: Request, patient: PatientInput):
    return await request.app.state.calls.create(patient, request.headers.get("Idempotency-Key"))


@router.get("/api/calls", dependencies=[Depends(require_operator)])
async def list_calls(request: Request):
    return {"calls": await asyncio.to_thread(request.app.state.calls.listing)}


@router.get("/api/calls/{call_id}", dependencies=[Depends(require_operator)])
async def get_call(request: Request, call_id: str):
    service = request.app.state.calls
    call = await asyncio.to_thread(service.raw, call_id)
    checked = call.evaluation_checked_at
    if checked and checked.tzinfo is None:
        checked = checked.replace(tzinfo=UTC)
    if (call.export_status == "ready" and call.trace_id
            and call.evaluation.get("status") != "completed"
            and (checked is None or checked < utcnow() - timedelta(seconds=10))):
        await asyncio.to_thread(service.update, call_id, evaluation_checked_at=utcnow())
        try:
            scores = await asyncio.to_thread(request.app.state.opik.get_evaluation, call.trace_id)
            await asyncio.to_thread(service.update, call_id, evaluation=scores)
        except Exception:
            await asyncio.to_thread(service.update, call_id, evaluation={"status": "unavailable", "scores": []})
    return await asyncio.to_thread(service.detail, call_id)


@router.post("/api/calls/{call_id}/end", dependencies=[Depends(require_mutation)])
async def end_call(request: Request, call_id: str):
    return await request.app.state.calls.end(call_id)


@router.get("/api/calls/{call_id}/recording", dependencies=[Depends(require_operator)])
async def recording(request: Request, call_id: str):
    call = await asyncio.to_thread(request.app.state.calls.raw, call_id)
    try:
        url = await request.app.state.recording.signed_url(call.recording)
        return {"url": url, "expires_in": 300}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "Recording access is temporarily unavailable.") from exc
