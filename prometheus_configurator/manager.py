import logging

import requests

import prometheus_configurator

logger = logging.getLogger(__name__)


class PrometheusManagerClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers['User-Agent'] = (
            f'prometheus_configurator/{prometheus_configurator.__version__} '
            + f'python-requests/{requests.__version__}'
        )

    def get(self, url, **kwargs):
        url = f"{self.base_url}/{url.lstrip('/')}"
        logger.debug(f'performing http GET request to {url}')
        return self.session.get(url, **kwargs).json()

    def get_projects(self):
        # TODO: shard projects across multiple prometheus instances? see T286301
        return self.get('/v1/projects')

    def get_project_details(self, project_id: int):
        return self.get(f'/v1/projects/{project_id}')
