import logging
import pathlib

import yaml

from prometheus_configurator.outputs import Output
from prometheus_configurator.prometheus import ConfigFileCreator

logger = logging.getLogger(__name__)


class ThanosRuleOutput(Output):
    def write(self, projects: list):
        creator = ConfigFileCreator(self.main_config)

        file_path = pathlib.Path(self.config.get("alert_file_path"))

        rule_data = creator.create_thanos_rule_file(self.manager)

        old_data = file_path.read_text() if file_path.exists() else ""
        new_data = yaml.safe_dump(rule_data)

        if old_data != new_data:
            with file_path.open(mode="w") as file:
                logger.info(f"writing alert file {file_path}")
                file.write(new_data)
            self._reload_units()
        else:
            logger.info("thanos rule alert file is up to date")
