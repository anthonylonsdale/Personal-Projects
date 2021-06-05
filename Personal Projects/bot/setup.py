#!/usr/bin/env python

from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    license="MIT",
    name='risk-discord-bot',
    version='0.9.1a',
    description='Used for tracking competitive Elo rating',
    authors='GnaeusPompeiusMagnus, CrazySeanPC',
    long_description=long_description,
    author_email='alons3253@gmail.com',
    packages=['bot'],
    install_requires=['discord', 'os', 'datetime', 'glob', 're', 'asyncio'],
)
