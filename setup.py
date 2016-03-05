#!/usr/bin/env python
from setuptools import setup

setup(
    name='trezor_agent',
    version='0.6.2',
    description='Using Trezor as hardware SSH agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    packages=['trezor_agent'],
    install_requires=['ecdsa>=0.13', 'ed25519>=1.4', 'Cython>=0.23.4', 'trezor>=0.6.6', 'keepkey>=0.7.0', 'semver>=2.2'],
    platforms=['POSIX'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Communications',
    ],
    entry_points={'console_scripts': [
        'trezor-agent = trezor_agent.__main__:run_agent',
        'trezor-git = trezor_agent.__main__:run_git',
    ]},
)
