import logging
import pathlib

import yaml

from prometheus_configurator.outputs import Output

logger = logging.getLogger(__name__)


class KarmaAclOutput(Output):
    def default_group_for_project(self, project: str) -> str:
        return self.main_config.get("project_group_format", "{project}").format(
            project=project
        )

    def write(self, projects: list):
        sudo_projects = self.main_config.get("sudo_projects", [])

        rules = [
            {
                "action": "allow",
                "reason": "Members of a sudo project can do anything",
                "scope": {
                    "groups": [
                        self.default_group_for_project(project)
                        for project in sudo_projects
                    ],
                },
            },
        ]

        for project in projects:
            project_name = project.get("name")

            project_details = self.manager.get_project_details(project.get("id"))
            group = project_details.get("acl_group", None)
            if group is None:
                group = self.default_group_for_project(project_name)

            rules.append(
                {
                    "action": "allow",
                    "reason": f"Members of project {project_name} can do anything in that project",
                    "scope": {
                        "groups": [group],
                    },
                    "matchers": {
                        "required": [
                            {
                                "name": "project",
                                "value": project_name,
                            },
                        ],
                    },
                }
            )

        rules.append({"action": "block", "reason": "not allowed"})

        file_path = pathlib.Path(self.config.get("acl_file_path"))

        old_data = file_path.read_text() if file_path.exists() else ""
        new_data = yaml.safe_dump({"rules": rules})

        if old_data != new_data:
            with file_path.open(mode="w") as file:
                logger.info(f"writing karma acl file {file_path}")
                file.write(new_data)
            self._reload_units()
        else:
            logger.info("karma acl file is up to date")
