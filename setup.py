#!/usr/bin/python3
#-------------------------------------------------------------
#Setup script for MTDA-MQTT
#-------------------------------------------------------------
from setuptools import setup, find_packages

setup(
    name='mtda_amqp',
    packages=find_packages(),
    version='1.0.0',
    scripts=['mtda-amqp-cli'],
    description='Multi-Tenant Devices Access-AMQP',
    url='https://github.com/anushayadav01/mtda_amqp',
    classifiers=[
        "Topic :: Utilities",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.0",
        "Topic :: Software Development :: Embedded Systems",
    ],

    install_requires=[
        "python-daemon>=2.0",
        "pika>=1.1.0"
    ],
)
