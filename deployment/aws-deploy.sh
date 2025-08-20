#!/bin/bash

# AWS Cloud Deployment Script for Native IQ
set -e

ENVIRONMENT=${1:-staging}
AWS_REGION=${2:-us-east-1}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  AWS Deployment - $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check AWS CLI and credentials
check_aws_setup() {
    echo "🔍 Checking AWS setup..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        echo "Install: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        echo "Run: aws configure"
        exit 1
    fi
    
    print_success "AWS CLI configured"
}

# Create ECR repository
create_ecr_repo() {
    echo "📦 Setting up ECR repository..."
    
    REPO_NAME="native-iq"
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION &> /dev/null; then
        print_success "ECR repository exists: $REPO_NAME"
    else
        aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION
        print_success "Created ECR repository: $REPO_NAME"
    fi
    
    # Get repository URI
    REPO_URI=$(aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION --query 'repositories[0].repositoryUri' --output text)
    echo "Repository URI: $REPO_URI"
}

# Build and push Docker image
build_and_push() {
    echo "🔨 Building and pushing Docker image..."
    
    # Get ECR login token
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REPO_URI
    
    # Build image
    docker build -t native-iq -f Dockerfile ..
    
    # Tag for ECR
    IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    docker tag native-iq:latest $REPO_URI:$IMAGE_TAG
    docker tag native-iq:latest $REPO_URI:latest
    
    # Push to ECR
    docker push $REPO_URI:$IMAGE_TAG
    docker push $REPO_URI:latest
    
    print_success "Image pushed: $REPO_URI:$IMAGE_TAG"
    echo "IMAGE_URI=$REPO_URI:$IMAGE_TAG" > ../deployment.env
}

# Create ECS cluster and service
deploy_ecs() {
    print_header "ECS Deployment"
    
    CLUSTER_NAME="native-iq-$ENVIRONMENT"
    SERVICE_NAME="native-iq-service"
    TASK_FAMILY="native-iq-task"
    
    # Create cluster
    if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION &> /dev/null; then
        print_success "ECS cluster exists: $CLUSTER_NAME"
    else
        aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION
        print_success "Created ECS cluster: $CLUSTER_NAME"
    fi
    
    # Create task definition
    cat > task-definition.json << EOF
{
    "family": "$TASK_FAMILY",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "native-iq",
            "image": "$REPO_URI:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "ENVIRONMENT", "value": "$ENVIRONMENT"},
                {"name": "AWS_REGION", "value": "$AWS_REGION"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/native-iq",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]
}
EOF
    
    # Register task definition
    aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION
    
    print_success "Task definition registered"
    
    # Create or update service
    if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION &> /dev/null; then
        aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --task-definition $TASK_FAMILY --region $AWS_REGION
        print_success "Service updated"
    else
        # Note: This requires VPC and security group setup
        print_warning "Service creation requires VPC configuration"
        echo "Create service manually in AWS Console or use CloudFormation"
    fi
    
    rm task-definition.json
}

# Setup Application Load Balancer
setup_alb() {
    print_header "Load Balancer Setup"
    
    print_warning "ALB setup requires:"
    echo "1. VPC with public subnets"
    echo "2. Security groups"
    echo "3. Target groups"
    echo "4. SSL certificate (ACM)"
    echo ""
    echo "Use AWS Console or CloudFormation for complete setup"
}

# Setup Route 53 DNS
setup_dns() {
    print_header "DNS Configuration"
    
    DOMAIN_NAME="nativeiq.tech"
    API_SUBDOMAIN="api"
    
    if [ "$ENVIRONMENT" = "staging" ]; then
        API_SUBDOMAIN="staging-api"
    fi
    
    echo "Configure Route 53 DNS:"
    echo "1. Create hosted zone for $DOMAIN_NAME"
    echo "2. Create A record: $API_SUBDOMAIN.$DOMAIN_NAME → ALB"
    echo "3. Create SSL certificate in ACM"
    echo "4. Associate certificate with ALB"
}

# Main deployment function
deploy_to_aws() {
    print_header "AWS Cloud Deployment - $ENVIRONMENT"
    
    check_aws_setup
    create_ecr_repo
    build_and_push
    deploy_ecs
    setup_alb
    setup_dns
    
    print_success "AWS deployment initiated!"
    echo ""
    echo "Next steps:"
    echo "1. Configure VPC and security groups"
    echo "2. Set up Application Load Balancer"
    echo "3. Configure Route 53 DNS"
    echo "4. Set up ElastiCache Redis cluster"
    echo "5. Configure environment variables in ECS"
}

# Show AWS architecture
show_aws_architecture() {
    print_header "AWS Architecture Overview"
    
    echo "🏗️  Recommended AWS Architecture:"
    echo ""
    echo "┌─────────────────────────────────────────────────┐"
    echo "│                 Route 53 DNS                    │"
    echo "│          api.nativeiq.tech                       │"
    echo "└─────────────────┬───────────────────────────────┘"
    echo "                  │"
    echo "┌─────────────────▼───────────────────────────────┐"
    echo "│          Application Load Balancer              │"
    echo "│              (SSL Termination)                  │"
    echo "└─────────────────┬───────────────────────────────┘"
    echo "                  │"
    echo "┌─────────────────▼───────────────────────────────┐"
    echo "│                ECS Fargate                      │"
    echo "│           (Native IQ Containers)                │"
    echo "└─────────┬───────────────────────┬───────────────┘"
    echo "          │                       │"
    echo "┌─────────▼─────────┐   ┌─────────▼─────────────────┐"
    echo "│   ElastiCache     │   │       DynamoDB            │"
    echo "│     (Redis)       │   │   (Session Storage)       │"
    echo "└───────────────────┘   └───────────────────────────┘"
    echo ""
    echo "🔧 Components:"
    echo "• Route 53: DNS management"
    echo "• ALB: Load balancing + SSL termination"
    echo "• ECS Fargate: Serverless containers"
    echo "• ElastiCache: Redis caching layer"
    echo "• DynamoDB: Persistent session storage"
    echo "• ECR: Container image registry"
    echo "• CloudWatch: Logging and monitoring"
}

# Help function
show_help() {
    echo "Native IQ AWS Cloud Deployment"
    echo ""
    echo "Usage: $0 [ENVIRONMENT] [AWS_REGION] [OPTIONS]"
    echo ""
    echo "Environments:"
    echo "  staging    - Staging environment (default)"
    echo "  production - Production environment"
    echo ""
    echo "Options:"
    echo "  --architecture - Show AWS architecture diagram"
    echo "  --help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 staging us-east-1"
    echo "  $0 production us-west-2"
    echo "  $0 --architecture"
}

# Parse arguments
case "$1" in
    "--help")
        show_help
        exit 0
        ;;
    "--architecture")
        show_aws_architecture
        exit 0
        ;;
    *)
        deploy_to_aws
        ;;
esac
