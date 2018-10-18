import logging
import json
import time
import boto3
from botocore.config import Config as BotoCoreConfig
from botocore.exceptions import ClientError
import signal
from abc import ABCMeta, abstractmethod
from threading import Thread, Lock
from .util import safe_cause


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

    def __init__(self, region=None, heartbeat=0):

        boto_config = BotoCoreConfig(region_name=region)
        self.sf_client = boto3.client('stepfunctions', config=boto_config)

        # This will be set to the current task_token of a running task.
        self.task_token = None

        # If heartbeats are enabled, the heartbeat thread is created once
        # and left running. Thus, the exact timing of the heartbeats are
        # somewhat random but they will be at most heartbeat seconds apart.
        self.heartbeat_sf_client = None
        if heartbeat:
            self.token_lock = Lock()
            self._set_task_token(None)
            self._heartbeat_fail_token = None
            self.heartbeat_thread = Thread(target=self._run_heartbeat_thread,
                                           name='heartbeat',
                                           args=(region, heartbeat), daemon=True)
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
        self.task_token_time = time.time() if task_token is not None else None

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
            except Exception:
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
        except Exception:
            # We log the error and the task state will eventually timeout
            self.logger.exception('Error sending task success for task')
            self._task_result_status = False

    def send_task_failure(self, error, cause):
        try:
            self.sf_client.send_task_failure(
                taskToken=self.task_token,
                error=error,
                cause=safe_cause(cause)
            )
        except Exception:
            # We log the error and the task state will eventually timeout
            self.logger.exception('Error sending task failure for task')
        finally:
            self._task_result_status = False

    def heartbeat(self, token):
        """Called from the heartbeat thread every X seconds"""
        if token is not None and token != self._heartbeat_fail_token:
            try:
                self.logger.debug('Sending heartbeat for task')
                self.heartbeat_sf_client.send_task_heartbeat(taskToken=token)
                self._heartbeat_fail_token = None

            except ClientError as e:
                ecode = e.response['Error'].get('Code', 'Unknown')
                if ecode in ['TaskDoesNotExist', 'InvalidToken', 'TaskTimedOut']:
                    # We set the heartbeat_fail_token so we don't retry a heartbeat for this token.
                    self._heartbeat_fail_token = token
                    # We only use debug level logging since the task either deleted or ended.
                    self.logger.debug('Error sending heartbeat for task: %s', ecode)
                else:
                    self.logger.exception('Error sending heartbeat for task')
            except Exception:
                self.logger.exception('Error sending heartbeat for task')

    def _run_heartbeat_thread(self, region, beat):
        self.logger.info('Started heartbeat_thread %d', beat)
        boto_config = BotoCoreConfig(region_name=region)
        self.heartbeat_sf_client = boto3.client('stepfunctions', config=boto_config)
        while True:
            self.token_lock.acquire()
            token = self.task_token
            token_time = self.task_token_time
            self.token_lock.release()

            if token is None:
                time.sleep(beat)
            else:
                delta = time.time() - token_time
                if delta + 0.5 < beat:
                    time.sleep(beat - delta)  # sleep until beat seconds from start of token processing
                else:
                    self.heartbeat(token)
                    time.sleep(beat)


def init_worker(worker_class, region, heartbeat):
    """
    One-time initialize of each worker process.
    """
    logger.info('Initializing worker')
    signal.signal(signal.SIGTERM, _default_sigterm_handler)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Create the single instance.
    Worker.worker_instance = worker_class(region=region, heartbeat=heartbeat)


def run_worker_task(task_token, input_data):
    """
    Called via a Pool; runs in a child process.
    """
    return Worker.worker_instance._run_task(task_token, input_data)
