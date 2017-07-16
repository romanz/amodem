#!/usr/bin/env python
from setuptools import setup

setup(
    name='libagent',
    version='0.9.2',
    description='Using hardware wallets as SSH/GPG agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    packages=[
        'libagent',
        'libagent.device',
        'libagent.gpg',
        'libagent.ssh'
    ],
    install_requires=[
        'ecdsa>=0.13',
        'ed25519>=1.4',
        'semver>=2.2',
        'unidecode>=0.4.20',
    ],
    platforms=['POSIX'],
    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
        'Topic :: Security',
        'Topic :: Utilities',
    ],
)
