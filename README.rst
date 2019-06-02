.. image:: https://travis-ci.org/irothschild/stefuna.svg
   :target: https://travis-ci.org/irothschild/stefuna

===============================
stefuna
===============================

Stefuna is a simple AWS Step Function Activity server framework.
It makes it incredibly quick and easy to write workers to
process activity tasks in Python.

Install
-------

.. code-block:: bash

    $ pip install stefuna


Implementation
---------------

Stefuna uses a multiprocessing Pool of pre-forked worker processes
to run the activity tasks. There is a single instance of a Server
class in the main process and a single instance of a Worker
class in each worker process. To implement your task, simply
create a Worker subclass, override the
``run_task(self, task_token, input_data)`` method and start the
server.

The ``run_task`` method can do whatever work it requires and then
return a result as a string or dict (which is automatically JSON
stringified). It can be a long-running task but the worker process
won't be released until the method returns.

If ``run_task`` raises an exception, the task is failed
with a ``Task.Failure`` error which can be handled in the Step
Function state machine. Alternatively, a worker can call
``self.send_task_failure(error, cause)`` with a custom error
string and return value from ``run_task`` will be ignored.

Configurable heartbeats are supported for longer-running tasks.

A healthcheck port can be configured so the server listens for
HTTP GET requests on ``http://localhost:<healthcheck>/``

The Server instance in the main class can be customized by
setting a custom Server subclass in the config and overriding
the ``init`` method.

The Python multiprocessing start method for worker processes
can be set in the config. By default 'spawn' is used to ensure
a clean, safe worker process. Although potentially slower than
'forkserver' (or 'fork' which is not recommended), since new
workers are typically rarely created, this should not be an
issue.


Getting Started
---------------

See the examples folder for the files described below.

Step Function
^^^^^^^^^^^^^^

Create an AWS Step Function Activity, for example ``hello``.

Then create a Step Function State Machine, using the ARN of the activity you just created.
For example a single state ``Hello World`` State Machine:

.. code-block:: JavaScript

    {
       "Comment": "A Hello World example with a single activity",
       "StartAt": "HelloWorld",
       "States": {
          "HelloWorld": {
            "Type": "Task",
            "Resource": "arn:aws:states:us-east-1:00000000000000:activity:hello",
            "End": true
          }
       }
    }


Worker Code
^^^^^^^^^^^

Create a worker class, which is a subclass of the ``stefuna.Worker``
in the file ``hello_worker.py``:

.. code-block:: python

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


Create a config file ``hello_config.py``, setting the worker class, server name, and
activity ARN:

.. code-block:: python

    #
    # Stefuna server worker config file
    #

    # [OPTIONAL] The module path of the server class
    server = 'examples.hello_server.HelloServer'

    # The module path of the worker class
    worker = 'examples.hello_worker.HelloWorker'

    # The base name of the server that will be combined with host and pid
    # and used when requesting tasks from AWS.
    name = 'HelloExample'

    # Set the ARN for the activity that this server will work on.
    activity_arn = 'arn:aws:states:us-east-1:00000000000000:activity:hello'

    # [OPTIONAL] The number of worker processes.
    # If None, it will be set to the number of cores.
    # Default is None.
    processes = None

    # [OPTIONAL] Number of seconds between heartbeats.
    # None or 0 means there is no heartbeat.
    # Default is no heartbeat.
    heartbeat = 120

    # [OPTIONAL] Maximum number of tasks for a worker to run before the worker
    # process is automatically killed and a new one created.
    # If None, workers will not be killed.
    # Default is None.
    maxtasksperchild = None

    # [OPTIONAL] The multiprocessing start method for worker processes.
    # See https://docs.python.org/3.7/library/multiprocessing.html for more info
    # The default is 'spawn' which starts a fresh python interpreter process.
    # It is rather slow compared to using fork or forkserver, but we typically
    # create workers and leave them running so the impact should be minimal.
    # Possible values are:
    # spawn - Recommended (Unix and Windows)
    # fork - Not recommended due to thread-safety issues
    # forkserver - On Unix platforms which support passing fds over Unix pipes
    # '' - Uses the python defaults. Not recommended.
    start_method = 'spawn'

    # [OPTIONAL] If set to a non-zero integer, an HTTP healthcheck handler listens on
    # the port number.
    # Healthcheck requests are GET requests to 'http://localhost:<healthcheck>/'
    # and return JSON: {"status": "ok"}
    # Default is 8080
    healthcheck = 8080

    # [OPTIONAL] The server_config is an arbitrary dictionary that is available
    # in the server instance as self.config and passed to server init()
    # Use it for server-specific configuration.
    server_config = {
        'foo': 'bar'
    }

    # [OPTIONAL] The worker_config is an arbitrary dictionary that is available
    # in the worker instance as self.config
    # Use it for worker-specific configuration.
    worker_config = {
	'foo': 'bar'
    }


Run the server:

.. code-block:: bash

    $ stefuna --config=hello_config


.. code-block:: bash

    $ stefuna --help
    usage: stefuna [-h] [--config CONFIG] [--worker WORKER]
                   [--activity-arn ACTIVITY_ARN] [--processes PROCESSES]
                   [--loglevel LOGLEVEL]

    Run a Step Function Activity server.

    optional arguments:
      -h, --help            show this help message and exit
      --config CONFIG       Module or dict of config to override defaults
      --worker WORKER       Module and class of worker in dot notation. Overrides
                            config setting.
      --activity-arn ACTIVITY_ARN
                            Step Function Activity ARN, Overrides config setting.
      --processes PROCESSES
                            Number of worker processes. Overrides config setting.
                            If 0, cpu_count is used.
      --loglevel LOGLEVEL   Loglevel (debug, info, warning, error or critical).
                            Overrides config setting.


History (Change Log)
--------------------

See `HISTORY.rst <HISTORY.rst>`_


License
-------

MIT License

See `LICENSE <LICENSE>`_
