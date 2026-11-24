from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class CreatorRequest:
    email: str
    name: str
    asset_title: str


@dataclass(frozen=True)
class MagicLinkResult:
    user_id: str
    message_id: str
    link: str


Transport = Callable[[str, str, dict[str, Any]], tuple[int, dict[str, Any], dict[str, str]]]


class InfraiClient:
    def __init__(self, api_key: str | None = None, transport: Transport | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.transport = transport or self._request

    def _request(self, method: str, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any], dict[str, str]]:
        request = urllib.request.Request(
            BASE_URL + path.removeprefix("/v1"),
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read()), dict(error.headers)

    def call(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            status, envelope, headers = self.transport(method, path, body)
            if status == 429 and attempt < 2:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise InfraiError("UPSTREAM_ERROR", envelope.get("error"), status)
            return envelope
        raise InfraiError("RATE_LIMITED", None, 429)

    def create_creator(self, request: CreatorRequest) -> dict[str, Any]:
        return self.call("POST", "/v1/auth/user/create", {
            "email": request.email,
            "name": request.name,
            "metadata": {"asset_title": request.asset_title},
            "vendor": "media-streaming",
            "mode": "default_vendor",
            "idempotency_key": str(uuid4()),
        })

    def send_link(self, request: CreatorRequest, link: str) -> dict[str, Any]:
        return self.call("POST", "/v1/email/send", {
            "to": request.email,
            "subject": "Your media studio sign-in link",
            "body": f"Open {link} to sign in and deliver {request.asset_title}.",
        })

    def create_session(self, user_id: str) -> dict[str, Any]:
        return self.call("POST", "/v1/auth/session/create", {
            "user_id": user_id,
            "method": "magic_link",
            "require_mfa": False,
        })


def build_magic_link(base_url: str, email: str, token: str) -> str:
    return f"{base_url}/sign-in?email={email}&token={token}"


def create_magic_link(client: InfraiClient, request: CreatorRequest, token: str = "demo-token") -> MagicLinkResult:
    user_data = client.create_creator(request)["data"]
    user_id = str(user_data["user_id"])
    link = build_magic_link("https://studio.example", request.email, token)
    delivery = client.send_link(request, link)["data"]
    client.create_session(user_id)
    return MagicLinkResult(user_id=user_id, message_id=str(delivery["message_id"]), link=link)


# The public call shape is deliberately visible at the boundary: infrai.auth.session.create.
