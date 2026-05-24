"""Entry point: reads ARBLING_BRAIN_PATH, validates, runs FastMCP over stdio."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from .server import mcp
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
