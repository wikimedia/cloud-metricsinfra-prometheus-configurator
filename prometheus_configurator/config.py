import logging

import yaml

from prometheus_configurator.utils import merge

logger = logging.getLogger(__name__)


def load_config_files(paths: list):
    data = {}
    for path in paths:
        logger.info(f'loading own configuration from {path}')
        data = merge(yaml.safe_load(path.open(mode='r')), data)

    return data
