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
