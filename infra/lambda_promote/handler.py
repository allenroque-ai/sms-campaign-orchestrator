import json
import os
import boto3

ssm = boto3.client("ssm")

def lambda_handler(event, context):
    """Update SSM parameter with new task definition ARN after prod deployment approval"""
    task_def_arn = event.get("task_def_arn")
    if not task_def_arn:
        raise ValueError("task_def_arn not provided in event")

    ssm.put_parameter(
        Name="/sms-campaign/task-def-arn",
        Value=task_def_arn,
        Type="String",
        Overwrite=True
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Task definition ARN updated",
            "task_def_arn": task_def_arn
        })
    }