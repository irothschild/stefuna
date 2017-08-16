import boto3
import unittest
import time
import json
import logging
from threading import Thread
from ..server import Server
from ..worker import Worker, init_worker
from ..util import configure_logger


class SFClient(object):
    def __init__(self):
        self.successes = []
        self.failures = []
        self.heartbeats = []
        self.activity_count = 0

    def reset(self):
        self.successes = []
        self.failures = []
        self.heartbeats = []
        self.activity_count = 0

    def send_task_success(self, taskToken, output):
        self.successes.append((taskToken, output))

    def send_task_failure(self, taskToken, error, cause):
        self.failures.append((taskToken, error, cause))

    def send_task_heartbeat(self, taskToken):
        self.heartbeats.append(taskToken)

    def get_activity_task(self, activityArn=None, workerName=None):
        if self.activity_count > 0:
            self.activity_count -= 1
            return {'taskToken': 'AT-{0}'.format(self.activity_count),
                    'input': json.dumps({"foo": "bar"})}
        time.sleep(3)
        return {'taskToken': ''}


original_boto3_client = boto3.client


def mock_stepfunction_client(name, config=None, **kwargs):
    if name == 'stepfunctions':
        return SFClient()
    else:
        return original_boto3_client(name, config=config, **kwargs)


class GoodWorker(Worker):
    def run_task(self, task_token, input_data):
        self.logger.debug('Worker in run_task')
        time.sleep(0.5)
        return {"test": "success"}


class SlowWorker(Worker):
    def run_task(self, task_token, input_data):
        self.logger.debug('Worker in run_task')
        time.sleep(3)
        return {"test": "success"}


class BadWorker(Worker):
    def run_task(self, task_token, input_data):
        self.logger.debug('Worker in run_task')
        raise ValueError('Intentional bad worker error')


class TestServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Server.worker_class = GoodWorker
        boto3.client = mock_stepfunction_client

    def test_configure_logger(self):
        configure_logger('stefuna',
                         '[%(levelname)s/%(processName)s/%(process)d] %(message)s',
                         logging.StreamHandler())

    def test_server_run_task(self):
        server = Server(name='test', processes=1, heartbeat=0)
        server.run_task('1', '{}')

    def test_process_worker(self):
        init_worker(GoodWorker, None, 0)
        worker = Worker.worker_instance
        task_token = 'token123'
        input_data = '{"name":"foo"}'
        ret = worker._run_task(task_token, input_data)
        self.assertEqual(ret[0], task_token)
        self.assertEqual(ret[1], 'task_success')
        self.assertEqual(len(worker.sf_client.successes), 1)
        self.assertEqual(worker.sf_client.successes[0][0], task_token)
        self.assertEqual(len(worker.sf_client.failures), 0)
        self.assertEqual(len(worker.sf_client.heartbeats), 0)

    def test_server_run(self):
        server = Server(name='test', processes=1, heartbeat=0)
        server.sf_client.activity_count = 3

        def _stop_server(server):
            time.sleep(3)
            server.close()

        stop_thread = Thread(target=_stop_server, args=(server,), daemon=True)
        stop_thread.start()
        server.run()
        self.assertEqual(server.sf_client.activity_count, 0)
        time.sleep(1)

    def test_worker_success(self):
        worker = GoodWorker()
        task_token = 'token123'
        input_data = '{"name":"foo"}'
        ret = worker._run_task(task_token, input_data)
        self.assertEqual(ret[0], task_token)
        self.assertEqual(ret[1], 'task_success')
        self.assertEqual(len(worker.sf_client.successes), 1)
        self.assertEqual(worker.sf_client.successes[0][0], task_token)
        self.assertEqual(len(worker.sf_client.failures), 0)
        self.assertEqual(len(worker.sf_client.heartbeats), 0)

    def test_worker_failure_bad_input(self):
        worker = GoodWorker()
        task_token = 'token123'
        input_data = '{"bad json"}'
        ret = worker._run_task(task_token, input_data)
        self.assertEqual(ret[0], task_token)
        self.assertEqual(ret[1], 'task_failure')
        self.assertEqual(len(worker.sf_client.successes), 0)
        self.assertEqual(len(worker.sf_client.failures), 1)
        self.assertEqual(worker.sf_client.failures[0][0], task_token)
        self.assertEqual(len(worker.sf_client.heartbeats), 0)

    def test_worker_failure_bad_worker(self):
        worker = BadWorker()
        task_token = 'token123'
        input_data = '{"name":"foo"}'
        ret = worker._run_task(task_token, input_data)
        self.assertEqual(ret[0], task_token)
        self.assertEqual(ret[1], 'task_failure')
        self.assertEqual(len(worker.sf_client.successes), 0)
        self.assertEqual(len(worker.sf_client.failures), 1)
        self.assertEqual(worker.sf_client.failures[0][0], task_token)
        self.assertEqual(len(worker.sf_client.heartbeats), 0)

    def test_worker_heartbeat(self):
        worker = SlowWorker(heartbeat=2)
        task_token = 'token123'
        input_data = '{"name":"foo"}'
        ret = worker._run_task(task_token, input_data)
        # Wait to make sure another heartbeat isn't sent
        time.sleep(3)
        self.assertEqual(ret[0], task_token)
        self.assertEqual(ret[1], 'task_success')
        self.assertEqual(len(worker.sf_client.successes), 1)
        self.assertEqual(worker.sf_client.successes[0][0], task_token)
        self.assertEqual(len(worker.sf_client.failures), 0)
        self.assertEqual(len(worker.sf_client.heartbeats), 0)
        self.assertEqual(len(worker.heartbeat_sf_client.heartbeats), 1)
        self.assertEqual(worker.heartbeat_sf_client.heartbeats[0], task_token)
