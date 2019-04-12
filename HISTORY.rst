.. :changelog:

History
-------

[unreleased]
* Restrict to python >=3.4

1.0.0 [2019-03-20]
* Added docs

0.9.9 [2019-03-20]
* Fixed spawn configuration for workers on Unix.

0.9.8 [2019-03-07]
* Check server class was located
* Add start_method as config setting and default to spawn.
* BREAKING: Changed default config values. Heartbeat is disabled by default.

0.9.7 [2018-10-18]
* Truncate the failure cause if over the result size limit
* Removed Python 3.4 from Travis test envs due to a dateutils / urllib3 install conflict.

0.9.6 [2017-11-06]
* Fix missing attribute bug if no healthcheck configured
* Improved timing of heartbeats

0.9.5 [2017-10-30]
* Keep pypi happy

0.9.4 [2017-10-30] [not available through pypi]
* Shutdown healthcheck server immediately when stopping server
* Added info logs

0.9.3 [2017-10-27]
* Add customizable Server subclass with init method.

0.9.2 [2017-10-25]
* Change default loglevel to info.
* Improve log format.
* Handle client error when doing heartbeat and don't retry for failed tokens.

0.9.1 [2017-10-20]
* Suppress boto dropped connection info log messages.

0.9.0 [2017-09-26]
* Add HTTP healthcheck

0.8.4 [2017-09-18]
* Add loglevel arg

0.8.3 [2017-09-18]
* Add processes arg to stefuna
* Add timestamp to log format

0.8.2 [2017-08-16]
* Set the region based on region in activity ARN.

0.8.1 [2017-08-15]
* First public release
