import os, re, json, boto3, botocore

SSM_PARAM = os.getenv("PARAM_NAME", "/sms-campaign/task-def-arn")
ECS_CLUSTER = os.getenv("ECS_CLUSTER")         # e.g., "sms-campaign-prod"
ECS_SERVICE = os.getenv("ECS_SERVICE")         # e.g., "sms-campaign-prod"

ssm = boto3.client("ssm")
ecs = boto3.client("ecs")
codepipeline = boto3.client("codepipeline")

ARN_RE = re.compile(r"^arn:aws:ecs:[a-z0-9-]+:\d{12}:task-definition/.+:\d+$")

def _discover_taskdef_arn() -> str:
    if not (ECS_CLUSTER and ECS_SERVICE):
        raise ValueError("ECS_CLUSTER and ECS_SERVICE env vars are required for discovery fallback")
    resp = ecs.describe_services(cluster=ECS_CLUSTER, services=[ECS_SERVICE])
    svcs = resp.get("services", [])
    if not svcs:
        raise RuntimeError(f"ECS service not found: {ECS_SERVICE}")
    arn = svcs[0]["taskDefinition"]
    return arn

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

def lambda_handler(event, _context):
    # Support direct invoke with {"task_def_arn": "..."} OR CodePipeline job events.
    job_id = None
    if _is_cp_event(event):
        job_id = event["CodePipeline.job"]["id"]

    try:
        task_def_arn = None
        if isinstance(event, dict):
            task_def_arn = event.get("task_def_arn")

        if not task_def_arn:
            # Fallback: discover from ECS service (post-DeployProd)
            task_def_arn = _discover_taskdef_arn()

        if not ARN_RE.match(task_def_arn or ""):
            raise ValueError(f"Invalid task_def_arn: {task_def_arn}")

        ssm.put_parameter(
            Name=SSM_PARAM,
            Value=task_def_arn,
            Type="String",
            Overwrite=True,
        )

        result = {"ok": True, "param": SSM_PARAM, "task_def_arn": task_def_arn}
        if job_id:
            _put_cp_result(job_id, True, "Updated SSM successfully")
        return result

    except Exception as e:
        if job_id:
            _put_cp_result(job_id, False, str(e))
        raise