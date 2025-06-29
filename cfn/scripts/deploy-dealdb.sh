#!/bin/bash

# Deploy script for MealSteals DealDB CloudFormation Stack
# This script deploys the DynamoDB tables for restaurants and deals
# Usage: deploy-dealdb.sh [--resource-prefix PREFIX] [--billing-mode MODE] [--read-capacity N] [--write-capacity N]

set -e  # Exit on any error

# Configuration
STACK_NAME="mealsteals-dealdb"
TEMPLATE_FILE="cfn/mealsteals-dealdb.yaml"
REGION="ap-southeast-2"

# Parse command line arguments
RESOURCE_PREFIX=""
BILLING_MODE=""
READ_CAPACITY_UNITS=""
WRITE_CAPACITY_UNITS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-prefix)
            RESOURCE_PREFIX="$2"
            shift 2
            ;;
        --billing-mode)
            BILLING_MODE="$2"
            shift 2
            ;;
        --read-capacity)
            READ_CAPACITY_UNITS="$2"
            shift 2
            ;;
        --write-capacity)
            WRITE_CAPACITY_UNITS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--resource-prefix PREFIX] [--billing-mode MODE] [--read-capacity N] [--write-capacity N]"
            echo ""
            echo "Options:"
            echo "  --resource-prefix PREFIX     Set the resource prefix (optional)"
            echo "  --billing-mode MODE          Set DynamoDB billing mode: PAY_PER_REQUEST or PROVISIONED (optional)"
            echo "  --read-capacity N            Set read capacity units for PROVISIONED mode (optional)"
            echo "  --write-capacity N           Set write capacity units for PROVISIONED mode (optional)"
            echo "  -h, --help                   Show this help message"
            echo ""
            echo "Note: For stack updates, if parameters are not provided, previous values will be used."
            echo "      Default values: resource-prefix=mealsteals-dealdb, billing-mode=PAY_PER_REQUEST"
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

print_status "Starting DealDB deployment..."

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    print_error "Template file not found: $TEMPLATE_FILE"
    exit 1
fi

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
    
    # Resource Prefix parameter
    if [ -n "$RESOURCE_PREFIX" ]; then
        parameters+=("ParameterKey=ResourcePrefix,ParameterValue=$RESOURCE_PREFIX")
    else
        parameters+=("ParameterKey=ResourcePrefix,UsePreviousValue=true")
    fi
    
    # Billing Mode parameter
    if [ -n "$BILLING_MODE" ]; then
        parameters+=("ParameterKey=BillingMode,ParameterValue=$BILLING_MODE")
    else
        parameters+=("ParameterKey=BillingMode,UsePreviousValue=true")
    fi
    
    # Read Capacity Units parameter
    if [ -n "$READ_CAPACITY_UNITS" ]; then
        parameters+=("ParameterKey=ReadCapacityUnits,ParameterValue=$READ_CAPACITY_UNITS")
    else
        parameters+=("ParameterKey=ReadCapacityUnits,UsePreviousValue=true")
    fi
    
    # Write Capacity Units parameter
    if [ -n "$WRITE_CAPACITY_UNITS" ]; then
        parameters+=("ParameterKey=WriteCapacityUnits,ParameterValue=$WRITE_CAPACITY_UNITS")
    else
        parameters+=("ParameterKey=WriteCapacityUnits,UsePreviousValue=true")
    fi
    
    echo "${parameters[@]}"
}

# Deploy the stack
if [ "$STACK_EXISTS" = true ]; then
    print_status "Updating existing stack..."
    
    # Build parameters
    PARAMETERS=($(build_parameters))
    
    if [ -n "$RESOURCE_PREFIX" ] || [ -n "$BILLING_MODE" ] || [ -n "$READ_CAPACITY_UNITS" ] || [ -n "$WRITE_CAPACITY_UNITS" ]; then
        print_status "Using provided parameter values (others will use previous values)"
    else
        print_status "Using all previous parameter values"
    fi
    
    # Execute update with parameters
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --parameters "${PARAMETERS[@]}" \
        2>&1 || true)
    
    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
        print_warning "No updates needed - stack is already up to date"
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
    
    # Build parameters for create (use defaults if not provided)
    CREATE_PARAMETERS=()
    
    if [ -n "$RESOURCE_PREFIX" ]; then
        CREATE_PARAMETERS+=("ParameterKey=ResourcePrefix,ParameterValue=$RESOURCE_PREFIX")
    fi
    
    if [ -n "$BILLING_MODE" ]; then
        CREATE_PARAMETERS+=("ParameterKey=BillingMode,ParameterValue=$BILLING_MODE")
    fi
    
    if [ -n "$READ_CAPACITY_UNITS" ]; then
        CREATE_PARAMETERS+=("ParameterKey=ReadCapacityUnits,ParameterValue=$READ_CAPACITY_UNITS")
    fi
    
    if [ -n "$WRITE_CAPACITY_UNITS" ]; then
        CREATE_PARAMETERS+=("ParameterKey=WriteCapacityUnits,ParameterValue=$WRITE_CAPACITY_UNITS")
    fi
    
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --region "$REGION" \
        --parameters "${CREATE_PARAMETERS[@]}"
    
    print_status "Create initiated successfully"
    OPERATION="CREATE"
fi

# Wait for stack operation to complete (only if we actually performed an operation)
if [ -n "$OPERATION" ]; then
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
        --query 'Exports[?starts_with(Name, `mealsteals-dealdb`)].[Name,Value]' \
        --output table
fi

print_success "DealDB deployment completed successfully!"
print_status "DynamoDB tables are ready for use."
print_status "Stack ARN: $(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackId' --output text)"
