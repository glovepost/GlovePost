#!/bin/bash

# Script to delete all EC2 instances with the name "GlovePost-Server"
set -e

# Get region from command line or use default
REGION=$(aws configure get region || echo "us-east-1")
INSTANCE_NAME="GlovePost-Server"

# Check AWS CLI and credentials
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "Searching for instances with name tag '$INSTANCE_NAME' in region $REGION..."

# Get all instance IDs with the specified name tag
INSTANCE_IDS=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text)

if [ -z "$INSTANCE_IDS" ]; then
    echo "No instances found with name '$INSTANCE_NAME'."
    exit 0
fi

# Count number of instances
INSTANCE_COUNT=$(echo "$INSTANCE_IDS" | wc -w)
echo "Found $INSTANCE_COUNT instance(s) to terminate."

# Display the instances with their details
echo "The following instances will be terminated:"
for INSTANCE_ID in $INSTANCE_IDS; do
    INSTANCE_INFO=$(aws ec2 describe-instances \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID" \
        --query "Reservations[].Instances[].[InstanceId, PublicIpAddress, State.Name, LaunchTime]" \
        --output text)
    echo "$INSTANCE_INFO"
done

# Ask for confirmation
echo "Do you want to terminate these instances? (y/n)"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Terminate instances
for INSTANCE_ID in $INSTANCE_IDS; do
    echo "Terminating instance $INSTANCE_ID..."
    
    # First verify that the root volume will be deleted on termination
    VOLUME_INFO=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" \
        --query "Reservations[].Instances[].BlockDeviceMappings[?DeviceName=='/dev/xvda' || DeviceName=='/dev/sda1'].Ebs.DeleteOnTermination" \
        --output text)
    
    if [ "$VOLUME_INFO" = "False" ]; then
        echo "Warning: Root volume for instance $INSTANCE_ID is not set to delete on termination."
        echo "Modifying instance attribute to delete root volume on termination..."
        
        # Get root device name
        ROOT_DEVICE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" \
            --query "Reservations[].Instances[].RootDeviceName" --output text)
        
        # Set DeleteOnTermination to true
        aws ec2 modify-instance-attribute --region "$REGION" --instance-id "$INSTANCE_ID" \
            --block-device-mappings "[{\"DeviceName\":\"$ROOT_DEVICE\",\"Ebs\":{\"DeleteOnTermination\":true}}]"
        
        echo "Root volume will now be deleted when instance is terminated."
    else
        echo "Root volume is already set to delete on termination."
    fi
    
    # Now terminate the instance
    aws ec2 terminate-instances --region "$REGION" --instance-ids "$INSTANCE_ID"
    echo "Instance $INSTANCE_ID termination initiated."
done

# Wait for instances to terminate
echo "Waiting for instances to terminate..."
for INSTANCE_ID in $INSTANCE_IDS; do
    aws ec2 wait instance-terminated --region "$REGION" --instance-ids "$INSTANCE_ID"
    echo "Instance $INSTANCE_ID terminated successfully."
done

echo "All instances have been terminated."

# Ask if they want to delete security group and key pair
echo "Do you want to delete the associated security group 'glovepost-sg' and key pair 'glovepost-key'? (y/n)"
read -r CLEANUP
if [[ "$CLEANUP" =~ ^[Yy]$ ]]; then
    # Find the security group
    SG_ID=$(aws ec2 describe-security-groups \
        --region "$REGION" \
        --group-names "glovepost-sg" \
        --query "SecurityGroups[0].GroupId" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
        echo "Deleting security group $SG_ID (glovepost-sg)..."
        aws ec2 delete-security-group --region "$REGION" --group-id "$SG_ID" || echo "Failed to delete security group. It may still be in use."
    else
        echo "Security group 'glovepost-sg' not found."
    fi
    
    # Check if key pair exists
    if aws ec2 describe-key-pairs --region "$REGION" --key-names "glovepost-key" &>/dev/null; then
        echo "Deleting key pair 'glovepost-key'..."
        aws ec2 delete-key-pair --region "$REGION" --key-name "glovepost-key"
        echo "You may also want to delete the local key file 'glovepost-key.pem' if it exists."
    else
        echo "Key pair 'glovepost-key' not found."
    fi
fi

echo "Cleanup completed."