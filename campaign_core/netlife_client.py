#!/usr/bin/env python3
"""
Netlife API Client for SMS Campaigns
Enhanced client with buyer vs non-buyer logic and access key management
UPDATED: Added registered user lookup methods for enhanced contact extraction
"""

import requests
import random
import logging
import time
import json
import threading
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth

# Suppress urllib3 SSL warnings (we use verify=False intentionally for internal certs)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from campaign_core.config import (
    PERFORMANCE_CONFIG, API_ENDPOINTS, SMS_DEFAULTS, 
    ACTIVITY_CONFIG, get_timestamp
)

logger = logging.getLogger(__name__)

class NetlifeAPIClient:
    """Enhanced Netlife API client for SMS campaign data processing"""
    
    def __init__(self, portal_name: str, base_url: str, username: str, password: str):
        # Clean up the URL (copied from FMC pattern)
        base_url = base_url.rstrip('/')
        if base_url.endswith('/api/v1'):
            base_url = base_url[:-7]
        
        self.portal_name = portal_name
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # Determine portal brand
        self.portal_brand = self._determine_portal_brand(portal_name)
        
        # Thread-safe statistics (enhanced from FMC)
        self._stats_lock = threading.Lock()
        self.stats = {
            'portal_name': portal_name,
            'portal_brand': self.portal_brand,
            'start_time': datetime.now(),
            'activities_found': 0,
            'jobs_processed': 0,
            'subjects_total': 0,
            'subjects_buyers': 0,
            'subjects_non_buyers': 0,
            'subjects_with_phones': 0,
            'subjects_with_emails': 0,
            'subjects_with_images': 0,
            'registered_users_checked': 0,  # NEW
            'registered_users_found': 0,     # NEW
            'access_keys_existing': 0,
            'access_keys_created': 0,
            'access_keys_failed': 0,
            'api_calls_total': 0,
            'api_calls_failed': 0,
            'errors': []
        }
        
        # Thread-safe caches
        self._cache_lock = threading.Lock()
        self._job_details_cache = {}
        self._buyers_cache = {}
        self._non_buyers_cache = {}
        self._subjects_enriched_cache = {}
        self._user_details_cache = {}  # NEW: Cache for user details
    
    def _determine_portal_brand(self, portal_name: str) -> str:
        """Determine portal brand based on portal name"""
        generations_portals = ['nowandforeverphoto', 'generationsphotos', 'nowandgen']
        legacy_portals = ['legacyseniorphotos', 'legacyphoto', 'legacyphotos', 
                         'westpointportraits', 'midshipmenportraits', 'coastguardportraits']
        
        if portal_name in generations_portals:
            return 'Generations'
        elif portal_name in legacy_portals:
            return 'Legacy'
        else:
            return 'Unknown'
    
    def test_connection(self) -> bool:
        """Test if the portal is accessible with provided credentials"""
        try:
            response = self._make_request('GET', API_ENDPOINTS['activities_search'], 
                                        params={'status_id': ACTIVITY_CONFIG['target_status']})
            logger.info(f"[{self.portal_name}] Connection test successful")
            return True
        except Exception as e:
            logger.warning(f"[{self.portal_name}] Connection test failed: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with retry logic (enhanced from FMC)"""
        # Handle URL construction (copied from FMC pattern)
        if self.base_url.endswith('/api/v1'):
            if endpoint.startswith('/api/v1'):
                endpoint = endpoint[7:]
            url = f"{self.base_url}{endpoint}"
        else:
            if not endpoint.startswith('/api/v1'):
                endpoint = f"/api/v1{endpoint}"
            url = f"{self.base_url}{endpoint}"
        
        max_retries = PERFORMANCE_CONFIG['retry_attempts']
        backoff = PERFORMANCE_CONFIG['retry_backoff']
        timeout = PERFORMANCE_CONFIG['timeout']
        
        with self._stats_lock:
            self.stats['api_calls_total'] += 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs, timeout=timeout, verify=False)
                response.raise_for_status()
                
                if response.content:
                    try:
                        data = response.json()
                        # Handle Netlife API response format
                        if isinstance(data, dict) and 'data' in data:
                            return data['data']
                        return data
                    except json.JSONDecodeError:
                        return response.text
                return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"[{self.portal_name}] Request timeout (attempt {attempt + 1}/{max_retries}) - {endpoint}")
                if attempt == max_retries - 1:
                    with self._stats_lock:
                        self.stats['api_calls_failed'] += 1
                        self.stats['errors'].append(f"Timeout: {endpoint}")
                    raise
                time.sleep(backoff ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"[{self.portal_name}] Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    with self._stats_lock:
                        self.stats['api_calls_failed'] += 1
                        self.stats['errors'].append(f"Request failed: {endpoint} - {str(e)}")
                    raise
                time.sleep(backoff ** attempt)
    

    _lock = threading.Lock()

    @property
    def origin(self) -> str:
        # Always normalize to /api/v1
        return self.base_url.rstrip("/") + "/api/v1"

    def http_get(self, endpoint: str, params: dict | None = None, timeout: int = 30):
        """
        Robust GET with retries/backoff, tolerant JSON parsing, and endpoint trim.
        """
        endpoint = (endpoint or "").strip()  # fix '  /jobs/...'
        url = self.origin + endpoint  # do NOT double-join leading slashes
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        for attempt in range(1, 4):
            try:
                with self._lock:
                    r = self.session.get(url, params=params, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    if ra:
                        time.sleep(min(int(ra), 30))
                    # jittered backoff
                    time.sleep(min(12, 0.75 * (2 ** (attempt - 1))) + random.random() * 0.5)
                    continue
                if r.status_code >= 500 and attempt < 3:
                    time.sleep(min(12, 0.75 * (2 ** (attempt - 1))) + random.random() * 0.5)
                    continue
                r.raise_for_status()
                # tolerant JSON decode
                ct = (r.headers.get("content-type") or "").lower()
                if "json" in ct or r.text.lstrip().startswith(("{", "[")):
                    return r.json()
                return None
            except requests.RequestException:
                if attempt < 3:
                    time.sleep(min(12, 0.75 * (2 ** (attempt - 1))) + random.random() * 0.5)
                    continue
                return None

    def _paginate(self, first_page: dict | list) -> list[dict]:
        """
        Flattens {data:[...], meta.next:?} / {results:[...]} / raw list pages into a list of rows.
        Follows meta.next (absolute or relative).
        """
        rows: list[dict] = []
        def page_rows(p):
            if isinstance(p, list):
                return p
            if isinstance(p, dict):
                if isinstance(p.get("data"), list):
                    return p["data"]
                if isinstance(p.get("results"), list):
                    return p["results"]
            return []
        def next_url(p):
            if not isinstance(p, dict):
                return None
            nxt = p.get("meta", {}).get("next") or p.get("next")
            if not nxt:
                return None
            # support absolute or relative
            return nxt.strip()

        cur = first_page
        rows.extend(page_rows(cur))
        nxt = next_url(cur)
        while nxt:
            # keep same origin if relative
            if nxt.startswith("/"):
                url = self.origin + nxt
            elif nxt.startswith("http"):
                url = nxt
            else:
                url = self.origin + nxt if not nxt.startswith("/api") else self.base_url.rstrip("/") + nxt
            with self._lock:
                r = self.session.get(url, headers={"Accept":"application/json"}, timeout=30, verify=False)
            if r.status_code != 200:
                break
            cur = r.json() if r.text.lstrip().startswith(("{","[")) else {}
            rows.extend(page_rows(cur))
            nxt = next_url(cur)
        return rows

    def get_job_registered_users_map(self, job_uuid: str) -> dict[str, dict[str, str]]:
        """
        Bulk registrations: /jobs/{job}/users  → {subjectUuid: {userUuid, email}}
        Handles shape + pagination.
        """
        first = self.http_get(f"/jobs/{job_uuid}/users")
        if first is None:
            return {}
        rows = self._paginate(first)
        out: dict[str, dict[str, str]] = {}
        for row in rows:
            su = str((row.get("subjectUuid") or "")).strip()
            uu = str((row.get("userUuid") or row.get("uuid") or "")).strip()
            em = str((row.get("userUsername") or row.get("email") or "")).strip()
            if su:
                out[su] = {"userUuid": uu, "email": em.lower()}  # normalize email case
        return out
    
    def get_activities_in_webshop(self) -> List[Dict[str, Any]]:
        """Get all activities with status in-webshop"""
        logger.info(f"[{self.portal_name}] Fetching activities with status '{ACTIVITY_CONFIG['target_status']}'...")
        
        try:
            activities = self._make_request('GET', API_ENDPOINTS['activities_search'], 
                                          params={'status_id': ACTIVITY_CONFIG['target_status']})
            
            if not activities:
                logger.info(f"[{self.portal_name}] No activities found")
                return []
            
            if isinstance(activities, dict):
                activities = [activities]
            elif not isinstance(activities, list):
                activities = []
            
            with self._stats_lock:
                self.stats['activities_found'] = len(activities)
            
            logger.info(f"[{self.portal_name}] Found {len(activities)} activities")
            return activities
            
        except Exception as e:
            logger.error(f"[{self.portal_name}] Error fetching activities: {e}")
            return []
    
    def get_job_details(self, job_uuid: str) -> Dict[str, Any]:
        """Get job details with caching and slow-path retry"""
        with self._cache_lock:
            if job_uuid in self._job_details_cache:
                return self._job_details_cache[job_uuid]
        
        endpoint = API_ENDPOINTS['job_details'].format(job_uuid=job_uuid)
        
        try:
            details = self._make_request('GET', endpoint)
        except requests.exceptions.ReadTimeout:
            logger.warning(f"[{self.portal_name}] Slow-path retry for job {job_uuid} with extended timeout")
            # Slow-path retry with extended timeout
            old_timeout = PERFORMANCE_CONFIG['timeout']
            try:
                # Temporarily extend timeout for this request
                self.session.timeout = 120
                details = self._make_request('GET', endpoint)
            finally:
                self.session.timeout = old_timeout
        
        details = details or {}
        
        with self._cache_lock:
            self._job_details_cache[job_uuid] = details
        
        return details
    
    def get_job_subjects(self, job_uuid: str, has_order: Optional[bool] = None,
                        include_images: bool = False, include_favorite: bool = False) -> List[Dict[str, Any]]:
        """Get subjects for a job with buyer filtering"""
        cache_key = f"{job_uuid}_{has_order}_{include_images}_{include_favorite}"
        
        with self._cache_lock:
            if has_order is True and job_uuid in self._buyers_cache:
                return self._buyers_cache[job_uuid]
            elif has_order is False and job_uuid in self._non_buyers_cache:
                return self._non_buyers_cache[job_uuid]
            elif has_order is None and cache_key in self._subjects_enriched_cache:
                return self._subjects_enriched_cache[cache_key]
        
        params = {}
        if has_order is True:
            params['filter_has_order'] = 'true'
        elif has_order is False:
            params['filter_has_order'] = 'false'
        if include_images:
            params['include_images'] = 'true'
        if include_favorite:
            params['include_favorite_image'] = 'true'
        
        try:
            endpoint = API_ENDPOINTS['job_subjects'].format(job_uuid=job_uuid)
            subjects = self._make_request('GET', endpoint, params=params)
            
            if not subjects:
                subjects = []
            elif isinstance(subjects, dict):
                subjects = [subjects]
            
            # Cache the results
            with self._cache_lock:
                if has_order is True:
                    self._buyers_cache[job_uuid] = subjects
                elif has_order is False:
                    self._non_buyers_cache[job_uuid] = subjects
                else:
                    self._subjects_enriched_cache[cache_key] = subjects
            
            return subjects
            
        except Exception as e:
            logger.error(f"[{self.portal_name}] Error fetching subjects for job {job_uuid}: {e}")
            return []
    
    # =============================================================================
    # NEW METHODS: Registered User Lookup
    # =============================================================================
    
    def get_registered_users(self, job_uuid: str, subject_uuid: str) -> List[Dict]:
        """Get registered users for a subject"""
        endpoint = f"/jobs/{job_uuid}/subjects/{subject_uuid}/users"
        
        try:
            users_data = self._make_request('GET', endpoint)
            
            with self._stats_lock:
                self.stats['registered_users_checked'] += 1
            
            if not users_data or not isinstance(users_data, dict):
                return []
            
            if not users_data.get('success', False):
                return []
            
            users = users_data.get('data', [])
            
            if users and isinstance(users, list):
                with self._stats_lock:
                    self.stats['registered_users_found'] += 1
            
            return users if isinstance(users, list) else []
            
        except Exception as e:
            logger.debug(f"[{self.portal_name}] Error fetching registered users for subject {subject_uuid}: {e}")
            return []
    
    def get_user_details(self, user_uuid: str) -> Optional[Dict]:
        """Get detailed user information with caching"""
        # Check cache first
        with self._cache_lock:
            if user_uuid in self._user_details_cache:
                return self._user_details_cache[user_uuid]
        
        endpoint = f"/users/{user_uuid}"
        
        try:
            user_data = self._make_request('GET', endpoint)
            
            if user_data and isinstance(user_data, dict):
                # Cache the result
                with self._cache_lock:
                    self._user_details_cache[user_uuid] = user_data
                return user_data
            
            return None
            
        except Exception as e:
            logger.debug(f"[{self.portal_name}] Error fetching user details for {user_uuid}: {e}")
            return None
    
    # =============================================================================
    # END NEW METHODS
    # =============================================================================
    
    def get_or_create_access_key(self, job_uuid: str, subject_uuid: str, 
                                subject_name: str, has_images: bool) -> Optional[str]:
        """Get existing access key or create one if subject has images (copied from FMC)"""
        try:
            endpoint = API_ENDPOINTS['subject_access_keys'].format(
                job_uuid=job_uuid, subject_uuid=subject_uuid
            )
            
            # Get existing keys
            response = self._make_request('GET', endpoint)
            
            access_keys = []
            if response:
                if isinstance(response, list):
                    access_keys = response
                elif isinstance(response, dict):
                    access_keys = response.get('access_keys', response.get('data', []))
            
            # If no keys and subject has images, create one
            if not access_keys and has_images:
                logger.debug(f"[{self.portal_name}] Creating access key for {subject_name}")
                create_response = self._make_request('POST', endpoint)
                
                with self._stats_lock:
                    self.stats['access_keys_created'] += 1
                
                # Fetch the keys again after creation
                response = self._make_request('GET', endpoint)
                if response:
                    if isinstance(response, list):
                        access_keys = response
                    elif isinstance(response, dict):
                        access_keys = response.get('access_keys', response.get('data', []))
            else:
                if access_keys:
                    with self._stats_lock:
                        self.stats['access_keys_existing'] += 1
            
            # Extract the key value
            if access_keys:
                if isinstance(access_keys, list) and len(access_keys) > 0:
                    first_key = access_keys[0]
                    if isinstance(first_key, dict):
                        return first_key.get('access_key') or first_key.get('key')
                    return str(first_key)
                elif isinstance(access_keys, str):
                    return access_keys
            
            return None
            
        except Exception as e:
            logger.error(f"[{self.portal_name}] Error with access key for {subject_name}: {e}")
            with self._stats_lock:
                self.stats['access_keys_failed'] += 1
            return None
    
    def get_buyers_and_non_buyers(self, job_uuid: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get both buyers and non-buyers for a job efficiently"""
        buyers = self.get_job_subjects(job_uuid, has_order=True)
        non_buyers = self.get_job_subjects(job_uuid, has_order=False)
        
        with self._stats_lock:
            self.stats['subjects_buyers'] += len(buyers)
            self.stats['subjects_non_buyers'] += len(non_buyers)
            self.stats['subjects_total'] += len(buyers) + len(non_buyers)
        
        return buyers, non_buyers
    
    def build_subject_activity_mapping(self, details_data: Dict[str, Any], 
                                     subjects_enriched: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Set[str]]:
        """Build mapping of subjects to activities from job details"""
        # Helper functions for data processing
        def _safe_str(v) -> str:
            return "" if v is None else str(v).strip()
        
        def coerce_subjects_dict(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
            subs = data.get("subjects")
            if subs is None and isinstance(data.get("job"), dict):
                subs = data["job"].get("subjects")
            if isinstance(subs, dict):
                return subs
            if isinstance(subs, list):
                out = {}
                for s in subs:
                    su = _safe_str(s.get("uuid"))
                    if su:
                        out[su] = s
                return out
            return {}
        
        def coerce_images_dict(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
            imgs = data.get("images")
            if isinstance(imgs, dict):
                return imgs
            if isinstance(imgs, list):
                out = {}
                for img in imgs:
                    iu = _safe_str(img.get("uuid"))
                    if iu:
                        out[iu] = img
                return out
            return {}
        
        def extract_image_ids_from_subject(subj: Dict[str, Any]) -> List[str]:
            out, seen = [], set()
            
            def add(u):
                u = _safe_str(u)
                if u and u not in seen:
                    seen.add(u)
                    out.append(u)
            
            def scan(v):
                if v is None:
                    return
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            add(item)
                        elif isinstance(item, dict):
                            add(item.get("uuid"))
                elif isinstance(v, dict):
                    keys = list(v.keys())
                    if keys and all(len(str(k)) >= 20 for k in keys):
                        for k in keys:
                            add(k)
                    else:
                        add(v.get("uuid"))
                elif isinstance(v, str):
                    add(v)
            
            scan(subj.get("images"))
            scan(subj.get("group_images"))
            scan(subj.get("image"))
            for fav_key in ("favorite_image_uuid", "favoriteImageUuid", "favorite_image"):
                fav = subj.get(fav_key)
                if isinstance(fav, dict):
                    add(fav.get("uuid"))
                elif fav:
                    add(fav)
            return out
        
        def image_activity_uuid(img: Dict[str, Any]) -> str:
            if not isinstance(img, dict):
                return ""
            act = img.get("activity") or {}
            au = _safe_str(act.get("uuid")) if isinstance(act, dict) else ""
            if not au:
                au = _safe_str(img.get("activity_uuid") or img.get("activityUuid"))
            return au
        
        # Build the mapping
        subs_by_uuid = coerce_subjects_dict(details_data)
        imgs_by_uuid = coerce_images_dict(details_data)
        
        # Enrich with subjects data if provided
        if subjects_enriched:
            for s in subjects_enriched:
                su = _safe_str(s.get("uuid"))
                if not su:
                    continue
                tgt = subs_by_uuid.setdefault(su, {})
                for k in ("images", "group_images", "image", "favorite_image_uuid", "favoriteImageUuid", "favorite_image"):
                    if k in s and s[k]:
                        tgt[k] = s[k]
        
        mapping: Dict[str, Set[str]] = {}
        for suuid, subj in subs_by_uuid.items():
            acts = set()
            direct = _safe_str(subj.get("activity_uuid") or subj.get("activity") or "")
            if direct:
                acts.add(direct)
            for img_id in extract_image_ids_from_subject(subj):
                img = imgs_by_uuid.get(img_id)
                if img:
                    au = image_activity_uuid(img)
                    if au:
                        acts.add(au)
            if acts:
                mapping[suuid] = acts
        
        return mapping
    
    def increment_job_processed(self):
        """Thread-safe increment of jobs processed counter"""
        with self._stats_lock:
            self.stats['jobs_processed'] += 1
    
    def add_subject_stats(self, has_phone: bool = False, has_email: bool = False, has_images: bool = False):
        """Thread-safe increment of subject statistics"""
        with self._stats_lock:
            if has_phone:
                self.stats['subjects_with_phones'] += 1
            if has_email:
                self.stats['subjects_with_emails'] += 1
            if has_images:
                self.stats['subjects_with_images'] += 1
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get thread-safe copy of current statistics"""
        with self._stats_lock:
            stats_copy = self.stats.copy()
            if 'start_time' in stats_copy:
                duration = datetime.now() - stats_copy['start_time']
                stats_copy['duration_seconds'] = duration.total_seconds()
                stats_copy['duration_formatted'] = str(duration).split('.')[0]  # Remove microseconds
            return stats_copy
    
    def log_final_stats(self):
        """Log final statistics for this portal"""
        stats = self.get_stats_summary()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"FINAL STATS - {self.portal_name} ({self.portal_brand})")
        logger.info(f"{'='*60}")
        logger.info(f"Duration: {stats.get('duration_formatted', 'Unknown')}")
        logger.info(f"Activities Found: {stats['activities_found']}")
        logger.info(f"Jobs Processed: {stats['jobs_processed']}")
        logger.info(f"Subjects Total: {stats['subjects_total']}")
        logger.info(f"  - Buyers: {stats['subjects_buyers']}")
        logger.info(f"  - Non-Buyers: {stats['subjects_non_buyers']}")
        logger.info(f"  - With Phones: {stats['subjects_with_phones']}")
        logger.info(f"  - With Emails: {stats['subjects_with_emails']}")
        logger.info(f"  - With Images: {stats['subjects_with_images']}")
        
        # NEW: Log registered user statistics
        if stats['registered_users_checked'] > 0:
            logger.info(f"Registered Users:")
            logger.info(f"  - Checked: {stats['registered_users_checked']}")
            logger.info(f"  - Found: {stats['registered_users_found']}")
            percentage = (stats['registered_users_found'] / stats['registered_users_checked'] * 100) if stats['registered_users_checked'] > 0 else 0
            logger.info(f"  - Rate: {percentage:.1f}%")
        
        logger.info(f"Access Keys:")
        logger.info(f"  - Existing: {stats['access_keys_existing']}")
        logger.info(f"  - Created: {stats['access_keys_created']}")
        logger.info(f"  - Failed: {stats['access_keys_failed']}")
        logger.info(f"API Calls:")
        logger.info(f"  - Total: {stats['api_calls_total']}")
        logger.info(f"  - Failed: {stats['api_calls_failed']}")
        
        if stats['errors']:
            logger.warning(f"Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
        
        logger.info(f"{'='*60}")
