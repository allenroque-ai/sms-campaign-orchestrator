"""Contract tests for SMS Campaign Orchestrator"""

import json
from datetime import datetime

from campaign_core.contracts import OutputContract
from campaign_core.models import Contact


def test_csv_header_contract():
    """Test CSV header matches expected format"""
    csv_output = OutputContract.format_csv([])
    lines = csv_output.split("\n")
    header = lines[0]
    assert OutputContract.validate_csv_header(header)


def test_csv_format_contract():
    """Test CSV format for contacts"""
    contacts = [
        Contact(
            subject_id="sub1",
            phone="+1234567890",
            priority=1,
            access_key="key123",
            consent_timestamp=datetime.now(),
            is_buyer=True
        )
    ]
    csv_output = OutputContract.format_csv(contacts)
    lines = csv_output.split("\n")
    assert len(lines) == 2  # header + 1 data
    data_line = lines[1]
    assert "sub1" in data_line
    assert "+1234567890" in data_line


def test_json_format_contract():
    """Test JSON format matches schema"""
    contacts = [
        Contact(
            subject_id="sub1",
            phone="+1234567890",
            priority=1,
            access_key="key123",
            consent_timestamp=datetime.now(),
            is_buyer=True
        )
    ]
    metadata = {"test": "data"}
    json_output = OutputContract.format_json(contacts, metadata)
    data = json.loads(json_output)

    assert "contacts" in data
    assert "metadata" in data
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["subject_id"] == "sub1"


def test_contacts_validation_contract():
    """Test contact validation"""
    valid_contacts = [
        Contact(
            subject_id="sub1",
            phone="+1234567890",
            priority=1,
            access_key="key123",
            consent_timestamp=datetime.now(),
            is_buyer=True
        )
    ]
    assert OutputContract.validate_contacts(valid_contacts)

    invalid_contacts = [
        Contact(
            subject_id="sub1",
            phone="",  # invalid
            priority=1,
            access_key="key123",
            consent_timestamp=datetime.now(),
            is_buyer=True
        )
    ]
    assert not OutputContract.validate_contacts(invalid_contacts)


def test_empty_contacts_contract():
    """Test handling of empty contact lists"""
    assert OutputContract.validate_contacts([])
    csv_output = OutputContract.format_csv([])
    lines = csv_output.split("\n")
    assert len(lines) == 1  # just header
    assert OutputContract.validate_csv_header(lines[0])
