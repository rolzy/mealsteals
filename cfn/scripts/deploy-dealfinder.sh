#!/bin/bash

# Deploy script for MealSteals DealFinder CloudFormation Stack
# This script builds, tests, and deploys the DealFinder Lambda function
# Usage: deploy-dealfinder.sh [--skip-build] [--google-api-key-secret-arn ARN] [--resource-prefix PREFIX]

set -e # Exit on any error

# Configuration
STACK_NAME="mealsteals-dealfinder"
TEMPLATE_FILE="cfn/mealsteals-dealfinder.yaml"
REGION="ap-southeast-2"
BASE_INFRA_STACK="mealsteals-base-infra"
DEALFINDER_DIR="dealfinder"
IMAGE_NAME="mealsteals-dealfinder"
CONTAINER_NAME="dealfinder-test"

# Parse command line arguments
SKIP_BUILD=false
GOOGLE_API_KEY_SECRET_ARN=""
RESOURCE_PREFIX=""

while [[ $# -gt 0 ]]; do
    case $1 in
    --skip-build)
        SKIP_BUILD=true
        shift
        ;;
    --google-api-key-secret-arn)
        GOOGLE_API_KEY_SECRET_ARN="$2"
        shift 2
        ;;
    --resource-prefix)
        RESOURCE_PREFIX="$2"
        shift 2
        ;;
    -h | --help)
        echo "Usage: $0 [--skip-build] [--google-api-key-secret-arn ARN] [--resource-prefix PREFIX]"
        echo ""
        echo "Options:"
        echo "  --skip-build                       Skip the build and test phase, use existing image"
        echo "  --google-api-key-secret-arn ARN    Set the Google API key secret ARN (optional)"
        echo "  --resource-prefix PREFIX           Set the resource prefix (optional)"
        echo "  -h, --help                         Show this help message"
        echo ""
        echo "This script will:"
        echo "1. Check for changes in dealfinder folder and build new image if needed"
        echo "2. Run image locally for testing with proper environment variables"
        echo "3. Wait for user confirmation before proceeding"
        echo "4. Tag image with semantic versioning and push to ECR"
        echo "5. Deploy CloudFormation stack with new image"
        exit 0
        ;;
    *)
        print_error "Unknown argument: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_build() {
    echo -e "${CYAN}[BUILD]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    if docker ps -q -f name="$CONTAINER_NAME" >/dev/null 2>&1; then
        print_status "Cleaning up test container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

print_status "Starting DealFinder build and deployment process..."

# Step 1: Check for changes and build image if needed
BUILD_NEW_IMAGE=false
DEALFINDER_IMAGE_URI=""

if [ "$SKIP_BUILD" = false ]; then
    print_build "Checking for changes in $DEALFINDER_DIR folder..."

    if [ ! -d "$DEALFINDER_DIR" ]; then
        print_error "DealFinder directory not found: $DEALFINDER_DIR"
        exit 1
    fi

    # Check if there are any uncommitted changes in the dealfinder directory
    if git status --porcelain "$DEALFINDER_DIR" 2>/dev/null | grep -q .; then
        print_build "Detected changes in $DEALFINDER_DIR folder"
        BUILD_NEW_IMAGE=true
    elif [ ! -f ".last_dealfinder_build" ]; then
        print_build "No previous build record found, building image"
        BUILD_NEW_IMAGE=true
    else
        # Check if any files in dealfinder are newer than the last build
        if find "$DEALFINDER_DIR" -newer ".last_dealfinder_build" -type f | grep -q .; then
            print_build "Found files newer than last build in $DEALFINDER_DIR"
            BUILD_NEW_IMAGE=true
        else
            print_status "No changes detected in $DEALFINDER_DIR folder"
            BUILD_NEW_IMAGE=false
        fi
    fi

    if [ "$BUILD_NEW_IMAGE" = true ]; then
        print_build "Building new DealFinder image: $IMAGE_NAME:latest"

        # Build the Docker image
        cd "$DEALFINDER_DIR"
        if ! docker build -t "$IMAGE_NAME:latest" .; then
            print_error "Failed to build Docker image"
            exit 1
        fi
        cd ..

        # Record the build time
        touch ".last_dealfinder_build"

        print_success "Successfully built $IMAGE_NAME:latest"
    else
        print_status "No changes detected, will use previous image parameter"
    fi
else
    print_status "Skipping build phase as requested"
fi

# Step 2: Only proceed with testing and ECR push if we built a new image
if [ "$BUILD_NEW_IMAGE" = true ]; then
    # Get Google API Key Secret ARN from base-infra stack
    if [ -z "$GOOGLE_API_KEY_SECRET_ARN" ]; then
        print_status "Getting Google API Key Secret ARN from base-infra stack..."
        GOOGLE_API_KEY_SECRET_ARN=$(aws cloudformation describe-stacks \
            --stack-name "$BASE_INFRA_STACK" \
            --region "$REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`GoogleApiKeySecretArn`].OutputValue' \
            --output text)

        if [ -z "$GOOGLE_API_KEY_SECRET_ARN" ]; then
            print_error "Could not retrieve Google API Key Secret ARN from base-infra stack"
            exit 1
        fi
        print_success "Retrieved Google API Key Secret ARN: $GOOGLE_API_KEY_SECRET_ARN"
    fi

    # Step 3: Run image locally for testing
    print_build "Starting local test container..."

    # Stop and remove any existing test container
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

    # Check if AWS Lambda RIE is available
    if [ ! -f ~/.aws-lambda-rie/aws-lambda-rie ]; then
        print_warning "AWS Lambda Runtime Interface Emulator not found at ~/.aws-lambda-rie/"
        print_status "You can install it with: mkdir -p ~/.aws-lambda-rie && curl -Lo ~/.aws-lambda-rie/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && chmod +x ~/.aws-lambda-rie/aws-lambda-rie"
    fi

    # Run the container in detached mode
    print_status "Running test container with environment variables..."
    CONTAINER_ID=$(docker run -d \
        --name "$CONTAINER_NAME" \
        --platform linux/amd64 \
        -p 9000:8080 \
        -e GOOGLE_API_KEY_SECRET_ARN="$GOOGLE_API_KEY_SECRET_ARN" \
        -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
        -e AWS_DEFAULT_REGION="$REGION" \
        "$IMAGE_NAME:latest")

    if [ $? -ne 0 ]; then
        print_error "Failed to start test container"
        exit 1
    fi

    print_success "Local test container is running!"
    print_status "Container ID: $CONTAINER_ID"
    print_status "Lambda function available at: http://localhost:9000/2015-03-31/functions/function/invocations"
    print_status ""
    print_status "You can test the function with:"
    print_status "curl -XPOST 'http://localhost:9000/2015-03-31/functions/function/invocations' -d '{\"address\": \"Brisbane CBD\", \"radius\": 2000}'"
    print_status ""
    print_warning "Container logs will be displayed below. Press Ctrl+C to stop log streaming when ready to proceed."
    print_status "After reviewing logs, type 'proceed' to continue with deployment or 'abort' to stop:"

    # Display logs
    docker logs -f "$CONTAINER_NAME" &
    LOGS_PID=$!

    # Wait for user input
    while true; do
        read -p "$(echo -e "${YELLOW}Ready to proceed? (proceed/abort): ${NC}")" response
        case $response in
        proceed | p | yes | y)
            print_success "Proceeding with deployment..."
            break
            ;;
        abort | a | no | n)
            print_warning "Deployment aborted by user"
            kill $LOGS_PID >/dev/null 2>&1 || true
            exit 0
            ;;
        *)
            print_warning "Please enter 'proceed' or 'abort'"
            ;;
        esac
    done

    # Stop log streaming
    kill $LOGS_PID >/dev/null 2>&1 || true

    # Step 4: Stop test container and login to ECR
    print_status "Stopping test container..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1

    print_status "Logging into AWS ECR..."
    aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com"

    # Step 5: Get ECR repository URI and determine next version
    print_status "Getting ECR repository information..."
    ECR_REPO_URI=$(aws cloudformation describe-stacks \
        --stack-name "$BASE_INFRA_STACK" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`DealFinderECRRepositoryUri`].OutputValue' \
        --output text)

    if [ -z "$ECR_REPO_URI" ]; then
        print_error "Could not retrieve ECR repository URI from base-infra stack"
        exit 1
    fi

    print_success "ECR Repository URI: $ECR_REPO_URI"

    # Get latest version tag
    print_status "Determining next version number..."
    LATEST_TAG=$(aws ecr describe-images \
        --repository-name "mealsteals-dealfinder" \
        --region "$REGION" \
        --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' \
        --output text 2>/dev/null || echo "v0.0.0")

    if [ "$LATEST_TAG" = "None" ] || [ -z "$LATEST_TAG" ]; then
        LATEST_TAG="v0.0.0"
    fi

    print_status "Latest tag in ECR: $LATEST_TAG"

    # Parse version and increment patch (support v prefix)
    if [[ $LATEST_TAG =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        MAJOR=${BASH_REMATCH[1]}
        MINOR=${BASH_REMATCH[2]}
        PATCH=${BASH_REMATCH[3]}
        NEW_PATCH=$((PATCH + 1))
        NEW_TAG="v$MAJOR.$MINOR.$NEW_PATCH"
    elif [[ $LATEST_TAG =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        # Handle legacy tags without v prefix
        MAJOR=${BASH_REMATCH[1]}
        MINOR=${BASH_REMATCH[2]}
        PATCH=${BASH_REMATCH[3]}
        NEW_PATCH=$((PATCH + 1))
        NEW_TAG="v$MAJOR.$MINOR.$NEW_PATCH"
        print_warning "Found legacy tag without 'v' prefix, upgrading to: $NEW_TAG"
    else
        print_warning "Could not parse version tag '$LATEST_TAG', starting with v0.0.1"
        NEW_TAG="v0.0.1"
    fi

    print_success "New version tag: $NEW_TAG"

    # Step 6: Tag and push image
    print_status "Tagging image with version $NEW_TAG..."
    docker tag "$IMAGE_NAME:latest" "$ECR_REPO_URI:$NEW_TAG"
    docker tag "$IMAGE_NAME:latest" "$ECR_REPO_URI:latest"

    print_status "Pushing image to ECR..."
    docker push "$ECR_REPO_URI:$NEW_TAG"
    docker push "$ECR_REPO_URI:latest"

    print_success "Successfully pushed image to ECR"
    DEALFINDER_IMAGE_URI="$ECR_REPO_URI:$NEW_TAG"

    print_status "Using new image URI for deployment: $DEALFINDER_IMAGE_URI"
else
    print_status "No new image built, will use previous parameter value in CloudFormation"
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    print_error "Template file not found: $TEMPLATE_FILE"
    exit 1
fi

print_status "Starting deployment of $STACK_NAME stack..."

# Check if stack exists
print_status "Checking if stack $STACK_NAME exists..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
    STACK_EXISTS=true
    print_status "Stack exists. Will perform update operation."
else
    STACK_EXISTS=false
    print_status "Stack does not exist. Will perform create operation."
fi

# Validate template first
print_status "Validating CloudFormation template..."
if aws cloudformation validate-template --template-body file://"$TEMPLATE_FILE" --region "$REGION" >/dev/null; then
    print_success "Template validation passed"
else
    print_error "Template validation failed"
    exit 1
fi

# Build parameters array for stack operations
build_parameters() {
    local parameters=()

    # DealFinder Image URI parameter
    if [ -n "$DEALFINDER_IMAGE_URI" ]; then
        parameters+=("ParameterKey=DealFinderImageUri,ParameterValue=$DEALFINDER_IMAGE_URI")
    else
        parameters+=("ParameterKey=DealFinderImageUri,UsePreviousValue=true")
    fi

    # Google API Key Secret ARN parameter (optional - uses imported value if not provided)
    if [ -n "$GOOGLE_API_KEY_SECRET_ARN" ]; then
        parameters+=("ParameterKey=GoogleApiKeySecretArn,ParameterValue=$GOOGLE_API_KEY_SECRET_ARN")
    else
        parameters+=("ParameterKey=GoogleApiKeySecretArn,UsePreviousValue=true")
    fi

    # Resource Prefix parameter
    if [ -n "$RESOURCE_PREFIX" ]; then
        parameters+=("ParameterKey=ResourcePrefix,ParameterValue=$RESOURCE_PREFIX")
    else
        parameters+=("ParameterKey=ResourcePrefix,UsePreviousValue=true")
    fi

    echo "${parameters[@]}"
}

# Deploy the stack
if [ "$STACK_EXISTS" = true ]; then
    print_status "Updating existing stack..."

    # Build parameters
    PARAMETERS=($(build_parameters))

    if [ -n "$DEALFINDER_IMAGE_URI" ]; then
        print_status "Using new image: $DEALFINDER_IMAGE_URI"
    else
        print_status "No new image built, using previous image parameter"
    fi

    if [ -n "$GOOGLE_API_KEY_SECRET_ARN" ] || [ -n "$RESOURCE_PREFIX" ]; then
        print_status "Using some provided parameter values (others will use previous values)"
    fi

    # Execute update with parameters
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters "${PARAMETERS[@]}" \
        2>&1 || true)

    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
        print_warning "No updates needed - stack is already up to date"
        exit 0
    elif echo "$UPDATE_OUTPUT" | grep -q "ValidationError"; then
        print_error "Update failed with validation error:"
        echo "$UPDATE_OUTPUT"
        exit 1
    else
        print_status "Update initiated successfully"
        OPERATION="UPDATE"
    fi
else
    print_status "Creating new stack..."

    # For new stacks, we need the image URI
    if [ -z "$DEALFINDER_IMAGE_URI" ]; then
        print_error "For new stack creation, --dealfinder-image-uri is required"
        exit 1
    fi

    # Build parameters for create
    CREATE_PARAMETERS=(
        "ParameterKey=DealFinderImageUri,ParameterValue=$DEALFINDER_IMAGE_URI"
    )

    # Add optional parameters if provided
    if [ -n "$GOOGLE_API_KEY_SECRET_ARN" ]; then
        CREATE_PARAMETERS+=("ParameterKey=GoogleApiKeySecretArn,ParameterValue=$GOOGLE_API_KEY_SECRET_ARN")
    fi

    if [ -n "$RESOURCE_PREFIX" ]; then
        CREATE_PARAMETERS+=("ParameterKey=ResourcePrefix,ParameterValue=$RESOURCE_PREFIX")
    fi

    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters "${CREATE_PARAMETERS[@]}"

    print_status "Create initiated successfully"
    OPERATION="CREATE"
fi

# Wait for stack operation to complete
print_status "Waiting for stack $OPERATION to complete..."
print_status "This may take a few minutes..."

if [ "$OPERATION" = "UPDATE" ]; then
    WAIT_CONDITION="stack-update-complete"
else
    WAIT_CONDITION="stack-create-complete"
fi

if aws cloudformation wait "$WAIT_CONDITION" --stack-name "$STACK_NAME" --region "$REGION"; then
    print_success "Stack $OPERATION completed successfully!"
else
    print_error "Stack $OPERATION failed or timed out"

    # Get stack events to show what went wrong
    print_status "Recent stack events:"
    aws cloudformation describe-stack-events \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'StackEvents[0:10].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId,ResourceStatusReason]' \
        --output table

    exit 1
fi

# Show stack outputs
print_status "Stack outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' \
    --output table

# Show exported values
print_status "Exported values (for use in other stacks):"
aws cloudformation list-exports \
    --region "$REGION" \
    --query 'Exports[?starts_with(Name, `MealSteals-DealFinder`)].[Name,Value]' \
    --output table

print_success "DealFinder deployment completed successfully!"
if [ -n "$NEW_TAG" ]; then
    print_status "New image version deployed: $NEW_TAG"
else
    print_status "Used previous image version (no changes detected)"
fi
print_status "Stack ARN: $(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackId' --output text)"
