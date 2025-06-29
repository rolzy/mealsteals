#!/bin/bash

# Deploy script for MealSteals Base Infrastructure CloudFormation Stack
# This script updates the existing base-infra stack or creates it if it doesn't exist
# Usage: deploy-base-infra.sh [--anthropic-api-key KEY] [--google-api-key KEY]

set -e  # Exit on any error

# Configuration
STACK_NAME="mealsteals-base-infra"
TEMPLATE_FILE="cfn/mealsteals-base-infra.yaml"
REGION="ap-southeast-2"  # Based on your AWS_DEFAULT_REGION from context

# Parse command line arguments
ANTHROPIC_API_KEY=""
GOOGLE_API_KEY=""

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
        *)
            print_error "Unknown argument: $1"
            echo "Usage: $0 [--anthropic-api-key KEY] [--google-api-key KEY]"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    
    # Always include both parameters - either with new values or using previous values
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        parameters+=("ParameterKey=AnthropicApiKey,ParameterValue=$ANTHROPIC_API_KEY")
    else
        parameters+=("ParameterKey=AnthropicApiKey,UsePreviousValue=true")
    fi
    
    if [ -n "$GOOGLE_API_KEY" ]; then
        parameters+=("ParameterKey=GoogleApiKey,ParameterValue=$GOOGLE_API_KEY")
    else
        parameters+=("ParameterKey=GoogleApiKey,UsePreviousValue=true")
    fi
    
    echo "${parameters[@]}"
}

# Deploy the stack
if [ "$STACK_EXISTS" = true ]; then
    print_status "Updating existing stack..."
    
    # Build parameters
    PARAMETERS=($(build_parameters))
    
    if [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
        print_status "Using provided parameter values (others will use previous values)"
    else
        print_status "Using all previous parameter values"
    fi
    
    # Execute update with parameters
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --capabilities CAPABILITY_IAM \
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
    
    # For new stacks, we need actual parameter values
    if [ -z "$ANTHROPIC_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then
        print_error "For new stack creation, both --anthropic-api-key and --google-api-key are required"
        exit 1
    fi
    
    # Build parameters for create
    CREATE_PARAMETERS=(
        "ParameterKey=AnthropicApiKey,ParameterValue=$ANTHROPIC_API_KEY"
        "ParameterKey=GoogleApiKey,ParameterValue=$GOOGLE_API_KEY"
    )
    
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --capabilities CAPABILITY_IAM \
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
    --query 'Exports[?starts_with(Name, `MealSteals`)].[Name,Value]' \
    --output table

print_success "Deployment completed successfully!"
print_status "Stack ARN: $(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackId' --output text)"
