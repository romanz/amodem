#!/usr/bin/env python
from setuptools import setup

setup(
    name='trezor_agent',
    version='0.7.1',
    description='Using Trezor as hardware SSH agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    packages=['trezor_agent', 'trezor_agent.gpg'],
    install_requires=['ecdsa>=0.13', 'ed25519>=1.4', 'Cython>=0.23.4', 'protobuf>=3.0.0', 'trezor>=0.7.4', 'semver>=2.2'],
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
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
        'Topic :: Security',
        'Topic :: Utilities',
    ],
    extras_require={
        'trezorlib': ['python-trezor>=0.7.4'],
        'keepkeylib': ['keepkey>=0.7.3'],
    },
    entry_points={'console_scripts': [
        'trezor-agent = trezor_agent.__main__:run_agent',
        'trezor-git = trezor_agent.__main__:run_git',
        'trezor-gpg = trezor_agent.gpg.__main__:main',
    ]},
)
