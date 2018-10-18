import logging


SFN_LIMITS = {
    'CAUSE_SIZE': 32768
}

ELLIPSIS = '...'


# Configure a logger with a format and handler.
def configure_logger(name, log_format, handler):
    logger = logging.getLogger(name)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def safe_cause(cause):
    if len(cause) > SFN_LIMITS['CAUSE_SIZE']:
        return cause[:SFN_LIMITS['CAUSE_SIZE'] - len(ELLIPSIS)] + ELLIPSIS
    return cause
