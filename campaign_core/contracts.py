"""Contract definitions for SMS Campaign Orchestrator"""


from .models import Contact


class OutputContract:
    """Contract for campaign output"""

    @staticmethod
    def validate_csv_header(header: str) -> bool:
        """Validate CSV header matches expected format"""
        expected = "portal,job_uuid,job_name,subject_uuid,external_id,first_name,last_name,parent_name,phone_number,phone_number_2,email,email_2,country,group,buyer,access_code,url,custom_gallery_url,sms_marketing_consent,sms_marketing_timestamp,sms_transactional_consent,sms_transactional_timestamp,activity_uuid,activity_name,registered_user,registered_user_email,registered_user_uuid,resolution_strategy"
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
        lines = ["portal,job_uuid,job_name,subject_uuid,external_id,first_name,last_name,parent_name,phone_number,phone_number_2,email,email_2,country,group,buyer,access_code,url,custom_gallery_url,sms_marketing_consent,sms_marketing_timestamp,sms_transactional_consent,sms_transactional_timestamp,activity_uuid,activity_name,registered_user,registered_user_email,registered_user_uuid,resolution_strategy"]
        for contact in contacts:
            line = ",".join([
                contact.portal,
                contact.job_uuid,
                contact.job_name,
                contact.subject_uuid,
                contact.external_id or "",
                contact.first_name or "",
                contact.last_name or "",
                contact.parent_name or "",
                contact.phone_number,
                contact.phone_number_2 or "",
                contact.email or "",
                contact.email_2 or "",
                contact.country,
                contact.group or "",
                contact.buyer,
                contact.access_code,
                contact.url,
                contact.custom_gallery_url,
                contact.sms_marketing_consent,
                contact.sms_marketing_timestamp,
                contact.sms_transactional_consent,
                contact.sms_transactional_timestamp,
                contact.activity_uuid,
                contact.activity_name,
                contact.registered_user,
                contact.registered_user_email or "",
                contact.registered_user_uuid or "",
                contact.resolution_strategy
            ])
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
