from pkg_resources import DistributionNotFound, get_distribution

from prometheus_configurator.manager import PrometheusManagerClient
from prometheus_configurator.outputs import Output
from prometheus_configurator.outputs.alertmanager import AlertmanagerOutput
from prometheus_configurator.outputs.karma_acl import KarmaAclOutput
from prometheus_configurator.outputs.prometheus import PrometheusOutput
from prometheus_configurator.outputs.thanos_rule import ThanosRuleOutput

try:
    __version__: str = get_distribution("prometheus_configurator").version
except DistributionNotFound:
    __version__ = "0.0.0"


def create_output(
    output_config: dict, main_config: dict, manager_client: PrometheusManagerClient
) -> Output:
    kind = output_config.get("kind")
    if kind == "prometheus":
        return PrometheusOutput(output_config, main_config, manager_client)
    if kind == "alertmanager":
        return AlertmanagerOutput(output_config, main_config, manager_client)
    if kind == "karma_acl":
        return KarmaAclOutput(output_config, main_config, manager_client)
    if kind == "thanos_rule":
        return ThanosRuleOutput(output_config, main_config, manager_client)
    raise NotImplementedError(f"Output {kind} is not supported.")
