#!/usr/bin/env python
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

pwd = os.path.dirname(__file__)

setup(
    name="amodem",
    version="1.0",
    description="Audio Modem Communication Library",
    author="Roman Zeyde",
    author_email="roman.zeyde@gmail.com",
    license="MIT",
    url="http://github.com/romanz/amodem",
    packages=['amodem'],
    tests_require=['py.test'],
    install_requires=['numpy', 'bitarray', 'reedsolo'],
    platforms=['POSIX'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Communications",
    ],
)
