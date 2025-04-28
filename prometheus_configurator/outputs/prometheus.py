# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import logging
import pathlib
import shlex
import subprocess
from typing import Any

import yaml

from prometheus_configurator.outputs import Output
from prometheus_configurator.prometheus import ConfigFileCreator

logger = logging.getLogger(__name__)


class PrometheusOutput(Output):
    def write_directory(
        self, base: pathlib.Path, files: dict[str, Any], external: list[str]
    ) -> bool:
        changes_made = False

        for file_name, file_content in files.items():
            file_path = base / file_name

            old_content = file_path.read_text() if file_path.exists() else ""
            new_content = yaml.safe_dump(file_content)

            if old_content != new_content:
                with file_path.open(mode="w") as file:
                    logger.info(f"writing file {file_path}")
                    file.write(yaml.safe_dump(file_content))
                changes_made = True
            else:
                logger.info(f"file {file_path} is up to date")

        for match in base.glob("*.yml"):
            if match.name not in files.keys() and match.name not in external:
                match.unlink()
                logger.info(f"removing old file {match}")
                changes_made = True

        return changes_made

    def write(self, projects: list):
        creator = ConfigFileCreator(self.main_config)

        changes_made = False

        base_directory = pathlib.Path(self.config["base_directory"])
        base_rule_directory = base_directory / "rules"
        if not base_rule_directory.exists():
            changes_made = True
            base_rule_directory.mkdir()

        blackbox_address = self.config.get("blackbox_address")

        config_data, blackbox_scrapes = creator.create_prometheus_config(
            projects,
            self.manager,
            [f"{base_rule_directory}/*.yml"],
            self.config,
        )

        prometheus_config_path = base_directory / "prometheus.yml"
        old_config = (
            prometheus_config_path.read_text()
            if prometheus_config_path.exists()
            else ""
        )
        new_config = yaml.safe_dump(config_data)
        if old_config != new_config:
            with prometheus_config_path.open(mode="w") as file:
                logger.info(f"writing prometheus config file {prometheus_config_path}")
                file.write(new_config)
            changes_made = True
        else:
            logger.info("prometheus configuration up to date")

        if blackbox_address:
            blackbox_directory = pathlib.Path(self.config["blackbox_dir"])
            if self.write_directory(blackbox_directory, blackbox_scrapes, []):
                logger.info("merging blackbox config")
                subprocess.check_call(
                    ["/usr/bin/sudo", *shlex.split(self.config["blackbox_reload"])]
                )
                changes_made = True

        rule_files = creator.create_rule_files(projects, self.manager)
        if self.write_directory(
            base_rule_directory,
            rule_files,
            self.main_config.get("external_rules_files", []),
        ):
            changes_made = True

        if changes_made:
            self._reload_units()
