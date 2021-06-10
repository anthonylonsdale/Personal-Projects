#!/usr/bin/env python

import setuptools

with open("README.md", 'r') as fr:
    long_description = fr.read()

setuptools.setup(
    license="MIT",
    name='risk-discord-bot',
    version='0.9.2',
    description='Used for tracking competitive one vs one rating',
    authors='GnaeusPompeiusMagnus, CrazySeanPC',
    long_description=long_description,
    url='https://github.com/CrazySeanPC/risk-discord-bot',
    author_email='alons3253@gmail.com',
    packages=setuptools.find_packages(),
    install_requires=['discord', 'os', 'datetime', 'glob', 're', 'asyncio', 'logging'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Topic :: Games/Entertainment :: Real Time Strategy",
    ],
    python_requires='>=3.0',
#    entry_points={
#        "console_scripts": [
#            "riskbot = bot.app:main",
#        ]
#    },
)
