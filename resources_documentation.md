# AWS Resources Created for SMS Campaign Orchestrator - Staging Environment

## ECS Resources
----------------------------------------------------------------------------------------------------------
|                                            DescribeClusters                                            |
+------------------------------------+-------------------------------------------------------------------+
|  clusterArn                        |  arn:aws:ecs:us-east-1:754102187132:cluster/sms-campaign-staging  |
|  clusterName                       |  sms-campaign-staging                                             |
|  pendingTasksCount                 |  0                                                                |
|  registeredContainerInstancesCount |  0                                                                |
|  runningTasksCount                 |  1                                                                |
|  status                            |  ACTIVE                                                           |
+------------------------------------+-------------------------------------------------------------------+
------------------------------------------------------------------------------------------------------------
|                                             DescribeServices                                             |
+----------------+-----------------------------------------------------------------------------------------+
|  desiredCount  |  1                                                                                      |
|  runningCount  |  1                                                                                      |
|  serviceArn    |  arn:aws:ecs:us-east-1:754102187132:service/sms-campaign-staging/sms-campaign-staging   |
|  serviceName   |  sms-campaign-staging                                                                   |
|  status        |  ACTIVE                                                                                 |
|  taskDefinition|  arn:aws:ecs:us-east-1:754102187132:task-definition/sms-campaign-staging:1              |
+----------------+-----------------------------------------------------------------------------------------+
----------------------------------------------------------------------------------------------------
|                                      DescribeTaskDefinition                                      |
+-------------------+------------------------------------------------------------------------------+
|  family           |  sms-campaign-staging                                                        |
|  networkMode      |  awsvpc                                                                      |
|  revision         |  1                                                                           |
|  status           |  ACTIVE                                                                      |
|  taskDefinitionArn|  arn:aws:ecs:us-east-1:754102187132:task-definition/sms-campaign-staging:1   |
+-------------------+------------------------------------------------------------------------------+

## Application Load Balancer (ALB) Resources
----------------------------------------------------------------------------------------------------------------------------------------
|                                                         DescribeLoadBalancers                                                        |
+------------------+-------------------------------------------------------------------------------------------------------------------+
|  DNSName         |  internal-sms-campaign-staging-alb-1813858304.us-east-1.elb.amazonaws.com                                         |
|  LoadBalancerArn |  arn:aws:elasticloadbalancing:us-east-1:754102187132:loadbalancer/app/sms-campaign-staging-alb/9d945a58caba1000   |
|  LoadBalancerName|  sms-campaign-staging-alb                                                                                         |
|  Scheme          |  internal                                                                                                         |
|  Type            |  application                                                                                                      |
+------------------+-------------------------------------------------------------------------------------------------------------------+
||                                                                State                                                               ||
|+----------------------------------------------------------+-------------------------------------------------------------------------+|
||  Code                                                    |  active                                                                 ||
|+----------------------------------------------------------+-------------------------------------------------------------------------+|
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                                        DescribeTargetGroups                                                                                         |
+------+-----------+------------------------------------------------------------------------------------------------------------------+--------------------------------+-------------+----------------+
| Port | Protocol  |                                                 TargetGroupArn                                                   |        TargetGroupName         | TargetType  |     VpcId      |
+------+-----------+------------------------------------------------------------------------------------------------------------------+--------------------------------+-------------+----------------+
|  8080|  HTTP     |  arn:aws:elasticloadbalancing:us-east-1:754102187132:targetgroup/sms-campaign-staging-tg-blue/d1853b3aaaa5438d   |  sms-campaign-staging-tg-blue  |  ip         |  vpc-c88adcae  |
|  8080|  HTTP     |  arn:aws:elasticloadbalancing:us-east-1:754102187132:targetgroup/sms-campaign-staging-tg-green/d4ada41662cea69c  |  sms-campaign-staging-tg-green |  ip         |  vpc-c88adcae  |
+------+-----------+------------------------------------------------------------------------------------------------------------------+--------------------------------+-------------+----------------+

## CodeDeploy Resources

### Application
- **Name**: sms-campaign-staging
- **ID**: 004ff692-5ac5-4dfb-9932-75facddb21ec

### Deployment Group
- **Name**: sms-campaign-staging-dg
- **ID**: 49e0e67c-2571-462a-a4e9-ab970c63caca
- **Deployment Config**: CodeDeployDefault.ECSAllAtOnce

## Lambda Resources
-----------------------------------------------------------------------------------------
|                                      GetFunction                                      |
+--------------+------------------------------------------------------------------------+
|  FunctionArn |  arn:aws:lambda:us-east-1:754102187132:function:sms-campaign-promote   |
|  FunctionName|  sms-campaign-promote                                                  |
|  Handler     |  handler.lambda_handler                                                |
|  LastModified|  2025-10-31T13:04:17.731+0000                                          |
|  MemorySize  |  128                                                                   |
|  Runtime     |  python3.12                                                            |
|  Timeout     |  60                                                                    |
+--------------+------------------------------------------------------------------------+

## Systems Manager (SSM) Resources

### Parameter
- **Name**: /sms-campaign/task-def-arn
- **Type**: String
- **Value**: arn:aws:ecs:us-east-1:754102187132:task-definition/sms-campaign-staging:1
- **ARN**: arn:aws:ssm:us-east-1:754102187132:parameter/sms-campaign/task-def-arn

## Elastic Container Registry (ECR) Resources
----------------------------------------------------------------------------------
|                              DescribeRepositories                              |
+----------------+---------------------------------------------------------------+
|  createdAt     |  2025-10-31T08:35:26.434000-05:00                             |
|  repositoryArn |  arn:aws:ecr:us-east-1:754102187132:repository/sms-campaign   |
|  repositoryName|  sms-campaign                                                 |
|  repositoryUri |  754102187132.dkr.ecr.us-east-1.amazonaws.com/sms-campaign    |
+----------------+---------------------------------------------------------------+

## VPC Endpoint Resources
---------------------------------------------------------------------------------------------------------------
|                                            DescribeVpcEndpoints                                             |
+----------------------------------+------------+-------------------------+------------------+----------------+
|            ServiceName           |   State    |      VpcEndpointId      | VpcEndpointType  |     VpcId      |
+----------------------------------+------------+-------------------------+------------------+----------------+
|  com.amazonaws.us-east-1.s3      |  available |  vpce-ac8b31c5          |  Gateway         |  vpc-90b6e0f6  |
|  com.amazonaws.us-east-1.ecr.dkr |  available |  vpce-012a9161e13deb8cf |  Interface       |  vpc-c88adcae  |
|  com.amazonaws.us-east-1.ecr.api |  available |  vpce-06fdf0b7605c0d0f8 |  Interface       |  vpc-c88adcae  |
|  com.amazonaws.us-east-1.s3      |  available |  vpce-01faaa7094eb4affa |  Gateway         |  vpc-c88adcae  |
+----------------------------------+------------+-------------------------+------------------+----------------+

## Identity and Access Management (IAM) Resources
-------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                         ListRoles                                                                         |
+-----------------------------------------------------------------+----------------------------+------------------------+-----------------------------------+
|                               Arn                               |        CreateDate          |        RoleId          |             RoleName              |
+-----------------------------------------------------------------+----------------------------+------------------------+-----------------------------------+
|  arn:aws:iam::754102187132:role/sms-campaign-staging-codedeploy |  2025-10-31T13:04:08+00:00 |  AROA27E76GR6PEZWHBATQ |  sms-campaign-staging-codedeploy  |
|  arn:aws:iam::754102187132:role/sms-campaign-staging-task       |  2025-10-31T13:04:08+00:00 |  AROA27E76GR6JPBDLXM6C |  sms-campaign-staging-task        |
|  arn:aws:iam::754102187132:role/sms-campaign-staging-task-exec  |  2025-10-31T13:04:08+00:00 |  AROA27E76GR6ED2JY67F5 |  sms-campaign-staging-task-exec   |
+-----------------------------------------------------------------+----------------------------+------------------------+-----------------------------------+
-----------------------------------------------------------------------------------------------------------------------------------------------------------------
|                                                                         ListPolicies                                                                          |
+--------------------------------------------------------------------+----------------------------+------------------------+------------------------------------+
|                                 Arn                                |        CreateDate          |       PolicyId         |            PolicyName              |
+--------------------------------------------------------------------+----------------------------+------------------------+------------------------------------+
|  arn:aws:iam::754102187132:policy/sms-campaign-secrets-access      |  2025-10-30T17:22:41+00:00 |  ANPA27E76GR6EFO2QTRUS |  sms-campaign-secrets-access       |
|  arn:aws:iam::754102187132:policy/sms-campaign-staging-task-inline |  2025-10-31T13:04:08+00:00 |  ANPA27E76GR6EH46TUYN6 |  sms-campaign-staging-task-inline  |
|  arn:aws:iam::754102187132:policy/sms-campaign-promote-inline      |  2025-10-31T13:04:08+00:00 |  ANPA27E76GR6NL3B537S7 |  sms-campaign-promote-inline       |
|  arn:aws:iam::754102187132:policy/sms-campaign-ssm-access          |  2025-10-30T13:27:42+00:00 |  ANPA27E76GR6PTMTNS77B |  sms-campaign-ssm-access           |
+--------------------------------------------------------------------+----------------------------+------------------------+------------------------------------+

## CloudWatch Resources
--------------------------------------------------
|                DescribeLogGroups               |
+------------------+-----------------------------+
|  creationTime    |  1761915848607              |
|  logGroupName    |  /ecs/sms-campaign-staging  |
|  retentionInDays |  14                         |
|  storedBytes     |  0                          |
+------------------+-----------------------------+

## Summary

### Resource Count by Service:
- **ECS**: 3 resources (Cluster, Service, Task Definition)
- **ALB**: 3 resources (Load Balancer, 2 Target Groups)
- **CodeDeploy**: 2 resources (Application, Deployment Group)
- **Lambda**: 1 resource (Function)
- **SSM**: 1 resource (Parameter)
- **ECR**: 1 resource (Repository)
- **VPC Endpoints**: 3 resources (ECR API, ECR DKR, S3 Gateway)
- **IAM**: 6 resources (3 Roles, 3 Policies)
- **CloudWatch**: 1 resource (Log Group)

**Total AWS Resources Created: 21**

### Deployment Details
- Environment: Staging
- Region: us-east-1
- Terraform Version: Applied successfully
- Docker Image: Built and pushed to ECR
- Health Checks: Configured on '/' path
- Blue/Green Deployments: Enabled via CodeDeploy
- Monitoring: CloudWatch logs configured
- Network: Public IP assignment enabled for ECS tasks


### Docker Resources
- **Image**: 754102187132.dkr.ecr.us-east-1.amazonaws.com/sms-campaign:latest
- **Tag**: latest
- **Digest**: sha256:b5504d4f7a2551598affb2f5f0ac3ddb5efbb7d1ac11cc568fbfff54d3c7bdee
- **Build Date**: 2025-10-31
- **Base Image**: python:3.12-slim
- **Application**: HTTP server on port 8080
