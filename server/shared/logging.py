import logging
from contextvars import ContextVar


correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [cid=%(correlation_id)s] %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)