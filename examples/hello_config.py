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
activity_arn = 'arn:aws:states:us-west-2:00000000000000:activity:hello'

# The number of worker processes.
# If None, it will be set to the number of cores.
processes = None

# Number of seconds between heartbeats.
# None or 0 means there is no heartbeat.
heartbeat = 120

# Maximum number of tasks for a worker to run before the worker
# process is automatically killed and a new one created.
# If None, workers will not be killed.
maxtasksperchild = None

# If set to a non-zero integer, an HTTP healthcheck handler listens on
# the port number.
# Healthcheck requests are GET requests to 'http://localhost:<healthcheck>/'
# and return JSON: {"status": "ok"}
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
