# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import functools
import logging

import requests

import prometheus_configurator

logger = logging.getLogger(__name__)


class PrometheusManagerClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            f"prometheus_configurator/{prometheus_configurator.__version__} "
            + f"python-requests/{requests.__version__}"
        )

    def get(self, url, **kwargs):
        url = f"{self.base_url}/{url.lstrip('/')}"
        logger.debug(f"performing http GET request to {url}")
        return self.session.get(url, **kwargs).json()

    def get_projects(self):
        # TODO: shard projects across multiple prometheus instances? see T286301
        return self.get("/v1/projects")

    @functools.lru_cache(maxsize=1024)
    def get_project_details(self, project_id: int):
        return self.get(f"/v1/projects/{project_id}")

    def get_contact_groups(self):
        return self.get("/v1/contact-groups")

    def get_supported_openstack_images(self):
        return self.get("/v1/supported-openstack-images")
