# install.sh
#
# John Newman
# 2020-05-23
#
# This script installs all of the necessary dependencies for Watchtower to run.
# In summary:
# - Installs all system libs and python dependencies for Watchtower.
# - Installs Icebox and its dependencies for cooling the system.
# - Configures a Firewall to only allow HTTP(S) and SSH traffic.
# - Schedules a cron job to manage disk usage.
# - Creates systemd services for Watchtower and Icebox.
# - Creates the log directory for Watchtower and the cron job.
# - Creates a simple Watchtower configuration to only save motion to disk.
# - Copies the nginx app gateway config file to access Watchtower via uWSGI.
# 
# Additional setup to the watchtower_config file is needed to enable Dropbox
# uploads and microcontroller support, described in the output.

set -e

WATCHTOWER_LOG_PATH="/var/log/watchtower"
WATCHTOWER_PATH=`dirname "$(readlink -f "$0")"`
ICEBOX_PATH="$WATCHTOWER_PATH/icebox"

sudo apt update
sudo apt upgrade -y
sudo apt install -y libavutil56 libcairo-gobject2 libgtk-3-0 libpango-1.0-0 libavcodec58 libcairo2 libswscale5 libtiff5 libatk1.0-0 libavformat58 libgdk-pixbuf2.0-0 libilmbase23 libjasper1 libopenexr23 libpangocairo-1.0-0 libwebp6 libatlas-base-dev libgstreamer1.0-0 git python3 python3-pip python3-venv ufw

# Install docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh 

# Install docker-compose
sudo pip3 -v install docker-compose

# Add user to the docker group
sudo usermod -aG docker $USER
echo "Installed docker and docker-compose. Current user is now in the docker group."

# Set up ufw
echo "Creating firewall rules to allow http(s) traffic and ssh access..."
sudo ufw enable
sudo ufw allow '443'
sudo ufw allow 'ssh'

# Create user for watchtower
sudo useradd -M watchtower
# Allow the user access to /var/log
sudo usermod -aG adm watchtower
echo "Created watchtower user with uid: `id -u watchtower` gid: `id -g watchtower`"

# Add the new UID and GID to the .env file for Docker.
sed -i "s,<uid>,`id -u watchtower`, ; s,<gid>,`id -g watchtower`," "$WATCHTOWER_PATH/.env"

# Create instance folder
mkdir -p "$WATCHTOWER_PATH/instance"
echo "Created \"$WATCHTOWER_PATH/instance\""

# Create the logs directory with write permission.
sudo mkdir -p "$WATCHTOWER_LOG_PATH"
sudo chgrp adm "$WATCHTOWER_LOG_PATH"
sudo chmod 775 "$WATCHTOWER_LOG_PATH"
echo "Created $WATCHTOWER_LOG_PATH directory."

# Set up cron job to keep disk usage under control.
# CRON_JOB="*/5 * * * * $WATCHTOWER_PATH/ancillary/pi/disk_purge.sh $WATCHTOWER_PATH/instance/recordings >> $WATCHTOWER_LOG_PATH/disk_purge.log"
# CRON_JOB=`(crontab -l 2>/dev/null ; echo "$CRON_JOB")`
# echo "$CRON_JOB" | crontab
# echo "Created disk_purge cron job."


echo -e "\n\nInstallation finished! The camera is configured to record to disk at $WATCHTOWER_PATH/instance/recordings.\n\
# Final steps to take: \n\
# 1) Required: Enable camera access via 'sudo raspiconfig'\n\
# 2) Optional: Enable serial access via 'sudo raspiconfig'\n\
# 3) Optional: To use the HTTP API, upload SSL certificates to /etc/nginx/certs\n\
#              Restart nginx: 'sudo systemctl restart nginx'\n\
# 4) Optional: Only allow HTTP access from trusted sources by editing /etc/nginx/sites-available/watchtower\n\
# 5) Optional: Configure the main reverse proxy with an upstream location to this machine. See $WATCHTOWER_PATH/ancillary/nginx/reverse_proxy\n\
# 6) Optional: Configure $WATCHTOWER_PATH/instance/watchtower_config.json with Dropbox and microcontroller support."
