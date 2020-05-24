# install.sh
#
# John Newman
# 2020-05-23
#
# This script installs all of the necessary dependencies for watchtower to run.
# In summary:
# - Installs all system libs and python dependencies for watchtower.
# - Installs PiServoServer and its dependencies.
# - Configures a Firewall to only allow HTTP(S) and SSH traffic.
# - Schedules a cron job to manage disk usage.
# - Creates systemd services for watchtower and PiServoServer.
# - Creates the log directory for watchtower and the cron job.
# - Creates a simple watchtower configuration to only save motion to disk.
# - Copies the nginx app gateway config file to access watchtower via uWSGI.
# 
# Additional setup to the watchtower_config file is needed to enable Dropbox
# uploads, servo control, and the serial interface, described in the output.

set -e

WATCHTOWER_LOG_PATH="/var/log/watchtower"
WATCHTOWER_PATH=`dirname "$(readlink -f "$0")"`
SERVO_PATH="$WATCHTOWER_PATH/PiServoServer"

sudo apt update
sudo apt upgrade -y
sudo apt install -y libavutil56 libcairo-gobject2 libgtk-3-0 libpango-1.0-0 libavcodec58 libcairo2 libswscale5 libtiff5 libatk1.0-0 libavformat58 libgdk-pixbuf2.0-0 libilmbase23 libjasper1 libopenexr23 libpangocairo-1.0-0 libwebp6 libatlas-base-dev libgstreamer1.0-0 git python3-venv ufw nginx

# Set up ufw
echo "Creating firewall rules to allow http(s) traffic and ssh access..."
sudo ufw enable
sudo ufw allow 'Nginx Full'
sudo ufw allow 'ssh'

# Set up watchtower
echo "Creating Python virtual environment for watchtower..."
python3 -m venv "$WATCHTOWER_PATH/venv"
source "$WATCHTOWER_PATH/venv/bin/activate"
echo "Installing Python dependencies..."
pip install -r "$WATCHTOWER_PATH/requirements.txt"
deactivate

# Set up the servo app
echo "Setting up the optional PiServoServer app..."
git clone https://github.com/johnnewman/PiServoServer.git "$SERVO_PATH"
echo "Creating Python virtual environment for PiServoServer..."
python3 -m venv "$SERVO_PATH/venv"
source "$SERVO_PATH/venv/bin/activate"
echo "Installing Python dependencies..."
pip install -r "$SERVO_PATH/requirements.txt"
deactivate

# Create instance folder and move example configs over
mkdir -p "$WATCHTOWER_PATH/instance"
cp "$WATCHTOWER_PATH/watchtower/config/log_config_example.json" "$WATCHTOWER_PATH/instance/log_config.json"
# Remove Dropbox, Servo, and Infrared examples for a basic setup.
egrep -v "(DROPBOX_|INFRA_)" "$WATCHTOWER_PATH/watchtower/config/watchtower_config_example.json" | sed "/SERVOS/,/]/d ; /^$/d" | tac | sed "0,/,$/{s/,$//}" | tac > "$WATCHTOWER_PATH/instance/watchtower_config.json"
echo "Created $WATCHTOWER_PATH/instance directory and added config files."

# Create the logs directory with write permission.
sudo mkdir -p "$WATCHTOWER_LOG_PATH"
sudo chgrp adm "$WATCHTOWER_LOG_PATH"
sudo chmod 775 "$WATCHTOWER_LOG_PATH"
echo "Created $WATCHTOWER_LOG_PATH directory."

# Set up cron job to keep disk usage under control.
CRON_JOB="*/5 * * * * $WATCHTOWER_PATH/ancillary/pi/disk_purge.sh $WATCHTOWER_PATH/instance/recordings >> $WATCHTOWER_LOG_PATH/disk_purge.log"
CRON_JOB=`(crontab -l 2>/dev/null ; echo "$CRON_JOB")`
echo "$CRON_JOB" | crontab
echo "Created disk_purge cron job."

# Put the real user and path into the service file and install it.
sed -i".bak" "s,<user>,$USER,g ; s,<watchtower_path>,$WATCHTOWER_PATH,g" "$WATCHTOWER_PATH/ancillary/pi/watchtower.service"
sudo ln -s "$WATCHTOWER_PATH/ancillary/pi/watchtower.service" "/etc/systemd/system/"
sudo systemctl enable watchtower.service
echo "Created systemd watchtower.service file and configured it to run on boot."
echo "   NOTE: This service has not been started. More configuration is needed."

# Set up the PiServoServer service
sed -i".bak" "s,<user>,$USER,g ; s,<path>,$SERVO_PATH,g" "$SERVO_PATH/ancillary/servo.service"
sudo ln -s "$SERVO_PATH/ancillary/servo.service" "/etc/systemd/system/"
echo "Created systemd servo.service file. It is NOT configured to run on boot."
echo "   NOTE: If you are using servos, execute 'sudo systemctl enable servo.service' to have it start every system boot."

# Install nginx configuration for uWSGI and watchtower
sudo mkdir -p /etc/nginx/certs
sudo cp $WATCHTOWER_PATH/ancillary/nginx/watchtower /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/watchtower /etc/nginx/sites-enabled/

echo -e "\n\nInstallation finished! The camera is configured to record to disk at $WATCHTOWER_PATH/instance/recordings.\n\
Final steps to take: \n\
1) Required: Enable camera access via 'sudo raspiconfig'\n\
2) Optional: Enable serial access via 'sudo raspiconfig'\n\
3) Optional: To use the HTTP API, upload SSL certificates to /etc/nginx/certs\n\
             Restart nginx: 'sudo systemctl restart nginx'\n\
4) Optional: Only allow HTTP access from trusted sources by editing /etc/nginx/sites-available/watchtower\n\
5) Optional: Configure the main reverse proxy with an upstream location to this machine. See $WATCHTOWER_PATH/ancillary/nginx/reverse_proxy\n\
6) Optional: Configure $WATCHTOWER_PATH/instance/watchtower_config.json with Dropbox, infrared, or servo support"
