import logging
from stefuna import Server

logger = logging.getLogger('stefuna.example')

#
# Having a custom Server subclass is purely optional.
# In most cases you will not require one.
#


class HelloServer(Server):

    def init(self, server_config):
        """Initialize the single server instance"""
        logger.debug('Init Hello Server')
