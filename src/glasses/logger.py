import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# LOG_FORMAT = (
#     "[%(asctime)s] %(levelname)-6s %(message)s [%(name)s.%(funcName)s:%(lineno)d]"
# )

LOG_FORMAT = r"[{asctime}] [{levelname:<8}] {message}"


def setup_logging(glasses_folder: Path) -> None:
    logger_folder = glasses_folder / "logs"
    logger_folder.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        logger_folder / "glasses.log", maxBytes=10000, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, style="{"))

    logger.addHandler(file_handler)
