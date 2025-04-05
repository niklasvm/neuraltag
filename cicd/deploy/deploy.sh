#!/bin/bash

source .env

echo "Deploying to $REMOTE_HOST..."

# deploy code
echo "Deploying files..."
rsync -avz -e ssh --exclude='.venv' --exclude .git --exclude uv.lock ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

# deploy service file
echo "Deploying service..."
SERVICE_FILE_BASENAME=$(basename $SERVICE_FILE)
scp $SERVICE_FILE $REMOTE_USER@$REMOTE_HOST:/tmp/${SERVICE_FILE_BASENAME}
ssh $REMOTE_USER@$REMOTE_HOST "sudo mv /tmp/${SERVICE_FILE_BASENAME} /etc/systemd/system/${SERVICE_FILE_BASENAME}"

# reload daemon
echo "Reloading daemon..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl daemon-reload"

# enable service to start on boot
echo "Enabling service..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl enable ${SERVICE_FILE_BASENAME}"

# start service
echo "Starting service..."
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl start ${SERVICE_FILE_BASENAME}"

# restart
echo "Restarting service..."s
ssh $REMOTE_USER@$REMOTE_HOST "sudo systemctl restart ${SERVICE_FILE_BASENAME}"

echo "Deployment complete"


# journalctl -u strava.service -f
# logs: journalctl -u strava.service -n 1000 --no-pager