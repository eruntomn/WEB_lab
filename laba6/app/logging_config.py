import logging
import os
from logging.handlers import RotatingFileHandler

from flask import g, has_request_context


class RequestIdFilter(logging.Filter):
    """Добавляет в каждую строку лога идентификатор запроса."""

    def filter(self, record):
        record.request_id = (
            g.get('request_id', '-') if has_request_context() else '-'
        )
        return True


def setup_logging(level, log_file):
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(request_id)s] %(message)s'
    )
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding='utf-8'
        ),
    ]
    logger = logging.getLogger('api')
    logger.handlers = []
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    return logger
