# Get current AWS account ID
data "aws_caller_identity" "current" {}

# ECR Repository for Docker images
resource "aws_ecr_repository" "agent" {
  name                 = var.agent_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = {
    Name      = var.agent_name
    ManagedBy = "Terraform"
  }
}

# IAM Role for Bedrock Agent
resource "aws_iam_role" "bedrock_agent_execution" {
  name = "${var.agent_name}-execution-role"

  assume_role_policy = jsonencode({
  Version = "2012-10-17"
  Statement = [
    {
      Effect = "Allow"
      Principal = {
        Service = [
          "bedrock.amazonaws.com",
          "bedrock-agentcore.amazonaws.com"
        ]
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }
  ]
})

  tags = {
    Name      = "${var.agent_name}-execution-role"
    ManagedBy = "Terraform"
  }
}

# IAM Policy: Bedrock Model Access (Claude)
resource "aws_iam_role_policy" "bedrock_model_access" {
  name = "bedrock-model-access"
  role = aws_iam_role.bedrock_agent_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
        ]
      }
    ]
  })
}

# IAM Policy: CloudWatch Logs
resource "aws_iam_role_policy" "cloudwatch_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.bedrock_agent_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/*"
      }
    ]
  })
}

# IAM Policy: ECR Access
resource "aws_iam_role_policy" "ecr_access" {
  name = "ecr-access"
  role = aws_iam_role.bedrock_agent_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.agent.arn
      },
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      }
    ]
  })
}
