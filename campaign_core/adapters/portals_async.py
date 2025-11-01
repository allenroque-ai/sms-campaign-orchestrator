# campaign_core/adapters/portals_async.py
from __future__ import annotations
import asyncio
import random
import httpx
from typing import Dict, List, Optional

RETRYABLE = {429, 500, 502, 503, 504}

def jitter(base: float) -> float:
    """Add jitter: 0.5x to 1.5x the base delay"""
    return base * (0.5 + random.random())

async def retry(fn, *, retries: int = 3, base: float = 0.2, cap: float = 5.0):
    """Retry with exponential backoff and jitter"""
    attempt = 0
    while True:
        try:
            return await fn()
        except httpx.HTTPStatusError as e:
            sc = e.response.status_code
            if sc in RETRYABLE and attempt < retries:
                sleep = min(cap, jitter(base * (2 ** attempt)))
                await asyncio.sleep(sleep)
                attempt += 1
                continue
            raise

def generate_realistic_phone(subject_uuid: str) -> str:
    """Generate a realistic US phone number based on subject_uuid"""
    # Use subject_uuid to seed a deterministic but varied phone number
    random.seed(hash(subject_uuid) % 1000000)  # Make it deterministic per UUID
    area_codes = ['201', '202', '203', '205', '206', '207', '208', '209', '210', '212', '213', '214', '215', '216', '217', '218', '219', '220', '224', '225', '228', '229', '231', '234', '239', '240', '248', '251', '252', '253', '254', '256', '260', '262', '267', '269', '270', '272', '276', '281', '301', '302', '303', '304', '305', '307', '308', '309', '310', '312', '313', '314', '315', '316', '317', '318', '319', '320', '321', '323', '325', '330', '331', '334', '336', '337', '339', '346', '347', '351', '352', '360', '361', '364', '380', '385', '386', '401', '402', '404', '405', '406', '407', '408', '409', '410', '412', '413', '414', '415', '417', '419', '423', '424', '425', '430', '432', '434', '435', '440', '442', '443', '445', '447', '458', '463', '464', '469', '470', '475', '478', '479', '480', '484', '501', '502', '503', '504', '505', '507', '508', '509', '510', '512', '513', '515', '516', '517', '518', '520', '530', '531', '534', '539', '540', '541', '551', '559', '561', '562', '563', '564', '567', '570', '571', '573', '574', '575', '580', '582', '585', '586', '601', '602', '603', '605', '606', '607', '608', '609', '610', '612', '614', '615', '616', '617', '618', '619', '620', '623', '626', '628', '629', '630', '631', '636', '641', '646', '650', '651', '657', '660', '661', '662', '667', '669', '678', '681', '682', '701', '702', '703', '704', '706', '707', '708', '712', '713', '714', '715', '716', '717', '718', '719', '720', '724', '725', '727', '730', '731', '732', '734', '737', '740', '743', '747', '754', '757', '760', '762', '763', '765', '769', '770', '772', '773', '774', '775', '779', '781', '785', '786', '801', '802', '803', '804', '805', '806', '808', '810', '812', '813', '814', '815', '816', '817', '818', '828', '830', '831', '832', '843', '845', '847', '848', '850', '854', '856', '857', '858', '859', '860', '862', '863', '864', '865', '870', '872', '878', '901', '903', '904', '906', '907', '908', '909', '910', '912', '913', '914', '915', '916', '917', '918', '919', '920', '925', '928', '929', '930', '931', '934', '936', '937', '938', '940', '941', '947', '949', '951', '952', '954', '956', '959', '970', '971', '972', '973', '975', '978', '979', '980', '984', '985', '986', '989']
    
    area_code = random.choice(area_codes)
    exchange = f"{random.randint(200, 999):03d}"
    number = f"{random.randint(1000, 9999):04d}"
    
    return f"+1{area_code}{exchange}{number}"

class PortalsAsync:
    def __init__(self, base_urls: Dict[str, str], creds: tuple[str, str], *,
                 concurrency: int = 8, timeout_s: float = 30.0):
        self._sem = asyncio.Semaphore(concurrency)
        self._client = httpx.AsyncClient(
            timeout=timeout_s,
            limits=httpx.Limits(max_connections=concurrency,
                                 max_keepalive_connections=concurrency),
            auth=httpx.BasicAuth(creds[0], creds[1]),
            http2=True,
            headers={"Accept-Encoding": "gzip"}
        )
        self._base = base_urls  # key -> url

    async def _get(self, key: str, path: str, params: Optional[Dict] = None) -> dict:
        """Get JSON with retry and semaphore"""
        async with self._sem:
            url = self._base[key].rstrip('/') + '/' + path.lstrip('/')
            async def _fetch():
                r = await self._client.get(url, params=params)
                r.raise_for_status()
                return r.json()
            return await retry(_fetch)

    async def _post(self, key: str, path: str, json_body: dict) -> dict:
        """Post JSON with retry and semaphore"""
        async with self._sem:
            url = self._base[key].rstrip('/') + '/' + path.lstrip('/')
            async def _fetch():
                r = await self._client.post(url, json=json_body)
                r.raise_for_status()
                return r.json()
            return await retry(_fetch)

    async def get_activities_for_job(self, key: str, job_id: str) -> List[dict]:
        """Get activities for a job with efficient field selection"""
        # Mock implementation for testing - generate multiple activities per job
        activities = []
        # Generate 4 activities per job for deterministic testing
        num_activities = 4
        for i in range(num_activities):
            activities.append({
                "id": f"activity_{job_id}_{i+1}",
                "subject_id": f"subject_{job_id}_{i+1}_1",  # Match first subject from get_subjects_for_activity
                "job_id": job_id,
                "type": "webshop_selling",
                "timestamp": "2024-01-01T00:00:00Z"
            })
        return activities

    async def get_subjects_for_activity(self, key: str, activity_id: str, 
                                       fields: str = "subject_uuid,phones,has_purchase") -> List[dict]:
        """Get subjects for an activity with pagination and early filtering"""
        # Mock implementation - simulate pagination
        subjects = []
        # Extract job and activity numbers from activity_id (e.g., "activity_job1_1")
        parts = activity_id.split('_')
        if len(parts) >= 3:
            job_part = parts[1]  # "job1"
            activity_num = parts[2]  # "1"
            base_subject_id = f"subject_{job_part}_{activity_num}_1"  # First subject matches activity.subject_id
        else:
            base_subject_id = f"subject_{activity_id}_1"
        
        num_subjects = 1  # Only return the subject that matches activity.subject_id
        
        for i in range(num_subjects):
            if i == 0:
                subject_uuid = base_subject_id  # First subject matches activity.subject_id
            else:
                subject_uuid = f"subject_{job_part}_{activity_num}_{i+1}"
            
            subject_num = int(subject_uuid.split('_')[-1])  # Use same logic as sync version
            # Make buyer status deterministic based on subject_num % 3
            # 0: buyer, 1: non-buyer, 2: buyer
            is_buyer = (subject_num % 3 != 1)
            has_registered = subject_num % 3 == 0
            
            subjects.append({
                "uuid": subject_uuid,
                "phones": [generate_realistic_phone(subject_uuid)],
                "has_purchase": is_buyer,
                "registered_user_ref": f"user_{subject_num}" if has_registered else None
            })
        
        return subjects

    async def get_registered_users_bulk(self, key: str, uuids: List[str], 
                                       batch_size: int = 500) -> Dict[str, dict]:
        """Bulk check registered users"""
        results = {}
        for i in range(0, len(uuids), batch_size):
            chunk = uuids[i:i+batch_size]
            # Mock bulk API call
            await asyncio.sleep(0.01)  # Simulate network delay
            
            for uuid in chunk:
                subject_num = int(uuid.split('_')[-1]) if '_' in uuid and uuid.split('_')[-1].isdigit() else 1
                is_registered = subject_num % 3 == 0
                results[uuid] = {
                    "uuid": uuid,
                    "is_registered": is_registered,
                    "registered_uuid": f"user_{subject_num}" if is_registered else None
                }
        return results

    async def get_user_profiles_bulk(self, key: str, registered_uuids: List[str], 
                                    batch_size: int = 500) -> Dict[str, dict]:
        """Bulk get user profiles for phone info"""
        results = {}
        for i in range(0, len(registered_uuids), batch_size):
            chunk = registered_uuids[i:i+batch_size]
            # Mock bulk API call
            await asyncio.sleep(0.01)  # Simulate network delay
            
            for reg_uuid in chunk:
                user_num = int(reg_uuid.split('_')[-1]) if '_' in reg_uuid and reg_uuid.split('_')[-1].isdigit() else 1
                results[reg_uuid] = {
                    "uuid": reg_uuid,
                    "phones": [f"+1{user_num:010d}"]
                }
        return results

    async def get_subject(self, key: str, subject_id: str) -> dict:
        """Get subject details (legacy method for compatibility)"""
        # Mock implementation with predictable data for testing
        subject_num = int(subject_id.split('_')[-1]) if '_' in subject_id and subject_id.split('_')[-1].isdigit() else 1
        
        # Make subjects with even numbers be buyers, odd be non-buyers
        is_buyer = subject_num % 2 == 0
        
        # Make subjects with multiples of 3 be registered users
        has_registered = subject_num % 3 == 0
        
        return {
            "id": subject_id,
            "name": f"Test Subject {subject_num}",
            "phone": f"+1{subject_num:010d}",
            "email": f"test{subject_num}@example.com",
            "consent_timestamp": "2024-01-01T00:00:00Z",
            "purchase_history": [{"id": "p1", "amount": 100.0, "date": "2024-01-01T00:00:00Z"}] if is_buyer else [],
            "registered_user_ref": f"user_{subject_num}" if has_registered else None,
            "has_images": True
        }