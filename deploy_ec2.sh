#!/bin/bash

# AWS EC2 Deployment Script for GlovePost
set -e

# Default values
REGION=$(aws configure get region || echo "us-east-1")
INSTANCE_TYPE="t2.micro"
KEY_NAME="glovepost-key"
SECURITY_GROUP_NAME="glovepost-sg"
INSTANCE_NAME="GlovePost-Server"
REPO_URL="https://github.com/glovepost/GlovePost.git"
GIT_PAT="${GIT_PAT:-}"  # Set via environment variable (e.g., export GIT_PAT=your_pat_here)

# Check AWS CLI and credentials
command -v aws &> /dev/null || { echo "AWS CLI not installed."; exit 1; }
aws sts get-caller-identity &> /dev/null || { echo "AWS credentials not configured."; exit 1; }

# Verify EC2 permissions
echo "Verifying EC2 permissions..."
aws ec2 describe-key-pairs --query 'KeyPairs' --output text &> /dev/null || { echo "Insufficient EC2 permissions."; exit 1; }

# Cleanup on failure
cleanup() {
    echo "Cleaning up..."
    aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION" || true
    [ -n "$SECURITY_GROUP_ID" ] && aws ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" --region "$REGION" || true
    rm -f "${KEY_NAME}.pem"
}
trap cleanup EXIT

# Key pair management
if aws ec2 describe-key-pairs --region "$REGION" --key-names "$KEY_NAME" &>/dev/null; then
    echo "Key pair $KEY_NAME already exists"
    if [ ! -f "${KEY_NAME}.pem" ]; then
        echo "Warning: Local key file ${KEY_NAME}.pem missing. Recreating key pair (this may affect other instances)."
        aws ec2 delete-key-pair --region "$REGION" --key-name "$KEY_NAME"
        echo "Creating new key pair..."
        aws ec2 create-key-pair --region "$REGION" --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > "${KEY_NAME}.pem" || { echo "Failed to create key pair."; exit 1; }
        chmod 400 "${KEY_NAME}.pem"
        echo "New key pair created and saved to ${KEY_NAME}.pem"
    else
        echo "Using existing key file ${KEY_NAME}.pem"
    fi
else
    echo "Creating key pair..."
    aws ec2 create-key-pair --region "$REGION" --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > "${KEY_NAME}.pem" || { echo "Failed to create key pair."; exit 1; }
    chmod 400 "${KEY_NAME}.pem"
    echo "Key pair created and saved to ${KEY_NAME}.pem"
fi

SSH_KEY="${KEY_NAME}.pem"

# Security group management
echo "Checking for existing security group..."
SG_EXISTS=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)
if [ "$SG_EXISTS" != "None" ] && [ -n "$SG_EXISTS" ]; then
    echo "Using existing security group $SECURITY_GROUP_NAME ($SG_EXISTS)"
    SECURITY_GROUP_ID=$SG_EXISTS
else
    echo "Creating security group..."
    SECURITY_GROUP_ID=$(aws ec2 create-security-group --region "$REGION" --group-name "$SECURITY_GROUP_NAME" --description "Security group for GlovePost" --query 'GroupId' --output text)
    MY_IP=$(curl -s ifconfig.me 2>/dev/null || echo "0.0.0.0")/32
    if [ "$MY_IP" = "0.0.0.0/32" ]; then
        echo "Warning: Failed to get public IP. Allowing SSH from all (0.0.0.0/0) - this is insecure!"
    else
        echo "Using IP $MY_IP for SSH access"
    fi
    aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 22 --cidr "$MY_IP" || true
    aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 || true
    aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 443 --cidr 0.0.0.0/0 || true
fi

# Get latest Amazon Linux 2023 AMI
echo "Fetching latest AL2023 AMI..."
AMI_ID=$(aws ec2 describe-images --region "$REGION" --owners amazon --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text)
[ -z "$AMI_ID" ] && { echo "No AL2023 AMI found."; exit 1; }

# Handle Git PAT
if [ -n "$GIT_PAT" ]; then
    REPO_URL="https://${GIT_PAT}@github.com/glovepost/GlovePost.git"
    echo "Using authenticated Git URL"
else
    echo "Warning: GIT_PAT not set. Using unauthenticated URL (may fail for private repos)."
fi

# User-data script
cat > user-data.sh << USERDATA
#!/bin/bash
exec > >(tee -a /var/log/glovepost-setup.log) 2>&1
echo "Starting user-data script at \$(date)"

dnf update -y
dnf install -y git nodejs python3-pip

# Install PostgreSQL
echo "Installing PostgreSQL..."
dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf -qy module disable postgresql
dnf install -y postgresql16-server postgresql16

# Initialize PostgreSQL database
echo "Initializing PostgreSQL..."
/usr/pgsql-16/bin/postgresql-16-setup initdb 2>&1 | tee -a /var/log/glovepost-setup.log

# Enable and start PostgreSQL service
systemctl enable postgresql-16
echo "Starting PostgreSQL..."
systemctl start postgresql-16 2>&1 | tee -a /var/log/glovepost-setup.log

# Wait for PostgreSQL to be active (up to 30 seconds)
echo "Waiting for PostgreSQL to start..."
MAX_WAIT=30
WAIT_INTERVAL=5
ELAPSED=0
until systemctl is-active --quiet postgresql-16; do
    echo "PostgreSQL not active yet, waiting... ($ELAPSED/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
    if [ $ELAPSED -ge $MAX_WAIT ]; then
        echo "ERROR: PostgreSQL failed to start after $MAX_WAIT seconds."
        systemctl status postgresql-16 --no-pager >> /var/log/glovepost-setup.log
        echo "Continuing deployment despite PostgreSQL failure for debugging..."
        PG_FAILED=true
        break
    fi
done

# Configure PostgreSQL if it started
if [ -z "$PG_FAILED" ]; then
    echo "Configuring PostgreSQL database and user..."
    sudo -u postgres psql <<'PGEOF' 2>&1 | tee -a /var/log/glovepost-setup.log
CREATE DATABASE glovepost;
CREATE USER glovepost WITH ENCRYPTED PASSWORD 'glovepost';
GRANT ALL PRIVILEGES ON DATABASE glovepost TO glovepost;
PGEOF
    if [ $? -eq 0 ]; then
        echo "PostgreSQL database and user created successfully."
    else
        echo "ERROR: Failed to configure PostgreSQL database."
        PG_FAILED=true
    fi
else
    echo "Skipping PostgreSQL configuration due to startup failure."
fi

# Install MongoDB
cat > /etc/yum.repos.d/mongodb-org-7.repo << 'EOF'
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-7.0.asc
EOF
dnf install -y mongodb-org
systemctl enable mongod
systemctl start mongod

# Clone repository
cd /home/ec2-user
git clone "$REPO_URL" GlovePost || { echo "Git clone failed"; exit 1; }
cd GlovePost/backend
npm install
npm install pg --save
npm install -g npm@latest
npm audit fix --force || echo "Some vulnerabilities remain"

cat > .env << 'ENVFILE'
PORT=3000
MONGO_URI=mongodb://localhost:27017/glovepost
PG_URI=postgresql://glovepost:glovepost@localhost:5432/glovepost
ENVFILE

node scripts/setup_database.js || echo "Database setup failed, continuing"

cd ../frontend/glovepost-ui
npm install
npm run build

cd ../..
mkdir -p scripts
cd scripts
python3 -m venv venv
source venv/bin/activate
if [ -f ../requirements.txt ]; then
    pip install -r ../requirements.txt
else
    pip install requests beautifulsoup4 feedparser pymongo python-dotenv
fi

if [ -f setup_ml_env.sh ]; then
    chmod +x setup_ml_env.sh
    ./setup_ml_env.sh || echo "setup_ml_env.sh failed"
else
    echo "setup_ml_env.sh not found, skipping"
fi
deactivate

export HOME=/root
npm install -g pm2
cd ..
pm2 start backend/server.js --name "glovepost-backend" || echo "Backend start failed"
pm2 serve frontend/glovepost-ui/build 3001 --name "glovepost-frontend" --spa
PM2_HOME=/root/.pm2 pm2 startup systemd -u root --hp /root
pm2 save

dnf install -y nginx
systemctl enable nginx
systemctl start nginx

cat > /etc/nginx/conf.d/glovepost.conf << 'NGINXCONF'
server {
    listen 80;
    server_name _;
    access_log /var/log/nginx/glovepost.access.log;
    error_log /var/log/nginx/glovepost.error.log;
    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
    location /api {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
NGINXCONF

nginx -t && systemctl restart nginx || { echo "Nginx config failed"; exit 1; }

echo "User-data script completed at \$(date)"
USERDATA

echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SECURITY_GROUP_ID" \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"DeleteOnTermination":true,"VolumeSize":8}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --user-data file://user-data.sh \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Waiting for SSH to be available..."
MAX_WAIT=300
WAIT_INTERVAL=10
ELAPSED=0
until ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "echo SSH ready" 2>/dev/null; do
    echo "SSH not ready yet, waiting... ($ELAPSED/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
    [ $ELAPSED -ge $MAX_WAIT ] && { echo "Error: SSH timeout."; exit 1; }
done

echo "Checking initial deployment status..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo systemctl status cloud-final --no-pager; sudo tail -n 10 /var/log/glovepost-setup.log"

echo "Starting continuous log monitoring..."
echo "Press Ctrl+C to stop monitoring (deployment continues in background)"
trap 'echo "Monitoring stopped."; MONITORING_STOPPED=true' INT
MONITORING_STOPPED=false
DEPLOYMENT_COMPLETE=false

while ! $MONITORING_STOPPED && ! $DEPLOYMENT_COMPLETE; do
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo tail -n 10 /var/log/glovepost-setup.log" 2>/dev/null || true
    if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo grep -q 'User-data script completed' /var/log/glovepost-setup.log" 2>/dev/null; then
        DEPLOYMENT_COMPLETE=true
        echo "Deployment completed!"
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo tail -n 30 /var/log/glovepost-setup.log"
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo systemctl is-active postgresql-16 && echo 'PostgreSQL: Running' || echo 'PostgreSQL: Not running'; sudo systemctl is-active mongod && echo 'MongoDB: Running' || echo 'MongoDB: Not running'; sudo systemctl is-active nginx && echo 'Nginx: Running' || echo 'Nginx: Not running'; pm2 list"
    fi
    sleep 5
done

trap - INT
if $MONITORING_STOPPED && ! $DEPLOYMENT_COMPLETE; then
    echo "To resume monitoring: ssh -i $SSH_KEY ec2-user@$PUBLIC_IP \"sudo tail -f /var/log/glovepost-setup.log\""
    read -p "Wait silently for completion? (y/n): " WAIT_RESPONSE
    if [[ "$WAIT_RESPONSE" =~ ^[Yy]$ ]]; then
        while ! ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo grep -q 'User-data script completed' /var/log/glovepost-setup.log" 2>/dev/null; do
            sleep 10
        done
        echo "Deployment completed!"
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "sudo systemctl is-active postgresql-16 && echo 'PostgreSQL: Running' || echo 'PostgreSQL: Not running'; sudo systemctl is-active mongod && echo 'MongoDB: Running' || echo 'MongoDB: Not running'; sudo systemctl is-active nginx && echo 'Nginx: Running' || echo 'Nginx: Not running'; pm2 list"
    fi
fi

echo "======================================================================"
echo "EC2 instance created successfully!"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "SSH Access: ssh -i $SSH_KEY ec2-user@$PUBLIC_IP"
echo "Frontend: http://$PUBLIC_IP"
echo "Backend API: http://$PUBLIC_IP/api"
echo "======================================================================"

rm -f user-data.sh
trap - EXIT