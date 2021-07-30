from prometheus_configurator import PrometheusManagerClient, openstack


class ConfigFileCreator:
    def __init__(self, params: dict):
        self.params = params

        self.openstack_credentials = openstack.read_openstack_configuration(
            self.params['openstack']['credentials']
        )

    def _create_job(self, project: dict, rule: dict) -> dict:
        project_name = project.get('name')
        job = {
            'job_name': f"{project_name}_{rule['name']}",
            'relabel_configs': [],
            'metrics_path': rule.get('path', '/metrics'),
        }

        # TODO: this is currently used for global rules only,
        # and may change when they are loaded from the manager
        if 'metrics_path' in rule:
            job['metrics_path'] = rule['metrics_path']

        if 'openstack_discovery' in rule:
            openstack_config = dict(self.openstack_credentials)
            openstack_config['project_name'] = project_name
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
                    'replacement': project_name,
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

    def _create_scrape_configs(
        self, projects: list, manager_client: PrometheusManagerClient
    ) -> list:
        result = []

        for project in projects:
            for job in self.params.get('global_jobs', []):
                result.append(self._create_job(project, job))
            for job in manager_client.get_project_details(project.get('id')).get('scrapes'):
                result.append(self._create_job(project, job))

        return result

    def _create_rule_group(self, group: dict, name_prefix: str) -> dict:
        # TODO: perform validation, etc
        return {'name': f"{name_prefix}{group['name']}", 'rules': group.get('rules', [])}

    def _create_rule_file(self, rule_groups: list, name_prefix: str = '') -> dict:
        return {'groups': [self._create_rule_group(group, name_prefix) for group in rule_groups]}

    def create_prometheus_config(
        self, projects: list, manager_client: PrometheusManagerClient, rule_files_paths: list
    ) -> dict:
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
            'scrape_configs': self._create_scrape_configs(projects, manager_client),
        }

    def get_project_config(self, project: str) -> dict:
        return self.params.get('projects', {}).get(project, {})

    def create_rule_files(self, projects: list) -> dict:
        rule_files = {
            # TODO: load from prometheus-manager?
            # also, use thanos rule for some but not all global rules
            'alerts_global.yml': self._create_rule_file(self.params.get('global_alert_groups', []))
        }

        for project in projects:
            # TODO: load from prometheus-manager
            project_alert_groups = self.get_project_config(project).get('alert_groups', [])
            if len(project_alert_groups) == 0:
                continue
            rule_files[f'alerts_project_{project}.yml'] = self._create_rule_file(
                project_alert_groups, f'project_{project}_'
            )

        return rule_files
