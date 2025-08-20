#!/bin/bash

# Multi-Environment Deployment Script for Native IQ
set -e

ENVIRONMENT=${1:-local}
VALID_ENVS=("local" "staging" "production")

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Native IQ Deployment - $1${NC}"
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

# Validate environment
if [[ ! " ${VALID_ENVS[@]} " =~ " ${ENVIRONMENT} " ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Valid environments: ${VALID_ENVS[*]}"
    exit 1
fi

print_header "$ENVIRONMENT Environment"

# Check required files
check_requirements() {
    echo "🔍 Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment files
    if [ ! -f "environments/${ENVIRONMENT}.env" ]; then
        print_error "Environment file not found: environments/${ENVIRONMENT}.env"
        exit 1
    fi
    
    if [ ! -f "../.env" ] && [ "$ENVIRONMENT" = "local" ]; then
        print_warning ".env file not found. Copying from example.env"
        cp ../example.env ../.env
    fi
    
    print_success "Requirements check passed"
}

# Deploy based on environment
deploy_local() {
    print_header "Local Development Deployment"
    
    # Create data directory
    mkdir -p ../data/chromadb ../logs
    
    # Start services
    docker-compose -f docker-compose.local.yml down
    docker-compose -f docker-compose.local.yml build
    docker-compose -f docker-compose.local.yml up -d
    
    # Wait for services
    echo "⏳ Waiting for services to start..."
    sleep 15
    
    # Health checks
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Native IQ API is healthy at http://localhost:8000"
    else
        print_error "Native IQ API health check failed"
        docker-compose -f docker-compose.local.yml logs native-iq
        exit 1
    fi
    
    # Test Redis
    if docker-compose -f docker-compose.local.yml exec -T redis redis-cli ping | grep -q PONG; then
        print_success "Redis is healthy"
    else
        print_error "Redis health check failed"
        exit 1
    fi
    
    echo ""
    print_success "Local deployment complete!"
    echo "📍 API: http://localhost:8000"
    echo "📍 Redis: localhost:6379"
    echo "📍 DynamoDB Local: http://localhost:8001"
    echo ""
    echo "Commands:"
    echo "  View logs: docker-compose -f deployment/docker-compose.local.yml logs -f"
    echo "  Stop: docker-compose -f deployment/docker-compose.local.yml down"
}

deploy_staging() {
    print_header "Staging Environment Deployment"
    
    # Check staging requirements
    if [ ! -f "../.env.staging" ]; then
        print_error "Staging environment file not found: .env.staging"
        echo "Create .env.staging with your staging credentials"
        exit 1
    fi
    
    # Deploy with Traefik for SSL
    docker-compose -f docker-compose.staging.yml down
    docker-compose -f docker-compose.staging.yml build
    docker-compose -f docker-compose.staging.yml up -d
    
    echo "⏳ Waiting for services and SSL certificates..."
    sleep 30
    
    print_success "Staging deployment initiated!"
    echo "📍 API: https://staging-api.nativeiq.tech"
    echo "📍 Traefik Dashboard: https://staging-api.nativeiq.tech:8080"
    echo ""
    echo "Note: SSL certificates may take a few minutes to provision"
}

deploy_production() {
    print_header "Production Environment Deployment"
    
    # Production safety checks
    echo "🔒 Production deployment requires additional confirmation"
    read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_warning "Production deployment cancelled"
        exit 0
    fi
    
    # Check production requirements
    if [ ! -f "../.env.production" ]; then
        print_error "Production environment file not found: .env.production"
        exit 1
    fi
    
    print_warning "Production deployment would be handled by CI/CD pipeline"
    print_warning "For manual production deployment, use AWS ECS/EKS or similar"
    
    echo "Recommended production setup:"
    echo "1. AWS ECS with Application Load Balancer"
    echo "2. Route 53 for DNS (api.nativeiq.tech)"
    echo "3. ACM for SSL certificates"
    echo "4. ElastiCache for Redis"
    echo "5. DynamoDB in production region"
}

# DNS Setup Information
show_dns_setup() {
    print_header "DNS Configuration Guide"
    
    echo "For proper API endpoint setup, configure these DNS records:"
    echo ""
    echo "🌐 Local Development:"
    echo "   No DNS needed - use localhost:8000"
    echo ""
    echo "🌐 Staging Environment:"
    echo "   staging-api.nativeiq.tech → Your staging server IP"
    echo "   Type: A Record"
    echo ""
    echo "🌐 Production Environment:"
    echo "   api.nativeiq.tech → Your production load balancer"
    echo "   Type: A Record or CNAME to ALB"
    echo ""
    echo "SSL certificates are automatically handled by:"
    echo "• Local: No SSL (HTTP only)"
    echo "• Staging: Let's Encrypt via Traefik"
    echo "• Production: AWS Certificate Manager (recommended)"
}

# Main execution
main() {
    check_requirements
    
    case $ENVIRONMENT in
        "local")
            deploy_local
            ;;
        "staging")
            deploy_staging
            ;;
        "production")
            deploy_production
            ;;
    esac
    
    if [ "$2" = "--show-dns" ]; then
        show_dns_setup
    fi
}

# Help function
show_help() {
    echo "Native IQ Multi-Environment Deployment"
    echo ""
    echo "Usage: $0 [ENVIRONMENT] [OPTIONS]"
    echo ""
    echo "Environments:"
    echo "  local      - Local development (default)"
    echo "  staging    - Staging environment with SSL"
    echo "  production - Production deployment guide"
    echo ""
    echo "Options:"
    echo "  --show-dns - Show DNS configuration guide"
    echo "  --help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 local"
    echo "  $0 staging --show-dns"
    echo "  $0 production"
}

# Parse arguments
if [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

main "$@"
