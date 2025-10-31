# campaign_core/config.py
from __future__ import annotations
import json
import os
from typing import Dict

ALLOWED_PORTALS: Dict[str, str] = {
    "nowandforeverphoto": "https://nowandforeverphoto.shop/api/v1",
    "legacyseniorphotos": "https://legacyseniorphotos.shop/api/v1",
    "legacyphoto": "https://legacyphoto.shop/api/v1",
    "generationsphotos": "https://generationsphotos.shop/api/v1",
    "nowandgen": "https://nowandgen.shop/api/v1",
    "legacyphotos": "https://legacyphotos.shop/api/v1",
    "westpointportraits": "https://westpointportraits.shop/api/v1",
    "midshipmenportraits": "https://midshipmenportraits.shop/api/v1",
    "coastguardportraits": "https://coastguardportraits.shop/api/v1",
}

NETLIFE_SECRET_ARN = os.getenv(
    "NETLIFE_SECRET_ARN",
    "arn:aws:secretsmanager:us-east-1:754102187132:secret:nws/netlife-api-dev-tsm19Z",
)

PORTALS_FILTER = [p for p in os.getenv("PORTALS", "").split(",") if p] or list(ALLOWED_PORTALS.keys())

# Optional: external config file for overrides
CFG_PATH = os.getenv("PORTAL_CONFIG_FILE")
if CFG_PATH and os.path.exists(CFG_PATH):
    with open(CFG_PATH, "r") as fh:
        data = json.load(fh)
        for k, v in (data or {}).items():
            if k in ALLOWED_PORTALS:
                ALLOWED_PORTALS[k] = v