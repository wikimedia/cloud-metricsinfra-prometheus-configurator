# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations


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


def camelcase_projectname(original: str) -> str:
    return "".join([part.title() for part in original.split("-")])
