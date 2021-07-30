import logging
import pathlib

import yaml

from prometheus_configurator.outputs import Output
from prometheus_configurator.prometheus import ConfigFileCreator

logger = logging.getLogger(__name__)


class PrometheusOutput(Output):
    def write(self, projects: list):
        creator = ConfigFileCreator(self.main_config)
        project_names = [project['name'] for project in projects]

        base_directory = pathlib.Path(self.config.get('base_directory'))
        base_rule_directory = base_directory.joinpath('rules')
        if not base_rule_directory.exists():
            base_rule_directory.mkdir()

        prometheus_config = creator.create_prometheus_config(
            projects,
            self.manager,
            [
                f'{base_rule_directory}/*.yml',
            ],
        )

        prometheus_config_path = base_directory.joinpath('prometheus.yml')
        with prometheus_config_path.open(mode='w') as file:
            logger.info(f'writing prometheus config file {prometheus_config_path}')
            file.write(yaml.safe_dump(prometheus_config))

        rule_files = creator.create_rule_files(project_names)
        for file_name, file_content in rule_files.items():
            file_path = base_rule_directory.joinpath(file_name)
            with file_path.open(mode='w') as file:
                logger.info(f'writing rule file {file_path}')
                file.write(yaml.safe_dump(file_content))

        for match in base_rule_directory.glob('*.yml'):
            if match.name not in rule_files.keys() and match.name not in self.main_config.get(
                'external_rules_files', []
            ):
                match.unlink()
                logger.info(f'removing old rules file {match}')

        self._reload_units()
