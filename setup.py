#!/usr/bin/env python
"""
A light wrapper for Cybersource SOAP Toolkit API
"""
import os
import sys
from setuptools import setup, find_packages

from . import pycybersource

# fix permissions for sdist
if 'sdist' in sys.argv:
    os.system('chmod -R a+rX .')
    os.umask(int('022', 8))

base_dir = os.path.dirname(__file__)

with open(os.path.join(base_dir, 'README'), 'rb') as fp:
    long_description = fp.read().decode('utf-8')

setup(
    name='pycybersource',
    version='0.1.2alpha',
    description='A light wrapper for Cybersource SOAP Toolkit API',
    author='Eric Bartels',
    author_email='ebartels@gmail.com',
    url='',
    platforms=['Platform Independent'],
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['pycybersource'],
    keywords='cybersource payment soap suds api wrapper',
    requires=['suds'],
    install_requires=['suds-jurko>=0.6'],
    test_suite='pycybersource.tests',
)
