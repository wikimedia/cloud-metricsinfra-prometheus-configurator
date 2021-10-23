from prometheus_configurator import PrometheusManagerClient, openstack
from prometheus_configurator.utils import camelcase_projectname


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
            'scheme': rule.get('scheme', 'http'),
            'static_configs': [],
        }

        # TODO: this is currently used for global rules only,
        # and may change when they are loaded from the manager
        if 'metrics_path' in rule:
            job['metrics_path'] = rule['metrics_path']

        if 'openstack_discovery' in rule and rule['openstack_discovery'] is not None:
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

        for static_target in rule.get('static_discovery', []):
            obj = {
                'targets': [f"{static_target['host']}:{static_target['port']}"],
                'labels': {
                    'project': project_name,
                },
            }

            job['static_configs'].append(obj)

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

    def _create_rule(self, rule: dict, name_prefix: str, extra_labels: dict) -> dict:
        return {
            'alert': f"{name_prefix}{rule.get('name')}",
            'expr': rule.get('expr'),
            'for': rule.get('duration'),
            'annotations': rule.get('annotations'),
            'labels': {
                **extra_labels,
                'severity': rule.get('severity'),
            },
        }

    def _create_project_rules(self, rules: list, project_name: str) -> dict:
        labels = {
            'project': project_name,
        }

        return {
            'groups': [
                {
                    'name': project_name,
                    'rules': [
                        self._create_rule(rule, camelcase_projectname(project_name), labels)
                        for rule in rules
                    ],
                }
            ]
        }

    def _create_global_rules(self, rules: list) -> dict:
        return {
            'groups': [
                {
                    'name': 'global',
                    'rules': [self._create_rule(rule, '', {}) for rule in rules],
                }
            ]
        }

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

    def create_rule_files(self, projects: list, manager_client: PrometheusManagerClient) -> dict:
        rule_files = {
            'alerts_global.yml': self._create_global_rules(
                [
                    rule
                    for rule in manager_client.get('/v1/global-alerts')
                    # do not deploy ones that need full global view from Thanos
                    if rule.get('mode') == 'PER_PROJECT'
                ]
            )
        }

        for project in projects:
            project_name = project.get('name')
            project_alert_rules = manager_client.get_project_details(project.get('id')).get(
                'alert_rules'
            )

            if len(project_alert_rules) == 0:
                continue

            rule_files[f'alerts_project_{project_name}.yml'] = self._create_project_rules(
                project_alert_rules, project_name
            )

        return rule_files
