import os
import logging
import boto3
import signal
import socket
import json
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from botocore.config import Config as BotoCoreConfig
from threading import Semaphore, Thread, Event
from multiprocessing import Pool
from .worker import init_worker, run_worker_task


logger = logging.getLogger('stefuna')


def activity_region(activity_arn):
    """
    Return the region for an AWS activity_arn.

    'arn:aws:states:us-east-2:123456789012:stateMachine:hello_world' => 'us-east-2'
    """
    if activity_arn:
        parts = activity_arn.split(':')
        return parts[3] if len(parts) >= 4 else None
    else:
        return None


class Server(object):

    worker_class = None

    def __init__(self, name='StefunaWorker', activity_arn=None,
                 processes=None, heartbeat=0, maxtasksperchild=100,
                 server_config=None, worker_config=None, healthcheck=None):

        if Server.worker_class is None:
            raise ValueError('Server.worker_class must be set to a Worker '
                             'subclass before creating a server instance.')

        Server.worker_class.config = worker_config

        self.config = server_config

        # Set the client region to the region in the arn
        region = activity_region(activity_arn)

        # get_activity_task uses long polling of up to 60 seconds.
        # Client side socket timeout should be set to at least 65 seconds.
        boto_config = BotoCoreConfig(read_timeout=70, region_name=region)
        self.sf_client = boto3.client('stepfunctions', config=boto_config)
        self.activity_arn = activity_arn

        # Determine a server name based on hostname and pid.
        host = None
        try:
            host = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass

        self.server_name = '{0}-{1}'.format(name, host if host is not None else os.getpid())

        # Init the server before the workers are created.
        self.init(server_config)

        if processes is None:
            processes = os.cpu_count()

        logger.debug('Creating ServerManager %s with %d worker processes',
                     self.server_name, processes)

        self.pool = Pool(processes=processes,
                         initializer=init_worker, initargs=(Server.worker_class, region, heartbeat),
                         maxtasksperchild=maxtasksperchild)

        # We keep track of available workers with a semaphore. This allows
        # us to only get a task from the activity queue when there is
        # a worker available.
        self.workers = Semaphore(processes)
        self.stop_event = Event()

        self.healthcheck_http_server = None
        if healthcheck:
            self._create_healthcheck(healthcheck)

        # Handle signals for graceful shutdown
        signal.signal(signal.SIGTERM, self._close_signal)
        signal.signal(signal.SIGINT, self._close_signal)

    def init(self, server_config):
        """Can be overridden in a subclass to initialize a server."""
        pass

    def run(self):
        logger.debug('Run server')

        # We use the local worker_ready flag here because
        # get_activity_task() will sometimes return without
        # a new task.
        worker_ready = False

        while not self.stop_event.is_set():

            # We first acquire a worker and then wait for a task for it
            # because we want to be able to always process a task
            # immediately after we get it so we ensure a worker is ready.
            if not worker_ready:
                logger.debug('Acquiring worker')
                self.workers.acquire()  # blocks until worker available
                worker_ready = True

            response = self.sf_client.get_activity_task(
                activityArn=self.activity_arn,
                workerName=self.server_name
            )
            task_token = response.get('taskToken')
            if task_token is not None and len(task_token) > 0:
                input_str = response.get('input', '')
                self.run_task(task_token, input_str)
                worker_ready = False

        self.stop_event.clear()

        logger.debug('Server run complete')
        self.pool.close()
        logger.debug('Waiting for workers to finish')
        self.pool.join()
        logger.debug('Workers exited.')

    def run_task(self, task_token, input_data):
        """Start a new task by sending message to worker process."""
        logger.debug('Sending task to acquired worker')
        self.pool.apply_async(run_worker_task, args=(task_token, input_data),
                              callback=self._task_ended)

    def _task_ended(self, task_result):
        """Called once task is done, releases the worker."""
        self.workers.release()
        logger.debug('Released worker for task')

    def _close_signal(self, signal=None, frame=None):
        Thread(target=self.close, args=(), daemon=True).start()

    def close(self):
        """
        Signal the server run loop to stop.
        """
        logger.info('Closing server. Waiting for run loop to end')
        self.stop_event.set()

        if self.healthcheck_http_server:
            self.healthcheck_http_server.shutdown()

    def _create_healthcheck(self, port):

        class HealthcheckHTTPRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                health = {'status': 'ok'}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(health), 'UTF-8'))

            def log_message(self, format, *args):
                logger.debug("Healthcheck from %s %s" % (self.address_string(), format % args))

        self.healthcheck_http_server = HTTPServer(('', port), HealthcheckHTTPRequestHandler)

        healthcheck_thread = Thread(target=self._run_healthcheck_thread,
                                    name='healthcheck', args=(), daemon=True)
        healthcheck_thread.start()

    def _run_healthcheck_thread(self):
        logger.info('Started healthcheck thread')
        self.healthcheck_http_server.serve_forever()
        self.healthcheck_http_server.server_close()
        self.healthcheck_http_server = None
        logger.info('Ended healthcheck thread')
