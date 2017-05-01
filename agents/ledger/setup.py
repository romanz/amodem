#!/usr/bin/env python
from setuptools import setup

setup(
    name='ledger_agent',
    version='0.9.0',
    description='Using Ledger as hardware SSH/GPG agent',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    scripts=['ledger_agent.py'],
    install_requires=[
        'libagent>=0.9.0',
        'ledgerblue>=0.1.8'
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
    entry_points={'console_scripts': [
        'ledger-agent = ledger_agent:ssh_agent',
        'ledger-gpg = ledger_agent:gpg_tool',
        'ledger-gpg-agent = ledger_agent:gpg_agent',
    ]},
)
