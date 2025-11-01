# campaign_core/config.py
from __future__ import annotations
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