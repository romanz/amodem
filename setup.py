#!/usr/bin/env python
from setuptools import setup
from setuptools.command.test import test as TestCommand

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
    version='1.15.3',
    description='Audio Modem Communication Library',
    author='Roman Zeyde',
    author_email='dev@romanzey.de',
    license='MIT',
    url='http://github.com/romanz/amodem',
    packages=['amodem'],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    install_requires=['numpy'],
    platforms=['POSIX'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
    ],
    entry_points={'console_scripts': ['amodem = amodem.__main__:_main']},
)
