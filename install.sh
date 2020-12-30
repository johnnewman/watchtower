# install.sh
#
# John Newman
# 2020-05-23
#
# This script only needs to be run once. This will set up everything Watchtower
# needs so that you simply need to run `docker-compose build` and `docker-compose up`.
# In summary, this script:
# - Updates all system packages.
# - Configures a Firewall to only allow HTTPS and SSH traffic.
# - Installs docker and docker-compose.
# - Adds the current user to the docker group.
# - Creates a new "watchtower" user to run containers with unprivileged access.
# - Adds necessary GID and UID parameters to the .env file.
# - Downloads Icebox for cooling the system.
# - Creates the recording and log directory.
# - Schedules a cron job to manage disk usage.

set -e

WATCHTOWER_LOG_PATH="/var/log/watchtower"
WATCHTOWER_PATH=`dirname "$(readlink -f "$0")"`
ICEBOX_PATH="$WATCHTOWER_PATH/icebox"

sudo apt update
sudo apt upgrade -y
sudo apt install -y ufw

# Install docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh 
rm get-docker.sh

# Install docker-compose
sudo pip3 -v install docker-compose

# Add user to the docker group
sudo usermod -aG docker $USER
echo "Installed docker and docker-compose. Current user is now in the \"docker\" group."

# Set up ufw
echo "Creating firewall rules to allow http(s) traffic and ssh access..."
sudo ufw enable
sudo ufw allow '443'
sudo ufw allow 'ssh'

# Create user for watchtower
sudo useradd -M watchtower
echo "Created watchtower user with uid: `id -u watchtower` gid: `id -g watchtower`"

# Add the new UID and GID to the .env file for Docker.
sed -i "s,<watchtower_uid>,`id -u watchtower`, ; s,<watchtower_gid>,`id -g watchtower`," "$WATCHTOWER_PATH/.env"
# Add the video group's GID.
sed -i "s,<video_gid>,`getent group video | awk -F: '{printf "%d", $3}'`", "$WATCHTOWER_PATH/.env"
# Add the dialout (serial) group's GID.
sed -i "s,<serial_gid>,`getent group dialout | awk -F: '{printf "%d", $3}'`", "$WATCHTOWER_PATH/.env"
# Add the gpio group's GID.
sed -i "s,<gpio_gid>,`getent group gpio | awk -F: '{printf "%d", $3}'`", "$WATCHTOWER_PATH/.env"

# Set up Icebox
echo "Downloading Icebox..."
git clone https://github.com/johnnewman/icebox.git "$ICEBOX_PATH"

# Create instance and recordings folders.
mkdir -p "$WATCHTOWER_PATH/instance/recordings"
sudo chgrp video "$WATCHTOWER_PATH/instance"
sudo chmod 770 "$WATCHTOWER_PATH/instance"
sudo chgrp video "$WATCHTOWER_PATH/instance/recordings"
sudo chmod 770 "$WATCHTOWER_PATH/instance/recordings"
echo "Created \"$WATCHTOWER_PATH/instance/recordings\""

# Create the logs directory. The watchtower instance will be started using the video group.
sudo mkdir -p "$WATCHTOWER_LOG_PATH"
sudo chgrp video "$WATCHTOWER_LOG_PATH"
sudo chmod 775 "$WATCHTOWER_LOG_PATH"
echo "Created $WATCHTOWER_LOG_PATH directory."

# Set up cron job to keep disk usage under control.
CRON_JOB="*/5 * * * * $WATCHTOWER_PATH/ancillary/pi/disk_purge.sh $WATCHTOWER_PATH/instance/recordings >> $WATCHTOWER_LOG_PATH/disk_purge.log"
CRON_JOB=`(crontab -l 2>/dev/null ; echo "$CRON_JOB")`
echo "$CRON_JOB" | crontab
echo "Created disk_purge cron job."

# Put the user and working directory into the service file and install it.
sed -i".bak" "s,<user>,$USER,g ; s,<watchtower_path>,$WATCHTOWER_PATH,g" "$WATCHTOWER_PATH/ancillary/pi/watchtower.service"
sudo ln -s "$WATCHTOWER_PATH/ancillary/pi/watchtower.service" "/etc/systemd/system/"
sudo systemctl enable watchtower.service
echo "Created systemd watchtower.service file and configured it to run on boot."
echo "   NOTE: This service has not been started."

docker-compose -f "$WATCHTOWER_PATH/docker-compose.yml" --env-file "$WATCHTOWER_PATH/.env" build

echo -e "\n\nInstallation finished! Watchtower is configured to record to disk at \"$WATCHTOWER_PATH/instance/recordings\".\n\n\
Final steps to take:\n\
1) REQUIRED: Enable camera access via 'sudo raspiconfig'\n\
2) Optional: To use the HTTP API and frontend:
    2.1) Upload SSL certificates to \"$WATCHTOWER_PATH/nginx/certs\". You will need:\n\
        - A public SSL certificate.
        - The corresponding private key. These two used for encrypting traffic.
        - A certificate authority cert for validating clients. Necessary to restrict access to trusted users.
        These 3 files must match the names defined in \"$WATCHTOWER_PATH/.env\":\n\
            - 'SSL_CERT=wt.crt'\n\
            - 'SSL_CERT_KEY=wt.key'\n\
            - 'SSL_CLIENT_CERT=ca.crt'\n\
    2.2) Enter the IP address (typically the reverse proxy address) allowed to access this machine by editing 'ALLOWED_CLIENT_IP=' in \"$WATCHTOWER_PATH/.env\"\n\
3) Optional: To use a microcontroller, you will need to:\n\
    3.1) Enable serial access via 'sudo raspiconfig'\n\
    3.2) Set 'SERIAL_ENABLED=1' in \"$WATCHTOWER_PATH/.env\"\n\
    3.3) Configure servo angles in \"$WATCHTOWER_PATH/config/watchtower_config.json\"\n\
4) Optional: Configure the reverse proxy with an upstream location to this machine. See \"$WATCHTOWER_PATH/ancillary/nginx/reverse_proxy\"\n\
5) Optional: Configure \"$WATCHTOWER_PATH/config/watchtower_config.json\" with Dropbox support. See \"$WATCHTOWER_PATH/config/watchtower_config_advanced.json\" for an example.\n\n\
After making changes to watchtower_config.json or uploading certificates, rerun 'docker-compose build'.\n\n\
To start Watchtower now, run:\n    sudo systemctl start watchtower\n\
To view logs, run:\n    docker-compose logs
