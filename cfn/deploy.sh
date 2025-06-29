#!/bin/bash

# Main deployment script for MealSteals CloudFormation infrastructure
# This script orchestrates the deployment of all CloudFormation stacks
# Usage: deploy.sh [--anthropic-api-key KEY] [--google-api-key KEY] [--dealfinder-image-uri URI] [--dealscraper-image-uri URI] [--resource-prefix PREFIX]

set -e  # Exit on any error

# Parse command line arguments
ANTHROPIC_API_KEY=""
GOOGLE_API_KEY=""
DEALFINDER_IMAGE_URI=""
DEALSCRAPER_IMAGE_URI=""
RESOURCE_PREFIX=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --anthropic-api-key)
            ANTHROPIC_API_KEY="$2"
            shift 2
            ;;
        --google-api-key)
            GOOGLE_API_KEY="$2"
            shift 2
            ;;
        --dealfinder-image-uri)
            DEALFINDER_IMAGE_URI="$2"
            shift 2
            ;;
        --dealscraper-image-uri)
            DEALSCRAPER_IMAGE_URI="$2"
            shift 2
            ;;
        --resource-prefix)
            RESOURCE_PREFIX="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--anthropic-api-key KEY] [--google-api-key KEY] [--dealfinder-image-uri URI] [--dealscraper-image-uri URI] [--resource-prefix PREFIX]"
            echo ""
            echo "Options:"
            echo "  --anthropic-api-key KEY          Set the Anthropic API key (optional for updates)"
            echo "  --google-api-key KEY             Set the Google API key (optional for updates)"
            echo "  --dealfinder-image-uri URI       Set the DealFinder Docker image URI (optional for updates)"
            echo "  --dealscraper-image-uri URI      Set the DealScraper Docker image URI (optional for updates)"
            echo "  --resource-prefix PREFIX         Set the resource prefix for DealDB (optional for updates)"
            echo "  -h, --help                       Show this help message"
            echo ""
            echo "Deployment sequence:"
            echo "  1. Base infrastructure (secrets, ECR repositories)"
            echo "  2. DealDB (DynamoDB tables for restaurants and deals)"
            echo "  3. DealFinder Lambda function"
            echo "  4. DealScraper Lambda function with SQS"
            echo ""
            echo "Note: For stack updates, if parameters are not provided, previous values will be used."
            echo "      For new stack creation, API keys and image URIs are required."
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_status "Starting MealSteals infrastructure deployment..."
print_status "Script directory: $SCRIPT_DIR"

# Build arguments for base-infra deployment
BASE_INFRA_ARGS=()
if [ -n "$ANTHROPIC_API_KEY" ]; then
    BASE_INFRA_ARGS+=("--anthropic-api-key" "$ANTHROPIC_API_KEY")
fi
if [ -n "$GOOGLE_API_KEY" ]; then
    BASE_INFRA_ARGS+=("--google-api-key" "$GOOGLE_API_KEY")
fi

# Deploy base infrastructure first
print_status "Deploying base infrastructure stack..."
"$SCRIPT_DIR/scripts/deploy-base-infra.sh" "${BASE_INFRA_ARGS[@]}"

# Build arguments for dealdb deployment
DEALDB_ARGS=()
if [ -n "$RESOURCE_PREFIX" ]; then
    DEALDB_ARGS+=("--resource-prefix" "$RESOURCE_PREFIX")
fi

# Deploy dealdb stack second
print_status "Deploying DealDB (DynamoDB tables) stack..."
if [ ${#DEALDB_ARGS[@]} -eq 0 ]; then
    print_warning "No DealDB parameters provided - will use previous values if stack exists"
fi
"$SCRIPT_DIR/scripts/deploy-dealdb.sh" "${DEALDB_ARGS[@]}"

# Build arguments for dealfinder deployment
DEALFINDER_ARGS=()
if [ -n "$DEALFINDER_IMAGE_URI" ]; then
    DEALFINDER_ARGS+=("--dealfinder-image-uri" "$DEALFINDER_IMAGE_URI")
fi

# Deploy dealfinder stack third
print_status "Deploying DealFinder Lambda stack..."
if [ ${#DEALFINDER_ARGS[@]} -eq 0 ]; then
    print_warning "No DealFinder image URI provided - will use previous value if stack exists"
fi
"$SCRIPT_DIR/scripts/deploy-dealfinder.sh" "${DEALFINDER_ARGS[@]}"

# Build arguments for dealscraper deployment
DEALSCRAPER_ARGS=()
if [ -n "$DEALSCRAPER_IMAGE_URI" ]; then
    DEALSCRAPER_ARGS+=("--dealscraper-image-uri" "$DEALSCRAPER_IMAGE_URI")
fi

# Deploy dealscraper stack fourth
print_status "Deploying DealScraper Lambda stack..."
if [ ${#DEALSCRAPER_ARGS[@]} -eq 0 ]; then
    print_warning "No DealScraper image URI provided - will use previous value if stack exists"
fi
"$SCRIPT_DIR/scripts/deploy-dealscraper.sh" "${DEALSCRAPER_ARGS[@]}"

print_success "All deployments completed successfully!"
print_status "Infrastructure deployment summary:"
print_status "  ✅ Base infrastructure (secrets, ECR repositories)"
print_status "  ✅ DealDB (DynamoDB tables for restaurants and deals)"
print_status "  ✅ DealFinder Lambda function"
print_status "  ✅ DealScraper Lambda function with SQS"
print_status ""
print_status "Your MealSteals infrastructure is ready for use!"
