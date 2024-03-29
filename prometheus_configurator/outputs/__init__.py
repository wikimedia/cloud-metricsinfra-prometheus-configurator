# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import logging
import subprocess

from prometheus_configurator.manager import PrometheusManagerClient

logger = logging.getLogger(__name__)


class Output:
    def __init__(
        self, config: dict, main_config: dict, manager: PrometheusManagerClient
    ):
        self.config = config
        self.main_config = main_config
        self.manager = manager

    def write(self, projects: list):
        pass

    def _get_project_config(self, project: str) -> dict:
        return self.main_config.get("projects", {}).get(project, {})

    def _reload_units(self):
        # This will succeed even if Prometheus fails to reload its config
        # In that case, just let it - it will alert shortly
        for unit in self.config.get("units_to_reload", []):
            logger.info(f"reloading systemd unit {unit}")
            subprocess.check_call(
                ["/usr/bin/sudo", "/usr/bin/systemctl", "reload", unit]
            )
        for unit in self.config.get("units_to_restart", []):
            logger.info(f"restarting systemd unit {unit}")
            subprocess.check_call(
                ["/usr/bin/sudo", "/usr/bin/systemctl", "restart", unit]
            )
