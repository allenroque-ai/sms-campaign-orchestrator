# campaign-core/tests/unit/test_retries.py
import pytest

@pytest.mark.skip(reason="Async adapter integration not fully implemented")
@pytest.mark.asyncio
async def test_retries_on_429(fake_async_portal_flaky):
    rows = await fake_async_portal_flaky.generate([...], concurrency=4, retries=3)
    assert rows and fake_async_portal_flaky.retry_counts["/subjects"] >= 1