# IPL-Kiro Deployment Guide

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS SAM CLI** installed
3. **AWS CLI** configured with credentials
4. **Node.js 20+** and **Python 3.11+**

## Step 1: Install AWS SAM CLI

```bash
# macOS
brew tap aws/tap
brew install aws-sam-cli

# Verify installation
sam --version
```

## Step 2: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json)
```

## Step 3: Pre-Deployment Checklist

### 3.1 Verify All Tests Pass
```bash
# Backend tests
cd /Users/performek5/Desktop/Code/IPL-kiro/kiro-packet
pytest api/tests/ -v

# Frontend tests
npm test -- --run

# Type check
npm run type-check
```

### 3.2 Build Frontend Assets
```bash
# Install dependencies
npm ci

# Build for production
npm run build
```

## Step 4: SAM Build and Validate

```bash
# Navigate to project root
cd /Users/performek5/Desktop/Code/IPL-kiro/kiro-packet

# Validate SAM template
sam validate

# Build SAM application
sam build --use-container
```

## Step 5: Deploy to Staging

### Option A: Using SAM CLI
```bash
# Deploy to staging
sam deploy --stack-name ipl-kiro-staging \
  --parameter-overrides Environment=staging \
  --s3-bucket ipl-kiro-deployments \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --guided
```

### Option B: Using SAM Config
```bash
# Deploy using samconfig.toml
sam deploy --config-env staging
```

## Step 6: Deploy Frontend to S3

After SAM deploy completes, upload frontend build:

```bash
# Get the frontend bucket name from stack outputs
aws cloudformation describe-stacks \
  --stack-name ipl-kiro-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucket`].OutputValue' \
  --output text

# Upload frontend assets
aws s3 sync dist/ s3://<FRONTEND_BUCKET_NAME>/ --delete
```

## Step 7: Verify Deployment

### Check Stack Status
```bash
aws cloudformation describe-stacks \
  --stack-name ipl-kiro-staging \
  --query 'Stacks[0].StackStatus'
```

### Get API Endpoint
```bash
aws cloudformation describe-stacks \
  --stack-name ipl-kiro-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

### Get CloudFront URL
```bash
aws cloudformation describe-stacks \
  --stack-name ipl-kiro-staging \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
  --output text
```

### Test API
```bash
# Test health endpoint
curl https://<API_URL>/health

# Test ILP endpoint
curl -X POST https://<API_URL>/api/optimize \
  -H "Content-Type: application/json" \
  -d '{"squad_id": "csk", "opponent_id": "mi", "venue": "Chennai"}'
```

## Step 8: Deploy to Production

Once staging is verified:

```bash
# Deploy to production
sam deploy --stack-name ipl-kiro-production \
  --parameter-overrides Environment=production \
  --s3-bucket ipl-kiro-deployments \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --guided
```

## Required AWS Resources

The SAM template creates:
- Lambda function (FastAPI backend)
- API Gateway (REST API)
- DynamoDB table (sessions with TTL)
- S3 bucket (data storage)
- S3 bucket (frontend hosting)
- CloudFront distribution (CDN)
- IAM roles and policies

## Environment Variables

Set these in GitHub Secrets for CI/CD:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `POSTHOG_KEY` (optional)

## Troubleshooting

### SAM Build Fails
```bash
# Try without container
sam build

# Or use specific runtime
sam build --use-container --build-image amazon/aws-sam-cli-build-image-python3.11
```

### Stack Creation Fails
```bash
# Check stack events
aws cloudformation describe-stack-events \
  --stack-name ipl-kiro-staging \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

### Lambda Function Error
```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/ipl-kiro-staging --follow
```

## Cost Estimates (Monthly)

- Lambda: ~$5-10 (1M requests)
- API Gateway: ~$3-5
- DynamoDB: ~$5 (on-demand)
- S3: ~$1-2
- CloudFront: ~$5-10
- **Total: ~$20-30/month**

## Next Steps

1. Set up custom domain with Route53
2. Configure SSL certificate
3. Set up CloudWatch alarms
4. Configure PostHog for production analytics
5. Enable AWS X-Ray for tracing

## Support

For issues:
1. Check CloudWatch logs
2. Review SAM template at `template.yaml`
3. Verify IAM permissions
4. Check API Gateway CloudWatch logs
