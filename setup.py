#!/usr/bin/env python
from setuptools import setup
from setuptools.command.test import test as TestCommand

import os
import ast

def parse_vesrion():
    cwd = os.path.dirname(__name__)
    version_file = os.path.join(cwd, 'amodem', 'version.py')

    tree = ast.parse(open(version_file).read())
    expr, = tree.body
    return expr.value.s

class PyTest(TestCommand):

    def finalize_options(self):
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import sys
        import pytest
        sys.exit(pytest.main(['.']))

setup(
    name='amodem',
    version=parse_vesrion(),
    description='Audio Modem Communication Library',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    license='MIT',
    url='http://github.com/romanz/amodem',
    packages=['amodem'],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    install_requires=['numpy', 'six'],
    platforms=['POSIX'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
    ],
    entry_points={'console_scripts': ['amodem = amodem.__main__:_main']},
)
