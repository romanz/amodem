#!/usr/bin/env python
from setuptools import setup

setup(
    name='trezor_agent',
    version='0.4.2',
    description='Using Trezor as hardware SSH agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    license='MIT',
    url='http://github.com/romanz/trezor-agent',
    packages=['trezor_agent', 'trezor_agent.trezor'],
    install_requires=['ecdsa>=0.13', 'trezor>=0.6.6'],
    platforms=['POSIX'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
    ],
    entry_points={'console_scripts': [
        'trezor-agent = trezor_agent.__main__:trezor_agent'
    ]},
)
