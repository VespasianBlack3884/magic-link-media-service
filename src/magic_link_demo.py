from __future__ import annotations

import sys

from magic_link_service import CreatorRequest, InfraiClient, create_magic_link


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 src/magic_link_demo.py EMAIL ASSET_TITLE")
    result = create_magic_link(InfraiClient(), CreatorRequest(sys.argv[1], "Media creator", sys.argv[2]))
    print({"user_id": result.user_id, "message_id": result.message_id, "link": result.link})


if __name__ == "__main__":
    main()
