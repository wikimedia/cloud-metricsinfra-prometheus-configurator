# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import logging

import yaml

logger = logging.getLogger(__name__)


def read_openstack_configuration(file: str):
    logger.debug(f"loading openstack config from file {file}")
    with open(file, "r") as openstack_file:
        data = yaml.safe_load(openstack_file)
        return {
            "all_tenants": False,
            "domain_id": data["OS_PROJECT_DOMAIN_ID"],
            "identity_endpoint": data["OS_AUTH_URL"],
            "password": data["OS_PASSWORD"],
            "refresh_interval": "5m",
            "region": data["OS_REGION_NAME"],
            "username": data["OS_USERNAME"],
        }
