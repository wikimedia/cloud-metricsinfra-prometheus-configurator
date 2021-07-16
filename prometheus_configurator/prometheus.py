from prometheus_configurator import openstack


class ConfigFileCreator:
    def __init__(self, params: dict):
        self.params = params
        self.projects = self.params['projects'].keys()

        self.openstack_credentials = openstack.read_openstack_configuration(
            self.params['openstack']['credentials']
        )

    def _create_job(self, project: str, rule: dict) -> dict:
        job = {
            'job_name': f"{project}_{rule['name']}",
            'relabel_configs': [],
        }

        if 'metrics_path' in rule:
            job['metrics_path'] = rule['metrics_path']

        if 'openstack_discovery' in rule:
            openstack_config = dict(self.openstack_credentials)
            openstack_config['project_name'] = project
            openstack_config['port'] = rule['openstack_discovery']['port']
            openstack_config['role'] = 'instance'

            job['openstack_sd_configs'] = [openstack_config]
            if 'name_regex' in rule['openstack_discovery']:
                job['relabel_configs'].append(
                    {
                        'action': 'keep',
                        'source_labels': ['__meta_openstack_instance_name'],
                        'regex': rule['openstack_discovery']['name_regex'],
                    }
                )
            job['relabel_configs'].append(
                {
                    'source_labels': ['__meta_openstack_project_id'],
                    'target_label': 'project',
                    'replacement': project,
                }
            )
            job['relabel_configs'].append(
                {
                    'source_labels': ['job'],
                    'target_label': 'job',
                    'replacement': rule['name'],
                }
            )
            job['relabel_configs'].append(
                {
                    'source_labels': ['__meta_openstack_instance_name'],
                    'target_label': 'instance',
                }
            )
            job['relabel_configs'].append(
                {
                    'action': 'keep',
                    'source_labels': ['__meta_openstack_instance_status'],
                    'regex': 'ACTIVE',
                }
            )

        return job

    def _create_internal_prometheus_job(self) -> dict:
        # TODO: make configurable: metrics_path, targets (support clustering)
        # (or just configure to scrape itself)
        return {
            'job_name': 'prometheus',
            'metrics_path': '/cloud/metrics',
            'static_configs': [
                {
                    'targets': ['localhost:9900'],
                }
            ],
        }

    def _create_internal_alertmanager_job(self) -> dict:
        return {
            'job_name': 'alertmanager',
            'metrics_path': '/metrics',
            'static_configs': [
                {
                    'targets': self.params['alertmanager_hosts'],
                }
            ],
        }

    def _create_scrape_configs(self, projects: list) -> list:
        result = []
        for project in projects:
            for job in self.params.get('global_jobs', []):
                result.append(self._create_job(project, job))
            for job in self.get_project_config(project).get('jobs', []):
                result.append(self._create_job(project, job))

        result.append(self._create_internal_prometheus_job())
        result.append(self._create_internal_alertmanager_job())
        return result

    def _create_rule_group(self, group: dict, name_prefix: str) -> dict:
        # TODO: perform validation, etc
        return {'name': f"{name_prefix}{group['name']}", 'rules': group.get('rules', [])}

    def _create_rule_file(self, rule_groups: list, name_prefix: str = '') -> dict:
        return {'groups': [self._create_rule_group(group, name_prefix) for group in rule_groups]}

    def create_prometheus_config(self, projects: list, rule_files_paths: list) -> dict:
        return {
            'global': {
                'scrape_interval': '60s',
            },
            'alerting': {
                'alert_relabel_configs': [
                    {
                        'action': 'labeldrop',
                        'regex': 'replica',
                    }
                ],
                'alertmanagers': [
                    {
                        'static_configs': [
                            {
                                'targets': self.params['alertmanager_hosts'],
                            }
                        ],
                    },
                ],
            },
            'rule_files': rule_files_paths,
            'scrape_configs': self._create_scrape_configs(projects),
        }

    def get_project_config(self, project: str) -> dict:
        return self.params['projects'].get(project, {})

    def create_rule_files(self, projects: list) -> dict:
        rule_files = {
            'alerts_global.yml': self._create_rule_file(self.params.get('global_alert_groups', []))
        }

        for project in projects:
            project_alert_groups = self.get_project_config(project).get('alert_groups', [])
            if len(project_alert_groups) == 0:
                continue
            rule_files[f'alerts_project_{project}.yml'] = self._create_rule_file(
                project_alert_groups, f'project_{project}_'
            )

        return rule_files

    def get_alertmanager_routes_receivers(self, projects: list):
        routes = []
        receivers = []

        # TODO: support for more advanced rules
        for project in projects:
            email_to = self.get_project_config(project).get('notify_email', [])
            if len(email_to) != 0:
                receivers.append(
                    {
                        'name': f'{project}_email',
                        'email_configs': [{'to': email} for email in email_to],
                    }
                )
                routes.append({'receiver': f'{project}_email', 'match': {'project': project}})

        return routes, receivers

    def get_defined_projects(self) -> list:
        return self.projects
