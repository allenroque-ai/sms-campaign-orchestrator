# campaign_core/adapters/secrets.py
from __future__ import annotations
import os
import json
import base64
import boto3

def load_basic_auth(secret_arn: str) -> tuple[str, str, int, int]:
    sm = boto3.client("secretsmanager")
    resp = sm.get_secret_value(SecretId=secret_arn)
    s = resp.get("SecretString") or base64.b64decode(resp["SecretBinary"]).decode()
    data = json.loads(s)
    return data["username"], data["password"], int(data.get("timeout_s", 30)), int(data.get("rate_limit_per_sec", 8))