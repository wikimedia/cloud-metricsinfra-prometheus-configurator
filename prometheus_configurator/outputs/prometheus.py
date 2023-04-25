import logging
import pathlib

import yaml

from prometheus_configurator.outputs import Output
from prometheus_configurator.prometheus import ConfigFileCreator

logger = logging.getLogger(__name__)


class PrometheusOutput(Output):
    def write(self, projects: list):
        creator = ConfigFileCreator(self.main_config)

        changes_made = False

        base_directory = pathlib.Path(self.config.get("base_directory"))
        base_rule_directory = base_directory.joinpath("rules")
        if not base_rule_directory.exists():
            changes_made = True
            base_rule_directory.mkdir()

        config_data = creator.create_prometheus_config(
            projects,
            self.manager,
            [
                f"{base_rule_directory}/*.yml",
            ],
        )

        prometheus_config_path = base_directory.joinpath("prometheus.yml")
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

        rule_files = creator.create_rule_files(projects, self.manager)
        for file_name, file_content in rule_files.items():
            file_path = base_rule_directory.joinpath(file_name)

            old_content = file_path.read_text() if file_path.exists() else ""
            new_content = yaml.safe_dump(file_content)

            if old_content != new_content:
                with file_path.open(mode="w") as file:
                    logger.info(f"writing rule file {file_path}")
                    file.write(yaml.safe_dump(file_content))
                changes_made = True
            else:
                logger.info(f"rule file {file_path} is up to date")

        for match in base_rule_directory.glob("*.yml"):
            if (
                match.name not in rule_files.keys()
                and match.name not in self.main_config.get("external_rules_files", [])
            ):
                match.unlink()
                logger.info(f"removing old rules file {match}")
                changes_made = True

        if changes_made:
            self._reload_units()
