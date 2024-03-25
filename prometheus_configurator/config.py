# SPDX-FileCopyrightText: 2021-2024 Taavi Väänänen <hi@taavi.wtf>
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from prometheus_configurator.utils import merge

logger = logging.getLogger(__name__)


def load_config_files(paths: list[Path]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for path in paths:
        logger.info(f"loading own configuration from {path}")
        data = merge(yaml.safe_load(path.open(mode="r")), data)

    return data
