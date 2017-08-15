import logging


# Configure a logger with a format and handler.
def configure_logger(name, log_format, handler):
    logger = logging.getLogger(name)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)
    logger.propagate = False
    return logger
