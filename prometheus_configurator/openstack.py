import yaml


def read_openstack_configuration(file: str):
    with open(file, 'r') as openstack_file:
        data = yaml.safe_load(openstack_file)
        return {
            'all_tenants': False,
            'domain_name': data['OS_PROJECT_DOMAIN_NAME'],
            'identity_endpoint': data['OS_AUTH_URL'],
            'password': data['OS_PASSWORD'],
            'refresh_interval': '5m',
            'region': data['OS_REGION_NAME'],
            'username': data['OS_USERNAME'],
        }
