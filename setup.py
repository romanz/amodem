#!/usr/bin/env python
from setuptools import setup

setup(
    name='libagent',
    version='0.12.1',
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
        'backports.shutil_which>=3.5.1',
        'ConfigArgParse>=0.12.1',
        'python-daemon>=2.1.2',
        'ecdsa>=0.13',
        'ed25519>=1.4',
        'mnemonic>=0.18',
        'pymsgbox>=1.0.6',
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
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
        'Topic :: Security',
        'Topic :: Utilities',
    ],
)
