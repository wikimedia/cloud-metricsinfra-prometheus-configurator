import logging
import pathlib

import yaml

from prometheus_configurator.outputs.prometheus import Output
from prometheus_configurator.utils import merge

logger = logging.getLogger(__name__)


class AlertmanagerOutput(Output):
    def _get_alertmanager_routes_receivers(self, projects: list):
        routes = []
        receivers = []

        # TODO: support for more advanced rules, load them from manager
        for project in projects:
            project_name = project.get('name')
            email_to = self._get_project_config(project_name).get('notify_email', [])
            if len(email_to) != 0:
                receivers.append(
                    {
                        'name': f'{project_name}_email',
                        'email_configs': [{'to': email} for email in email_to],
                    }
                )
                routes.append(
                    {'receiver': f'{project_name}_email', 'match': {'project': project_name}}
                )

        return routes, receivers

    def write(self, projects: list):
        am_config = self.main_config.get('alertmanager_config', {})
        am_config = merge(am_config, self.config.get('alertmanager_config', {}))

        routes, receivers = self._get_alertmanager_routes_receivers(projects)

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
            logger.info(f'writing alert manager config file {am_config_path}')
            file.write(yaml.safe_dump(am_config))
