import logging
import sys


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("oblio_exporter_py")
    logger.setLevel(logging.DEBUG)
    fh = logging.StreamHandler(sys.stderr)
    fh_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    return logger


logger = setup_logger()
