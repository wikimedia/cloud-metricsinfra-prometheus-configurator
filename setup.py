# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from setuptools import setup

setup(
    name="prometheus-configurator",
    python_requires=">=3.9",
    version="0.0.1",
    packages=["prometheus_configurator"],
    install_requires=[
        "requests",
        "PyYAML",
    ],
    scripts=["scripts/create-prometheus-config"],
)
