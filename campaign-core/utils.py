"""Utility functions for SMS Campaign Orchestrator"""

import hashlib
from datetime import datetime
from typing import List
from .models import Contact


def generate_access_key(subject_id: str, phone: str) -> str:
    """Generate deterministic access key"""
    data = f"{subject_id}:{phone}:{datetime.now().date()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def mask_pii(text: str) -> str:
    """Mask PII in logs"""
    # Simple masking for phone numbers
    import re
    return re.sub(r'\+\d{3}\d{3}\d{4}', '+XXX-XXX-XXXX', text)


def prioritize_contacts(contacts: List[Contact]) -> List[Contact]:
    """Sort contacts by priority"""
    return sorted(contacts, key=lambda c: c.priority)