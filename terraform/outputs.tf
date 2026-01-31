output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images"
  value       = aws_ecr_repository.agent.repository_url
}

output "execution_role_arn" {
  description = "IAM role ARN for Bedrock agent"
  value       = aws_iam_role.bedrock_agent_execution.arn
}

output "aws_account_id" {
  description = "Your AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}
