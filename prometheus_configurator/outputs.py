import pathlib
import subprocess

import yaml

from prometheus_configurator.prometheus import ConfigFileCreator
from prometheus_configurator.utils import merge


class Output:
    def __init__(self, config: dict, main_config: dict):
        self.config = config
        self.main_config = main_config

    def write(self, creator: ConfigFileCreator, projects: list):
        pass

    def _reload_units(self):
        for unit in self.config.get('units_to_reload', []):
            # This will succeed even if Prometheus fails to reload its config
            # In that case, just let it - it will alert shortly
            print(f'reloading systemd unit {unit}')
            subprocess.check_call(['/usr/bin/sudo', '/usr/bin/systemctl', 'reload', unit])


class PrometheusOutput(Output):
    def write(self, creator: ConfigFileCreator, projects: list):
        base_directory = pathlib.Path(self.config.get('base_directory'))
        base_rule_directory = base_directory.joinpath('rules')
        if not base_rule_directory.exists():
            base_rule_directory.mkdir()

        prometheus_config = creator.create_prometheus_config(
            projects,
            [
                f'{base_rule_directory}/*.yml',
            ],
        )

        prometheus_config_path = base_directory.joinpath('prometheus.yml')
        with prometheus_config_path.open(mode='w') as file:
            print(f'writing prometheus config file {prometheus_config_path}')
            file.write(yaml.safe_dump(prometheus_config))

        rule_files = creator.create_rule_files(projects)
        for file_name, file_content in rule_files.items():
            file_path = base_rule_directory.joinpath(file_name)
            with file_path.open(mode='w') as file:
                print(f'writing rule file {file_path}')
                file.write(yaml.safe_dump(file_content))

        for match in base_rule_directory.glob('*.yml'):
            if match.name not in rule_files.keys() and match.name not in self.main_config.get(
                'external_rules_files', []
            ):
                match.unlink()
                print(f'removing old rules file {match}')

        self._reload_units()


class AlertmanagerOutput(Output):
    def write(self, creator: ConfigFileCreator, projects: list):
        am_config = self.main_config.get('alertmanager_config', {})
        am_config = merge(am_config, self.config.get('alertmanager_config', {}))

        routes, receivers = creator.get_alertmanager_routes_receivers(projects)

        am_config = merge(
            am_config,
            {
                'route': {
                    'routes': routes,
                },
                'receivers': receivers,
            },
        )

        base_directory = pathlib.Path(self.config.get('base_directory'))
        am_config_path = base_directory.joinpath('alertmanager.yml')
        with am_config_path.open(mode='w') as file:
            print(f'writing alert manager config file {am_config_path}')
            file.write(yaml.safe_dump(am_config))


def create_output(output_config: dict, main_config: dict):
    kind = output_config.get('kind')
    if kind == 'prometheus':
        return PrometheusOutput(output_config, main_config)
    if kind == 'alertmanager':
        return AlertmanagerOutput(output_config, main_config)
    raise NotImplementedError(f'Output {kind} is not supported.')
