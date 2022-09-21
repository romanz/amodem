#!/usr/bin/env python
from setuptools import setup

setup(
    name='jade_agent',
    version='0.1.0',
    description='Using Blockstream Jade as hardware SSH agent',
    author='Jamie C. Driver',
    author_email='jamie@blockstream.com',
    url='http://github.com/romanz/trezor-agent',
    scripts=['jade_agent.py'],
    install_requires=[
        'libagent>=0.14.5',
        # Jade py api from github source, v0.1.37
        'jadepy[requests] @ git+https://github.com/Blockstream/Jade.git@0.1.37'
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
        'jade-agent = jade_agent:ssh_agent',
        'jade-gpg = jade_agent:gpg_tool',
        'jade-gpg-agent = jade_agent:gpg_agent',
    ]},
)
