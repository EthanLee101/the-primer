import logging


def configure_logging() -> None:
    """Server-side logging only — nothing here ever reaches an HTTP response.
    Fly.io (and most container platforms) capture stdout/stderr as logs
    directly, so no file handler or external sink is needed at this scale."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
