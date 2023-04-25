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
