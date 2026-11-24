import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from magic_link_service import CreatorRequest, InfraiClient, create_magic_link


def test_creator_gets_a_link_and_one_delivery() -> None:
    calls = []

    def transport(method, path, body):
        calls.append((method, path, body))
        if path == "/v1/auth/user/create":
            return 200, {"ok": True, "data": {"user_id": "creator-7"}, "error": None, "metadata": {}}, {}
        return 200, {"ok": True, "data": {"message_id": "msg-9"}, "error": None, "metadata": {}}, {}

    result = create_magic_link(
        InfraiClient(api_key="test-key", transport=transport),
        CreatorRequest("maker@example.com", "Mina", "Trailer"),
        token="fixed-token",
    )

    assert result.user_id == "creator-7"
    assert result.message_id == "msg-9"
    assert "maker@example.com" in result.link
    assert calls[0][0:2] == ("POST", "/v1/auth/user/create")
    assert calls[1][0:2] == ("POST", "/v1/email/send")
    assert calls[1][2]["to"] == "maker@example.com"
