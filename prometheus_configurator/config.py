import yaml

from prometheus_configurator.utils import merge


def load_config_files(paths: list):
    data = {}
    for path in paths:
        print(f'loading own configuration from {path}')
        data = merge(yaml.safe_load(path.open(mode='r')), data)

    return data
