#!/usr/bin/env python
from setuptools import setup

print('NEVER USE THIS CODE FOR REAL-LIFE USE-CASES!!!')
print('ONLY FOR DEBUGGING AND TESTING!!!')

setup(
    name='fake_device_agent',
    version='0.9.0',
    description='Testing trezor_agent with a fake device - NOT SAFE!!!',
    author='Roman Zeyde',
    author_email='roman.zeyde@gmail.com',
    url='http://github.com/romanz/trezor-agent',
    scripts=['fake_device_agent.py'],
    install_requires=[
        'libagent>=0.9.0',
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
        'fake-device-agent = fake_device_agent:ssh_agent',
        'fake-device-gpg = fake_device_agent:gpg_tool',
        'fake-device-gpg-agent = fake_device_agent:gpg_agent',
    ]},
)
