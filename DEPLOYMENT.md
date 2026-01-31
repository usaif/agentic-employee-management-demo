# Deployment Guide: Employee Data Agent to AWS Bedrock AgentCore

## Prerequisites

- Docker installed
- AWS CLI configured (`aws configure`)
- Terraform installed
- AgentCore CLI installed (`pip install bedrock-agentcore-starter-toolkit`)


## Deployment Steps

### Step 1: Build Docker Image Locally

```bash
# Build ARM64 image (required by Bedrock AgentCore)
docker buildx build --platform linux/arm64 -t employee-agent:latest .

# Test locally (optional)
docker run -p 8080:8080 employee-agent:latest

curl http://localhost:8080/ping  # Should return {"status":"healthy"}

```

### Step 2: Create AWS Infrastructure with Terraform

```bash
cd terraform/

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Create resources (ECR + IAM roles)
terraform apply
# Type 'yes' when prompted

# Save the outputs
terraform output ecr_repository_url  # Save this
terraform output execution_role_arn  # Save this

cd ..
```

Resources created:
* ECR repository with KMS encryption
* IAM execution role for AgentCore
* IAM policies (Bedrock Claude access, CloudWatch logs, ECR pull)

<br/>

### Step 3: Enable Claude Model Access (One-Time)

```bash

# Check if Claude is enabled
aws bedrock list-foundation-models \
  --by-provider anthropic \
  --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-5-sonnet`)].modelId'

# If empty, enable via AWS Console:
# https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
# 1. Click "Manage model access"
# 2. Check "Claude 3.5 Sonnet"
# 3. Click "Request model access" (instant approval)
```

<br/>

### Step 4: Configure AgentCore (First Time Only)

```bash
# Run interactive configuration
agentcore configure

# Answer the prompts:
# - Entrypoint: app/agent_entrypoint.py
# - Deployment type: 2 (Container)
# - Execution role ARN: <paste from terraform output>
# - ECR Repository URI: <paste from terraform output> (WITHOUT :v1 tag)
# - OAuth: no
# - Request headers: no
# - Memory: s (skip)

# This creates .bedrock_agentcore.yaml
```

**Manual config alternative:** If interactive mode fails, edit  `.bedrock_agentcore.yaml` :

```
agent_name: employee_data_mgmt_agent
region: us-east-1
deployment_type: container
execution_role_arn: arn:aws:iam::ACCOUNT_ID:role/employee-data-mgmt-agent-execution-role
ecr_repository_uri: ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/employee-data-mgmt-agent
```

<br/>

### Step 5: Deploy to Bedrock AgentCore

```bash
# Deploy using local Docker image
agentcore deploy --local-build

# Wait 2-3 minutes for deployment
# Success message will show CloudWatch log groups
```

<br/>

### Step 6: Test the Deployment

```bash
# Check agent status
agentcore status

# Create session
agentcore invoke '{"input": {"action": "create_session"}}'

# Save the session_id from response, then test login
agentcore invoke '{"input": {"action": "chat", "session_id": "YOUR_SESSION_ID", "prompt": "Login with email priya.nair@company.com"}}'

# View profile
agentcore invoke '{"input": {"action": "chat", "session_id": "YOUR_SESSION_ID", "prompt": "Show my profile"}}'
```

<br/>

## Update Deployment (Code Changes)

When you update your agent code:

```bash
# 1. Rebuild Docker image
docker buildx build --platform linux/arm64 -t employee-agent:latest .

# 2. Redeploy
agentcore deploy --local-build

# AgentCore will:
# - Push new image to ECR with timestamp tag
# - Update the runtime
# - Zero-downtime deployment
```

<br/>

## Update Infrastructure (IAM/ECR Changes)

When you update Terraform files:

```bash
cd terraform/

# Preview changes
terraform plan

# Apply updates
terraform apply

cd ..
```

<br/>

## Monitoring & Logs

### View Logs

```bash
# Real-time logs
aws logs tail /aws/bedrock-agentcore/runtimes/employee_data_mgmt_agent-XXXXX-DEFAULT \
  --log-stream-name-prefix "2026/01/31/[runtime-logs]" \
  --follow

# Last hour of logs
aws logs tail /aws/bedrock-agentcore/runtimes/employee_data_mgmt_agent-XXXXX-DEFAULT \
  --log-stream-name-prefix "2026/01/31/[runtime-logs]" \
  --since 1h
```

### Check Agent Status

```bash
agentcore status
```

### View Agent Details

```bash
# List all agents
agentcore list

# View configuration
cat .bedrock_agentcore.yaml
```

<br/>

## Cleanup / Destroy

### Destroy AgentCore Agent

```bash
agentcore destroy
```

### Destroy Terraform Resources

```bash
cd terraform/

# Preview what will be deleted
terraform plan -destroy

# Delete all resources
terraform destroy
# Type 'yes' when prompted

cd ..

```



