"""Check a running loopback dashboard without dialing or exposing credentials."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx


def csrf(response):
    return re.search(r'name="csrf-token" content="([^"]+)"', response.text).group(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--username", default="operator")
    parser.add_argument("--call-id", help="Optionally verify a known synthetic persistence record.")
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("This check accepts loopback URLs only.")
    password = Path(args.password_file).read_text(encoding="utf-8").strip()
    checks = []
    with httpx.Client(base_url=args.base_url, follow_redirects=True, timeout=15) as client:
        response = client.get("/healthz")
        assert response.status_code == 200 and response.json() == {"status": "ok"}
        checks.append("liveness")
        assert client.get("/api/calls").status_code == 401
        checks.append("private API rejects unauthenticated access")
        login = client.get("/login")
        response = client.post("/login", data={
            "username": args.username, "password": password, "csrf": csrf(login),
        })
        assert response.status_code == 200 and "New test call" in response.text
        # The login response can set its cookie on the redirect rather than the final GET.
        assert any("httponly" in r.headers.get("set-cookie", "").lower()
                   for r in [*response.history, response])
        checks.append("login and HttpOnly session")
        token = csrf(response)
        ready = client.get("/api/readiness")
        assert ready.status_code == 200 and ready.json()["calls_enabled"] is False
        checks.append("live calling disabled")
        listing = client.get("/api/calls")
        assert listing.status_code == 200 and isinstance(listing.json()["calls"], list)
        checks.append("database-backed history")
        for path in ("/static/dashboard.js", "/static/styles.css"):
            assert client.get(path).status_code == 200
        checks.append("packaged assets")
        assert client.post("/api/calls", json={}).status_code == 403
        checks.append("CSRF protection")
        if args.call_id:
            detail = client.get(f"/api/calls/{args.call_id}")
            assert detail.status_code == 200
            assert detail.json()["id"] == args.call_id
            assert detail.json()["patient"]["name"].startswith("LOCAL CHECK")
            assert detail.json()["booking"]["status"] == "booked"
            assert client.get(f"/calls/{args.call_id}").status_code == 200
            checks.append("persisted synthetic call and booking")
        client.post("/logout", data={"csrf": token})
        assert client.get("/api/calls").status_code == 401
        checks.append("logout")
    print(f"HTTP checks passed ({len(checks)}): " + ", ".join(checks))


if __name__ == "__main__":
    main()
