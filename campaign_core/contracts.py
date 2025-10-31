"""Contract definitions for SMS Campaign Orchestrator"""


from .models import Contact


class OutputContract:
    """Contract for campaign output"""

    @staticmethod
    def validate_csv_header(header: str) -> bool:
        """Validate CSV header matches expected format"""
        expected = "subject_id,phone,priority,access_key,consent_timestamp,is_buyer"
        return header.strip() == expected

    @staticmethod
    def validate_contacts(contacts: list[Contact]) -> bool:
        """Validate contacts list"""
        if not contacts:
            return True
        for contact in contacts:
            if not contact.phone or not contact.access_key:
                return False
        return True

    @staticmethod
    def format_csv(contacts: list[Contact]) -> str:
        """Format contacts as CSV"""
        lines = ["subject_id,phone,priority,access_key,consent_timestamp,is_buyer"]
        for contact in contacts:
            line = f"{contact.subject_id},{contact.phone},{contact.priority},{contact.access_key},{contact.consent_timestamp.isoformat()},{contact.is_buyer}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def format_json(contacts: list[Contact], metadata: dict) -> str:
        """Format as JSON"""
        import json
        data = {
            "contacts": [contact.model_dump() for contact in contacts],
            "metadata": metadata
        }
        return json.dumps(data, indent=2, default=str)
