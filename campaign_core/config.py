# campaign_core/config.py
from __future__ import annotations
import os
from typing import Dict
from datetime import datetime

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

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_ENDPOINTS = {
    'activities_search': '/activities/search',
    'job_details': '/jobs/{job_uuid}',
    'job_subjects': '/jobs/{job_uuid}/subjects',
    'subject_access_keys': '/jobs/{job_uuid}/subjects/{subject_uuid}/accesskeys',
}

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================

PERFORMANCE_CONFIG = {
    'timeout': 30,
    'retry_attempts': 3,
    'retry_backoff': 1.5,
    'max_concurrent_jobs': 10,
}

# ============================================================================
# SMS DEFAULTS
# ============================================================================

SMS_DEFAULTS = {
    'message_template': 'Your photos are ready!',
    'sender_id': 'Netlife',
}

# ============================================================================
# ACTIVITY CONFIGURATION
# ============================================================================

ACTIVITY_CONFIG = {
    'target_status': 'in-webshop',  # Status for activities with subjects in webshop/selling
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()