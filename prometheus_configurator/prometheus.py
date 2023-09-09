from __future__ import annotations

import re
from typing import Any, Optional

from prometheus_configurator import PrometheusManagerClient, openstack
from prometheus_configurator.utils import camelcase_projectname


class ConfigFileCreator:
    def __init__(self, params: dict):
        self.params = params

        self.openstack_credentials = openstack.read_openstack_configuration(
            self.params["openstack"]["credentials"]
        )

    def _format_blackbox_module(self, config: dict) -> dict:
        module = {
            "prober": config["type"],
        }

        if module["prober"] == "http":
            module["http"] = {
                "method": config["method"],
                "no_follow_redirects": not config["follow_redirects"],
            }

            if config["headers"]:
                module["http"]["headers"] = config["headers"]

            if config["valid_status_codes"]:
                module["http"]["valid_status_codes"] = config["valid_status_codes"]

            if config["require_body_match"]:
                module["http"]["fail_if_body_not_matches_regexp"] = config[
                    "require_body_match"
                ]

            if config["require_body_not_match"]:
                module["http"]["fail_if_body_matches_regexp"] = config[
                    "require_body_not_match"
                ]

        return module

    def _create_job(
        self,
        project: dict,
        rule: dict,
        images: list[str],
        blackbox_address: Optional[str],
    ) -> tuple[Optional[dict], Optional[dict]]:
        project_name = project["name"]
        job = {
            "job_name": f"{project_name}_{rule['name']}",
            "relabel_configs": [],
            "metrics_path": rule.get("path", "/metrics"),
            "scheme": rule.get("scheme", "http"),
            "params": {},
        }

        # TODO: this is currently used for global rules only,
        # and may change when they are loaded from the manager
        if "metrics_path" in rule:
            job["metrics_path"] = rule["metrics_path"]

        blackbox = None

        if "blackbox" in rule and rule["blackbox"]:
            if not blackbox_address:
                return None, None

            job["metrics_path"] = "/probe"
            job["scheme"] = "http"
            job["params"]["module"] = [f"{project_name}_{rule['name']}"]

            job["relabel_configs"].append(
                {"source_labels": ["__address__"], "target_label": "__param_target"},
            )
            job["relabel_configs"].append(
                {
                    "target_label": "__address__",
                    "replacement": blackbox_address,
                }
            )

            blackbox = self._format_blackbox_module(rule["blackbox"])

        if "openstack_discovery" in rule and rule["openstack_discovery"] is not None:
            openstack_config = dict(self.openstack_credentials)
            openstack_config["project_name"] = project_name
            openstack_config["port"] = rule["openstack_discovery"]["port"]
            openstack_config["role"] = "instance"

            job["openstack_sd_configs"] = [openstack_config]

            job["relabel_configs"].append(
                {
                    "action": "keep",
                    "source_labels": ["__meta_openstack_instance_image"],
                    "regex": "|".join([re.escape(image) for image in images]),
                }
            )

            if "name_regex" in rule["openstack_discovery"]:
                job["relabel_configs"].append(
                    {
                        "action": "keep",
                        "source_labels": ["__meta_openstack_instance_name"],
                        "regex": rule["openstack_discovery"]["name_regex"],
                    }
                )
            job["relabel_configs"].append(
                {
                    "source_labels": ["__meta_openstack_project_id"],
                    "target_label": "project",
                    "replacement": project_name,
                }
            )
            job["relabel_configs"].append(
                {
                    "source_labels": ["job"],
                    "target_label": "job",
                    "replacement": rule["name"],
                }
            )
            job["relabel_configs"].append(
                {
                    "source_labels": ["__meta_openstack_instance_name"],
                    "target_label": "instance",
                }
            )
            job["relabel_configs"].append(
                {
                    "action": "keep",
                    "source_labels": ["__meta_openstack_instance_status"],
                    "regex": "ACTIVE",
                }
            )

        static_targets = [
            f"{target['host']}:{target['port']}"
            for target in rule.get("static_discovery", [])
        ]
        if static_targets:
            if blackbox:
                static_targets = [
                    f"{rule['scheme']}://{target}{rule['path']}"
                    for target in static_targets
                ]

            obj = {
                "targets": static_targets,
                "labels": {
                    "project": project_name,
                },
            }

            job["static_configs"] = [obj]

        return job, blackbox

    def _create_scrape_configs(
        self,
        projects: list,
        manager_client: PrometheusManagerClient,
        blackbox_address: Optional[str],
    ) -> tuple[list, dict[str, Any]]:
        scrape_configs: list[dict] = []
        blackbox_configs = {}
        images = [
            image["openstack_id"]
            for image in manager_client.get_supported_openstack_images()
        ]

        for project in projects:
            project_name = project["name"]
            project_details = manager_client.get_project_details(project["id"])
            project_blackbox_modules = {}

            for job in self.params.get("global_jobs", []):
                job_scrape, _ = self._create_job(project, job, images, blackbox_address)
                if job_scrape:
                    scrape_configs.append(job_scrape)

            for job in project_details.get("scrapes"):
                job_scrape, job_blackbox = self._create_job(
                    project, job, images, blackbox_address
                )

                if not job_scrape:
                    continue

                scrape_configs.append(job_scrape)
                if job_blackbox:
                    project_blackbox_modules[
                        f"{project_name}_{job['name']}"
                    ] = job_blackbox

            if project_blackbox_modules:
                blackbox_configs[f"project_{project_name}.yml"] = {
                    "modules": project_blackbox_modules
                }

        return scrape_configs, blackbox_configs

    def _create_rule(self, rule: dict, name_prefix: str, extra_labels: dict) -> dict:
        return {
            "alert": f"{name_prefix}{rule.get('name')}",
            "expr": rule.get("expr"),
            "for": rule.get("duration"),
            "annotations": rule.get("annotations"),
            "labels": {
                **extra_labels,
                "severity": rule.get("severity"),
            },
        }

    def _create_project_rules(self, rules: list, project_name: str) -> dict:
        labels = {
            "project": project_name,
        }

        return {
            "groups": [
                {
                    "name": project_name,
                    "rules": [
                        self._create_rule(
                            rule, camelcase_projectname(project_name), labels
                        )
                        for rule in rules
                    ],
                }
            ]
        }

    def _create_global_rules(self, rules: list) -> dict:
        return {
            "groups": [
                {
                    "name": "global",
                    "rules": [self._create_rule(rule, "", {}) for rule in rules],
                }
            ]
        }

    def create_prometheus_config(
        self,
        projects: list,
        manager_client: PrometheusManagerClient,
        rule_files_paths: list,
        blackbox_address: Optional[str],
    ) -> tuple[dict, dict[str, Any]]:
        scrape_configs, blackbox_modules = self._create_scrape_configs(
            projects,
            manager_client,
            blackbox_address,
        )

        prometheus_config = {
            "global": {
                "scrape_interval": "60s",
                "external_labels": self.params.get("external_labels", []),
            },
            "alerting": {
                "alert_relabel_configs": self._create_alert_relabel_configs(
                    projects=projects
                ),
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": self.params["alertmanager_hosts"],
                            }
                        ],
                    },
                ],
            },
            "rule_files": rule_files_paths,
            "scrape_configs": scrape_configs,
        }

        return prometheus_config, blackbox_modules

    def _create_alert_relabel_configs(
        self, projects: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        configs: list[dict[str, Any]] = [
            {
                "action": "labeldrop",
                "regex": "replica",
            }
        ]

        for project in projects:
            if not project["extra_labels"]:
                continue

            for label_name, label_value in project["extra_labels"].items():
                # Add a new label named `label_name` with value `label_value` when the project
                # label matches the project name. For extra syntax:
                # https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config
                configs.append(
                    {
                        "action": "replace",
                        "source_labels": ["project"],
                        "regex": project["name"],
                        "target_label": label_name,
                        "replacement": label_value,
                    }
                )

        return configs

    def get_project_config(self, project: str) -> dict:
        return self.params.get("projects", {}).get(project, {})

    def create_rule_files(
        self, projects: list, manager_client: PrometheusManagerClient
    ) -> dict:
        rule_files = {
            "alerts_global.yml": self._create_global_rules(
                [
                    rule
                    for rule in manager_client.get("/v1/global-alerts")
                    # do not deploy ones that need full global view from Thanos
                    if rule.get("mode") == "PER_PROJECT"
                ]
            )
        }

        for project in projects:
            project_name = project.get("name")
            project_details = manager_client.get_project_details(project["id"])
            project_alert_rules = project_details["alert_rules"]

            if len(project_alert_rules) == 0:
                continue

            rule_files[
                f"alerts_project_{project_name}.yml"
            ] = self._create_project_rules(
                rules=project_alert_rules,
                project_name=project_name,
            )

        return rule_files

    def create_thanos_rule_file(self, manager_client: PrometheusManagerClient) -> dict:
        return self._create_global_rules(
            [
                rule
                for rule in manager_client.get("/v1/global-alerts")
                if rule.get("mode") == "GLOBAL"
            ]
        )
