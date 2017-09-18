#!/usr/bin/env python
import sys
sys.path.append('.')
import argparse  # noqa
from stefuna import Server, configure_logger  # noqa
from pydoc import locate  # noqa
from multiprocessing import cpu_count  # noqa
import logging  # noqa


configure_logger('',
                 '%(asctime)s [%(levelname)s/%(processName)s/%(process)d] %(message)s',
                 logging.StreamHandler())


logger = logging.getLogger('stefuna')
logger.setLevel(logging.INFO)


# Default config
config = {
    'name': 'StepFunActivityWorker',
    'activity_arn': None,
    'processes': None,
    'heartbeat': 0,
    'maxtasksperchild': 100,
    'worker': 'UNSET_WORKER_CLASS',
    'worker_config': {}
}


def main():
    parser = argparse.ArgumentParser(description='Run a Step Function Activity server.')
    parser.add_argument('--config', dest='config', action='store', required=False,
                        help='Module or dict of config to override defaults')
    parser.add_argument('--worker', dest='worker', action='store', required=False,
                        help='Module and class of worker in dot notation. Overrides config setting.')
    parser.add_argument('--processes', type=int, dest='processes', action='store', required=False,
                        help='Number of worker processes. Overrides config setting. If 0, cpu_count is used.')

    args = parser.parse_args()

    if args.config:
        local_config = locate(args.config)
        if local_config is None:
            sys.stderr.write('Error loading config {0}\n'.format(args.config))
            sys.exit(-1)

        if type(local_config) is not dict:
            local_config = {k: v for k, v in vars(local_config).items() if not k.startswith('_')}
        config.update(local_config)

    if args.worker:
        config['worker'] = args.worker

    if args.processes is not None:
        # Setting to None will use the cpu_count processes
        config['processes'] = args.processes if args.processes else None

    worker_count = config['processes']
    if worker_count is None:
        worker_count = cpu_count()

    logger.info('Running {0} for activity {1} {2} with {3} workers'.format(
        config['worker'], config['name'], config['activity_arn'], worker_count))

    Server.worker_class = locate(config['worker'])

    server = Server(name=config['name'], activity_arn=config['activity_arn'],
                    processes=config['processes'], heartbeat=config['heartbeat'],
                    maxtasksperchild=config['maxtasksperchild'],
                    worker_config=config['worker_config'])

    server.run()  # does not return
    sys.exit(0)


if __name__ == "__main__":
    main()
