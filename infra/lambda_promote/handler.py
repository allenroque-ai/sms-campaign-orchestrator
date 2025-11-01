# infra/lambda_promote/handler.py
import os, re, boto3

SSM_PARAM   = os.getenv("PARAM_NAME", "/sms-campaign/task-def-arn")
ECS_CLUSTER = os.getenv("ECS_CLUSTER")          # e.g., sms-campaign-prod
ECS_SERVICE = os.getenv("ECS_SERVICE")          # e.g., sms-campaign-prod

ssm          = boto3.client("ssm")
ecs          = boto3.client("ecs")
codepipeline = boto3.client("codepipeline")

ARN_RE = re.compile(r"^arn:aws:ecs:[a-z0-9-]+:\d{12}:task-definition/.+:\d+$")

def _is_cp_event(event) -> bool:
    return isinstance(event, dict) and "CodePipeline.job" in event

def _put_cp_result(job_id: str, ok: bool, msg: str):
    if ok:
        codepipeline.put_job_success_result(jobId=job_id)
    else:
        codepipeline.put_job_failure_result(
            jobId=job_id,
            failureDetails={"type": "JobFailed", "message": msg[:500]}
        )

def _discover_taskdef_arn() -> str:
    if not (ECS_CLUSTER and ECS_SERVICE):
        raise ValueError("ECS_CLUSTER and ECS_SERVICE env vars are required")
    resp = ecs.describe_services(cluster=ECS_CLUSTER, services=[ECS_SERVICE])
    svcs = resp.get("services", [])
    if not svcs:
        raise RuntimeError(f"ECS service not found: {ECS_SERVICE}")
    return svcs[0]["taskDefinition"]

def lambda_handler(event, _ctx):
    print(f"Received event: {event}")  # Debug logging
    job_id = event.get("CodePipeline.job", {}).get("id") if _is_cp_event(event) else None
    print(f"Job ID: {job_id}")  # Debug logging
    try:
        # Prefer explicit event.task_def_arn; otherwise discover from ECS service
        task_def_arn = None
        if isinstance(event, dict):
            task_def_arn = event.get("task_def_arn") or event.get("TaskDefinitionArn")
        if not task_def_arn:
            task_def_arn = _discover_taskdef_arn()

        if not ARN_RE.match(task_def_arn or ""):
            raise ValueError(f"Invalid task_def_arn: {task_def_arn}")

        ssm.put_parameter(Name=SSM_PARAM, Value=task_def_arn, Type="String", Overwrite=True)

        result = {"ok": True, "param": SSM_PARAM, "task_def_arn": task_def_arn}
        if job_id: _put_cp_result(job_id, True, "SSM updated")
        return result
    except Exception as e:
        if job_id: _put_cp_result(job_id, False, str(e))
        raise