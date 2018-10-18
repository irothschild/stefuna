#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='stefuna',
    version='0.9.7',
    description='AWS Step Function Activity server framework',
    long_description=readme + '\n\n' + history,
    author='Ivo Rothschild',
    author_email='ivo@clarify.io',
    url='https://github.com/irothschild/stefuna',
    packages=[
        'stefuna',
    ],
    package_dir={'stefuna':
                 'stefuna'},
    include_package_data=True,
    install_requires=[
        'boto3>=1.4.6, <2.0.0'
    ],
    entry_points={
        'console_scripts': [
            'stefuna = stefuna.stefuna:main'
        ]
    },
    license="MIT",
    zip_safe=False,
    keywords='AWS Step Functions Activity task server worker',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
    ],
    tests_require=[
    ],
    test_suite='stefuna.test',
)
