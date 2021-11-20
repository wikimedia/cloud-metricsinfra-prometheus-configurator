import logging
import pathlib

import yaml

from prometheus_configurator.outputs import Output

logger = logging.getLogger(__name__)


class KarmaAclOutput(Output):
    def project_for_group(self, project: str) -> str:
        return self.main_config.get('project_group_format', '{project}').format(project=project)

    def write(self, projects: list):
        sudo_projects = self.main_config.get('sudo_projects', [])

        rules = [
            {
                'action': 'allow',
                'reason': 'Members of a sudo project can do anything',
                'scope': {
                    'groups': [self.project_for_group(project) for project in sudo_projects],
                },
            },
        ]

        for project in projects:
            project_name = project.get('name')
            rules.append(
                {
                    'action': 'allow',
                    'reason': f'Members of project {project_name} can do anything in that project',
                    'scope': {
                        'groups': [self.project_for_group(project_name)],
                    },
                    'matchers': {
                        'required': [
                            {
                                'name': 'project',
                                'value': project_name,
                            },
                        ],
                    },
                }
            )

        rules.append({'action': 'block', 'reason': 'not allowed'})

        file_path = pathlib.Path(self.config.get('acl_file_path'))

        old_data = file_path.read_text() if file_path.exists() else ''
        new_data = yaml.safe_dump({'rules': rules})

        if old_data != new_data:
            with file_path.open(mode='w') as file:
                logger.info(f'writing karma acl file {file_path}')
                file.write(new_data)
                self._reload_units()
        else:
            logger.info('karma acl file is up to date')
