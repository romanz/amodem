#!/usr/bin/env python
from setuptools import setup

setup(
    name='sshagent',
    version='0.3',
    description='Using Trezor as hardware SSH agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    license='MIT',
    url='http://github.com/romanz/trezor-agent',
    packages=['sshagent'],
    install_requires=['ecdsa', 'trezor'],
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
        'trezor-agent = sshagent.__main__:trezor_agent'
    ]},
)
