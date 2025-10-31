# campaign-core/tests/integration/test_portal_s3.py
import os, subprocess, json, uuid, boto3
import pytest

pytestmark = pytest.mark.skip(reason="Integration test requires real AWS credentials")

def test_real_portal_to_s3(tmp_path):
    bucket = os.environ["ARTIFACT_BUCKET"]
    key = f"it/{uuid.uuid4()}.csv"
    jobs = {"jobs": [{"job_id": "J1", "activities": ["A1"], "portal": "legacyphoto"}]}  # minimal
    cp = subprocess.run([
        "campaign-cli","build","--both","--out",f"s3://{bucket}/{key}","--concurrency","8","--retries","3"
    ], input=json.dumps(jobs).encode(), capture_output=True, check=True)
    boto3.client("s3").head_object(Bucket=bucket, Key=key)