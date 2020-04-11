#!/usr/bin/env python
"""Setup script for the package."""

import io
import os
import re

from setuptools import find_packages
from setuptools import setup

PACKAGE_NAME = "dockertidy"


def get_property(prop, project):
    current_dir = os.path.dirname(os.path.realpath(__file__))
    result = re.search(
        r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
        open(os.path.join(current_dir, project, "__init__.py")).read(),
    )
    return result.group(1)


def get_readme(filename="README.md"):
    this = os.path.abspath(os.path.dirname(__file__))
    with io.open(os.path.join(this, filename), encoding="utf-8") as f:
        long_description = f.read()
    return long_description


setup(
    name=get_property("__project__", PACKAGE_NAME),
    use_scm_version={
        "version_scheme": "python-simplified-semver",
        "local_scheme": "no-local-version",
        "fallback_version": "unknown",
    },
    description="Keep docker hosts tidy",
    keywords="docker gc prune garbage",
    author=get_property("__author__", PACKAGE_NAME),
    author_email=get_property("__email__", PACKAGE_NAME),
    url=get_property("__url__", PACKAGE_NAME),
    license=get_property("__license__", PACKAGE_NAME),
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["*.test", "test", "test.*"]),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.5,<4",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Topic :: Software Development",
    ],
    install_requires=[
        "anyconfig==0.9.10",
        "appdirs==1.4.3",
        "attrs==19.3.0",
        "certifi==2020.4.5.1",
        "chardet==3.0.4",
        "colorama==0.4.3",
        "dateparser==0.7.4",
        "docker==4.2.0",
        "docker-pycreds==0.4.0",
        "environs==7.3.1",
        "idna==2.9",
        "importlib-metadata==1.6.0; python_version < '3.8'",
        "ipaddress==1.0.23",
        "jsonschema==3.2.0",
        "marshmallow==3.5.1",
        "nested-lookup==0.2.21",
        "pathspec==0.8.0",
        "pyrsistent==0.16.0",
        "python-dateutil==2.8.1",
        "python-dotenv==0.12.0",
        "python-json-logger==0.1.11",
        "pytz==2019.3",
        "regex==2020.4.4",
        "requests==2.23.0",
        "ruamel.yaml==0.16.10",
        "ruamel.yaml.clib==0.2.0; platform_python_implementation == 'CPython' and python_version < '3.9'",
        "six==1.14.0",
        "tzlocal==2.0.0",
        "urllib3==1.25.8",
        "websocket-client==0.57.0",
        "zipp==1.2.0",
    ],
    dependency_links=[],
    setup_requires=["setuptools_scm"],
    entry_points={"console_scripts": ["docker-tidy = dockertidy.__main__:main"]},
)
