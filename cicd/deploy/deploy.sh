#!/bin/bash

source .env

echo "Deploying to $REMOTE_HOST..."

# deploy app and env files
echo "Deploying files..."
sshpass -p $REMOTE_PASSWORD scp $ENV_FILE $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH
sshpass -p $REMOTE_PASSWORD scp $APP_FILE $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH
sshpass -p $REMOTE_PASSWORD scp $REQUIREMENTS_FILE $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH

# create virtual environment
# sshpass -p $REMOTE_PASSWORD ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt"

# deploy service file
echo "Deploying service..."
SERVICE_FILE_BASENAME=$(basename $SERVICE_FILE)
sshpass -p $REMOTE_PASSWORD scp $SERVICE_FILE $REMOTE_USER@$REMOTE_HOST:/tmp/${SERVICE_FILE_BASENAME}
sshpass -p $REMOTE_PASSWORD ssh $REMOTE_USER@$REMOTE_HOST "sudo mv /tmp/${SERVICE_FILE_BASENAME} /etc/systemd/system/${SERVICE_FILE_BASENAME}"

# reload daemon
sshpass -p $REMOTE_PASSWORD ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl daemon-reload"

# enable service to start on boot
sshpass -p $REMOTE_PASSWORD ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl enable ${SERVICE_FILE_BASENAME}"

# start service
sshpass -p $REMOTE_PASSWORD ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl start ${SERVICE_FILE_BASENAME}"

echo "Deployment complete"