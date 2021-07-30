import logging
import subprocess

from prometheus_configurator.manager import PrometheusManagerClient

logger = logging.getLogger(__name__)


class Output:
    def __init__(self, config: dict, main_config: dict, manager: PrometheusManagerClient):
        self.config = config
        self.main_config = main_config
        self.manager = manager

    def write(self, projects: list):
        pass

    def _get_project_config(self, project: str) -> dict:
        return self.main_config.get('projects', {}).get(project, {})

    def _reload_units(self):
        for unit in self.config.get('units_to_reload', []):
            # This will succeed even if Prometheus fails to reload its config
            # In that case, just let it - it will alert shortly
            logger.info(f'reloading systemd unit {unit}')
            subprocess.check_call(['/usr/bin/sudo', '/usr/bin/systemctl', 'reload', unit])
