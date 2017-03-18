#!/usr/bin/env python
from setuptools import setup

setup(
    name='trezor_agent',
    version='0.8.3',
    description='Using Trezor as hardware SSH agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    packages=['trezor_agent', 'trezor_agent.device', 'trezor_agent.gpg'],
    install_requires=[
        'ecdsa>=0.13', 'ed25519>=1.4', 'Cython>=0.23.4', 'protobuf>=3.0.0', 'semver>=2.2',
        'trezor>=0.7.6', 'keepkey>=0.7.3', 'ledgerblue>=0.1.8',
        'hidapi==0.7.99.post15'  # until https://github.com/keepkey/python-keepkey/pull/8 is merged
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
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
        'Topic :: Security',
        'Topic :: Utilities',
    ],
    entry_points={'console_scripts': [
        'trezor-agent = trezor_agent.__main__:run_agent',
        'trezor-gpg-create = trezor_agent.gpg.__main__:main_create',
        'trezor-gpg-agent = trezor_agent.gpg.__main__:main_agent',
        'trezor-gpg-unlock = trezor_agent.gpg.__main__:auto_unlock',
    ]},
)
