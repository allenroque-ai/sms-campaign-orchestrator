output "build_project_name" {
  value = aws_codebuild_project.build.name
}

output "integration_test_project_name" {
  value = aws_codebuild_project.integration_test.name
}