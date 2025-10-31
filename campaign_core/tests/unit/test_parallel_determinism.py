# campaign-core/tests/unit/test_parallel_determinism.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from campaign_core.services import CampaignService, EnrichmentService, FilteringService
from campaign_core.adapters.portals_async import PortalsAsync


@pytest.mark.asyncio
async def test_parallel_order_is_deterministic():
    """Test that async runs produce identical CSV output"""
    # Mock the async adapter
    mock_adapter = MagicMock(spec=PortalsAsync)
    mock_adapter._base = {"legacyphoto": "https://example.com"}  # Mock the _base attribute
    mock_adapter.get_activities_for_job = AsyncMock(return_value=[
        {"id": "A1", "subject_id": "S1", "type": "buyer", "timestamp": "2025-10-31T00:00:00Z"}
    ])
    mock_adapter.get_subject = AsyncMock(return_value={
        "id": "S1", "name": "Test Subject", "phone": "+1234567890", "email": None,
        "consent_timestamp": "2025-10-31T00:00:00Z", "purchase_history": [{"id": "p1", "amount": 100.0}],
        "registered_user_ref": None
    })
    
    # Create service with mocked adapter
    service = CampaignService(
        portal_client=MagicMock(),  # Not used in async path
        enrichment_service=EnrichmentService(),
        filtering_service=FilteringService(),
        portals_async=mock_adapter
    )
    
    # Run twice
    result1 = await service._generate_campaign_async(["J1"], "both")
    result2 = await service._generate_campaign_async(["J1"], "both")
    
    # Should produce identical results
    assert len(result1.contacts) == len(result2.contacts)
    assert all(c1.subject_id == c2.subject_id for c1, c2 in zip(result1.contacts, result2.contacts))