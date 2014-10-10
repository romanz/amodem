#!/usr/bin/env python
import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

pwd = os.path.dirname(__file__)

from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):

    def finalize_options(self):
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(['tests']))

setup(
    name="amodem",
    version="1.2",
    description="Audio Modem Communication Library",
    author="Roman Zeyde",
    author_email="roman.zeyde@gmail.com",
    license="MIT",
    url="http://github.com/romanz/amodem",
    packages=['amodem'],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    install_requires=['numpy', 'bitarray', 'reedsolo'],
    platforms=['POSIX'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Communications",
    ],
    scripts=['scripts/amodem'],
)
