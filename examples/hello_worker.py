import logging
from stefuna import Worker

logger = logging.getLogger('stefuna.example')


class HelloWorker(Worker):

    def init(self):
        """Initialize the single instance in a worker"""
        # self.config is the worker config
        self.logger.debug('Init worker instance')

    def run_task(self, task_token, input_data):
        self.logger.debug('Worker in run_task')

        # Do some work!
        # self.config is the worker config

        # Return value can be a string or a dict/array that
        # will be JSON stringified.
        return {"message": "Hello World"}
