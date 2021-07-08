import yaml


def load_config_files(paths: list):
    data = {}
    for path in paths:
        print(f'loading own configuration from {path}')
        data = merge(yaml.safe_load(path.open(mode='r')), data)

    return data


# Based on https://github.com/wikimedia/wikimedia-bots-jouncebot/blob/master/jouncebot/configloader.py
def merge(new_vals, existing_obj):
    if isinstance(new_vals, dict) and isinstance(existing_obj, dict):
        for k, v in list(existing_obj.items()):
            if k not in new_vals:
                new_vals[k] = v
            else:
                new_vals[k] = merge(new_vals[k], v)
    elif isinstance(new_vals, list) and isinstance(existing_obj, list):
        return [*new_vals, *existing_obj]
    return new_vals
