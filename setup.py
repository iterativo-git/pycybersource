#!/usr/bin/env python
"""
A light wrapper for Cybersource SOAP Toolkit API
"""
from setuptools import setup

setup(
    name='pycybersource',
    version='0.1.2alpha',
    description='A light wrapper for Cybersource SOAP Toolkit API',
    author='Eric Bartels',
    author_email='ebartels@gmail.com',
    url='',
    packages=['pycybersource'],
    platforms=['Platform Independent'],
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='cybersource payment soap suds api wrapper',
    requires=['suds'],
    install_requires=['suds-jurko>=0.6'],
    test_suite='pycybersource.tests',
)
