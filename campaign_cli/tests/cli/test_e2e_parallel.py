# campaign-cli/tests/cli/test_e2e_parallel.py
import subprocess, json

# def test_cli_json_parallel(tmp_path, jobs_json_path):
#     cp = subprocess.run([
#         "campaign-cli","build","--both","--json","--concurrency","12","--retries","3"
#     ], input=json.dumps(jobs_json_path.read_bytes()), capture_output=True, check=True)
#     payload = json.loads(cp.stdout)
#     assert isinstance(payload, list) and len(payload) >= 0