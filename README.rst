.. image:: https://travis-ci.org/irothschild/stefuna.svg
   :target: https://travis-ci.org/irothschild/stefuna

===============================
stefuna
===============================

Stefuna is a simple AWS Step Function Activity server framework.
It makes it incredibly quick and easy to write workers to
process activity tasks in Python.

Implementation
---------------

Stefuna uses a multiprocessing Pool of pre-forked worker processes
to run the activity tasks. The is a single instance of a Worker
class in each worker process. To implement your task, simply
create a Worker subclass, override the
``run_task(self, task_token, input_data)`` method and start the
server.

The ``run_task`` method can do whatever work it requires and then
return a result as a string or dict (which is automatically JSON
stringified). If the method raises an exception, the task is failed
with a ``Task.Failure`` error.

Configurable heartbeats are supported for longer-running tasks.


Getting Started
---------------

See the examples folder for the files described below.

Create a worker class, which is a subclass of the `stefuna.Worker`
in the file `hello_worker.py`:

.. code-block:: python
    import logging
    from stefuna import Worker

    logger = logging.getLogger('stefuna.example')


    class HelloWorker(Worker):

	def init(self):
	    """Initialize the single instance in a worker"""
	    pass

	def run_task(self, task_token, input_data):
	    self.logger.debug('Worker in run_task')

	    # Do some work!

	    # Return value can be a string or a dict/array that
	    # will be JSON stringified.
	    return {"message": "Hello World"}


Create a config file `hello_config.py`, setting the worker class, server name, and
activity ARN:

.. code-block:: python
    #
    # Stefuna server worker config file
    #

    # The module path of the worker class
    worker = 'examples.hello_worker.HelloWorker'

    # The base name of the server that will be combined with host and pid
    # and used when requesting tasks from AWS.
    name = 'HelloExample'

    # Set the ARN for the activity that this server will work on.
    activity_arn = 'arn:aws:states:us-west-2:00000000000000:activity:hello'

    # The number of worker processes.
    # If None, it will be set to the number of cores.
    processes = None

    # Maximum number of seconds between heartbeats.
    # None or 0 means there is no heartbeat.
    heartbeat = 120

    # Maximum number of tasks for a worker to run before the worker
    # process is automatically killed and a new one created.
    # If None, workers will not be killed.
    maxtasksperchild = None

    # The worker_config is an arbitrary dictionary that is available
    # in the worker instance as self.config
    # Use it for worker-specific configuration.
    worker_config = {
	'foo': 'bar'
    }


Run the server:

.. code-block:: bash
    $ stefuna --config=hello_config


History (Change Log)
--------------------

See `HISTORY.rst <HISTORY.rst>`_


License
-------

MIT License

See `LICENSE <LICENSE>`_
