"""Entry point: python -m video_clipper.api.main"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("VC_HOST", "127.0.0.1")
    port = int(os.environ.get("VC_PORT", "8765"))
    uvicorn.run("video_clipper.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
