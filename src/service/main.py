"""Service entrypoint."""

import uvicorn

from src.service.config import load_config


def main() -> None:
    """Run the service with host/port pulled from config/env."""
    cfg = load_config()
    uvicorn.run("src.service.api:app", host=cfg.get("host", "0.0.0.0"), port=int(cfg.get("port", 8000)), reload=False)


if __name__ == "__main__":
    main()
