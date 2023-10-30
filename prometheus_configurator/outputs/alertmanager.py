from __future__ import annotations

import logging
import pathlib
from typing import Any, List

import yaml

from prometheus_configurator.outputs import Output
from prometheus_configurator.utils import merge

logger = logging.getLogger(__name__)


class AlertmanagerOutput(Output):
    def _format_webhook_configs(self, members: List[dict]) -> List[dict]:
        irc_base = self.main_config.get("alert_routing", {}).get(
            "irc_base", "http://invalid/"
        )
        return [
            # TODO: add support for arbitrary user-supplied webhook
            {"url": f"{irc_base}{member['value'].lstrip('#')}"}
            for member in members
            if member.get("type") == "IRC"
        ]

    def _format_contact_group(self, contact_group: dict[str, Any]) -> dict[str, Any]:
        project_name = contact_group["project"].get("name")
        name = contact_group.get("name")
        members = contact_group.get("members", [])

        return {
            "name": f"{project_name}_{name}",
            "email_configs": [
                {
                    "to": member.get("value"),
                    "send_resolved": True,
                    "headers": {"Auto-Submitted": "auto-generated"},
                }
                for member in members
                if member.get("type") == "EMAIL"
            ],
            "webhook_configs": self._format_webhook_configs(members),
        }

    def _get_receivers(self) -> List[dict]:
        return [
            self._format_contact_group(contact_group)
            for contact_group in self.manager.get_contact_groups()
        ]

    def _get_project_routes(self, projects: list):
        routes = []

        # TODO: support for more advanced rules, load them from manager
        for project in projects:
            project_name = project.get("name")
            project_details = self.manager.get_project_details(project.get("id"))

            contact_group = project_details.get("default_contact_group", None)

            if contact_group is not None:
                group_project_name = contact_group.get("project").get("name")
                group_name = contact_group.get("name")

                routes.append(
                    {
                        "receiver": f"{group_project_name}_{group_name}",
                        "match": {"project": project_name},
                    }
                )

        return routes

    def write(self, projects: list):
        am_config = self.main_config.get("alertmanager_config", {})
        am_config = merge(am_config, self.config.get("alertmanager_config", {}))

        am_config = merge(
            am_config,
            {
                "route": {
                    "routes": self._get_project_routes(projects),
                },
                "receivers": self._get_receivers(),
            },
        )

        base_directory = pathlib.Path(self.config["base_directory"])
        am_config_path = base_directory.joinpath("alertmanager.yml")

        old_config = am_config_path.read_text() if am_config_path.exists() else ""
        new_config = yaml.safe_dump(am_config)

        if old_config != new_config:
            with am_config_path.open(mode="w") as file:
                logger.info(f"writing alert manager config file {am_config_path}")
                file.write(new_config)
            self._reload_units()
        else:
            logger.info("alert manager config is up to date")
