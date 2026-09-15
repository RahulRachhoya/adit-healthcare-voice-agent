"""Single-operator sessions, CSRF tokens, and bounded login attempts."""

import hmac
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request

hasher = PasswordHasher()


def csrf_token(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


def verify_csrf(request: Request, token: str | None):
    expected = request.session.get("csrf", "")
    if not token or not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(403, "Invalid request token. Refresh the page and try again.")


def require_operator(request: Request):
    if request.session.get("operator") != request.app.state.settings.admin_username:
        raise HTTPException(401, "Sign in to continue.")


def require_mutation(request: Request):
    require_operator(request)
    verify_csrf(request, request.headers.get("X-CSRF-Token"))


class LoginGuard:
    def __init__(self):
        self.attempts = defaultdict(deque)

    def check(self, address: str):
        now = time.monotonic()
        # Requests run on the event loop; this in-process guard supplements password verification.
        if address not in self.attempts and len(self.attempts) >= 1000:
            self.attempts = defaultdict(deque, {
                key: queue for key, queue in self.attempts.items()
                if queue and queue[-1] > now - 300
            })
            if len(self.attempts) >= 1000:
                raise HTTPException(429, "Too many login attempts. Try again later.")
        queue = self.attempts[address]
        while queue and queue[0] < now - 300:
            queue.popleft()
        if len(queue) >= 5:
            raise HTTPException(429, "Too many login attempts. Try again in five minutes.")
        queue.append(now)


def password_matches(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False
