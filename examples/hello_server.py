import logging
from stefuna import Server

logger = logging.getLogger('stefuna.example')


class HelloServer(Server):

    def init(self, server_config):
        """Initialize the single server instance"""
        logger.debug('Init Hello Server')
