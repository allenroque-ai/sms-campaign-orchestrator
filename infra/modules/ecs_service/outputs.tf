output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.this.arn
}

output "task_def_arn" {
  description = "ECS task definition ARN"
  value       = aws_ecs_task_definition.this.arn
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.this.arn
}

output "alb_listener_arn" {
  description = "ALB listener ARN"
  value       = aws_lb_listener.http.arn
}

output "target_group_arn" {
  description = "Target group ARN (blue)"
  value       = aws_lb_target_group.blue.arn
}

output "target_group_blue_name" {
  description = "Target group blue name"
  value       = aws_lb_target_group.blue.name
}

output "target_group_green_name" {
  description = "Target group green name"
  value       = aws_lb_target_group.green.name
}