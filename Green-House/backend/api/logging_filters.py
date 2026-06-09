from __future__ import annotations

import logging


class SuppressForecastAccessLog(logging.Filter):
    """Hide noisy successful forecast polling logs from Daphne runserver."""

    def filter(self, record: logging.LogRecord) -> bool:
        details = record.args if isinstance(record.args, dict) else {}
        if details.get('path') == '/api/forecast/' and record.levelno < logging.ERROR:
            return False
        return True
