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
sed -i "s,<s_uid>,`id -u watchtower`, ; s,<s_gid>,`id -g watchtower`," "$WATCHTOWER_PATH/.env"
# Add the video group's GID to the .env file.
sed -i "s,<v_gid>,`getent group video | awk -F: '{printf "%d", $3}'`", "$WATCHTOWER_PATH/.env"

# Create instance and recordings folders.
mkdir -p "$WATCHTOWER_PATH/instance/recordings"
sudo chgrp video "$WATCHTOWER_PATH/instance"
sudo chmod 775 "$WATCHTOWER_PATH/instance"
sudo chgrp video "$WATCHTOWER_PATH/instance/recordings"
sudo chmod 775 "$WATCHTOWER_PATH/instance/recordings"
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

echo -e "\n\nInstallation finished! The camera is configured to record to disk at \"$WATCHTOWER_PATH/instance/recordings\".\n\n\
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
5) Optional: Configure \"$WATCHTOWER_PATH/config/watchtower_config.json\" with Dropbox support."
