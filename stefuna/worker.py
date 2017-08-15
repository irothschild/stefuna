import logging
import json
import time
import boto3
import signal
from abc import ABCMeta, abstractmethod
from threading import Thread, Lock


logger = logging.getLogger('stefuna')


_default_sigterm_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)


class Worker(object):
    """
    There is a single instance of a Worker object in each worker process.

    Subclass this class and override the run_task() method.
    """
    __metaclass__ = ABCMeta

    # This is set to the single worker instance per child process.
    worker_instance = None

    # Worker config, set from the server init.
    config = None

    # Subclasses can use this worker logger if they wish.
    logger = logger

    def __init__(self, heartbeat=0):

        self.sf_client = boto3.client('stepfunctions')

        # This will be set to the current task_token of a running task.
        self.task_token = None

        # If heartbeats are enabled, the heartbeat thread is created once
        # and left running. Thus, the exact timing of the heartbeats are
        # somewhat random but they will be at most heartbeat seconds apart.
        self.heartbeat_sf_client = None
        if heartbeat:
            self.token_lock = Lock()
            self._set_task_token(None)
            self.heartbeat_thread = Thread(target=self._run_heartbeat_thread,
                                           name='heartbeat',
                                           args=(heartbeat,), daemon=True)
            self.heartbeat_thread.start()
        else:
            self.token_lock = None
            self._set_task_token(None)
            self.heartbeat_thread = None

        self.init()

    def init(self):
        """
        Called once when the worker process is created.
        Can be overridden in a subclass to initialize the worker instance.

        The instance will be set up and the self.config will be set when
        this is called.
        """
        pass

    def _set_task_token(self, task_token):
        """
        We guard task_token with a lock because it's accessed from the
        heartbeat thread.
        """
        if self.token_lock is not None:
            self.token_lock.acquire()

        self.task_token = task_token

        if self.token_lock is not None:
            self.token_lock.release()

    def _run_task(self, task_token, input_data):
        """
        We ensure the code run in the worker will be exception free.
        """
        self._task_result_status = None
        try:
            self._set_task_token(task_token)

            self.logger.debug('Running task')

            try:
                input_data = json.loads(input_data)
            except ValueError as e:
                raise ValueError('Error parsing task input json: {0}'.format(e))

            task_result = self.run_task(task_token, input_data)

            # We send the success result if we haven't sent a
            # success or failure already for this task.
            if self._task_result_status is None:
                if type(task_result) is not str:
                    task_result = (json.dumps(task_result) if task_result
                                   is not None else '{}')
                self.send_task_success(task_result)

        except Exception as e:
            self.logger.exception('Exception running task')
            if self._task_result_status is None:
                error = 'Task.Failure'
                cause = 'Exception raised during task run: {0}'.format(e)
                self.send_task_failure(error, cause)

        finally:
            status = 'task_success' if self._task_result_status \
                     else 'task_failure'
            self.logger.debug('Task complete with %s', status)

            try:
                self._set_task_token(None)
            except:
                self.logger.exception('Exception clearing task token')

            return (task_token, status)

    @abstractmethod
    def run_task(self, task_token, input_data):
        """
        To be overridden in a Worker subclass to run the task.

        A success result can be returned as a dict or JSON string.

        If there is an error running the task, self.send_task_failure()
        should be called or an exception should be raised.
        """
        self.logger.warning('Override Worker run_task() in your worker subclass.')

    def send_task_success(self, task_result):
        try:
            self.sf_client.send_task_success(
                taskToken=self.task_token,
                output=task_result
            )
            self._task_result_status = True
        except:
            # We log the error and the task state will eventually timeout
            self.logger.exception('Error sending task success for task')
            self._task_result_status = False

    def send_task_failure(self, error, cause):
        try:
            self.sf_client.send_task_failure(
                taskToken=self.task_token,
                error=error,
                cause=cause
            )
        except:
            # We log the error and the task state will eventually timeout
            self.logger.exception('Error sending task failure for task')
        finally:
            self._task_result_status = False

    def heartbeat(self):
        """Called from the heartbeat thread every X seconds"""
        self.token_lock.acquire()
        token = self.task_token
        self.token_lock.release()

        if token is not None:
            try:
                self.logger.debug('Sending heartbeat for task %s', token)
                self.heartbeat_sf_client.send_task_heartbeat(taskToken=token)
            except:
                self.logger.exception('Error sending heartbeat for task %s', token)

    def _run_heartbeat_thread(self, beat):
        self.logger.info('Started heartbeat_thread %d', beat)
        self.heartbeat_sf_client = boto3.client('stepfunctions')
        while True:
            time.sleep(beat)
            self.heartbeat()


def init_worker(worker_class, heartbeat):
    """
    One-time initialize of each worker process.
    """
    logger.info('Initializing worker')
    signal.signal(signal.SIGTERM, _default_sigterm_handler)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Create the single instance.
    Worker.worker_instance = worker_class(heartbeat=heartbeat)


def run_worker_task(task_token, input_data):
    """
    Called via a Pool; runs in a child process.
    """
    return Worker.worker_instance._run_task(task_token, input_data)
