# install.sh
#
# John Newman
# 2020-05-23
#
# This script only needs to be run once. This will set up everything Watchtower
# needs so that you simply need to run `docker-compose build` and `docker-compose up`.
# In summary, this script:
# - Configures a Firewall to only allow HTTPS and SSH traffic.
# - Installs docker/docker-compose and builds the docker containers.
# - Creates a new "watchtower" user to run containers with unprivileged access.
# - Adds necessary GID and UID parameters to the .env file.
# - Downloads Icebox for cooling the system.
# - Schedules a cron job to manage disk usage.


set -e

WATCHTOWER_LOG_PATH="/var/log/watchtower"
WATCHTOWER_PATH=`dirname "$(readlink -f "$0")"`
ICEBOX_PATH="$WATCHTOWER_PATH/icebox"

sudo apt update
sudo apt upgrade -y
sudo apt install -y ufw python3-pip

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

echo -e "\n\nInstallation finished! Watchtower is configured to record to disk at \"$WATCHTOWER_PATH/instance/recordings\". Final steps to take:

REQUIRED:
1) In a new shell session, run:
    docker-compose -f $WATCHTOWER_PATH/docker-compose.yml --env-file $WATCHTOWER_PATH/.env build
2) Enable camera access via 'sudo raspiconfig'
3) Restart

OPTIONAL:
4) To use the HTTP API and frontend:
    4.1) Upload SSL certificates to \"$WATCHTOWER_PATH/nginx/certs\". You will need:
            a) A public SSL certificate.
            b) The corresponding private key. These two are used for encrypting traffic.
            c) A certificate authority cert for validating clients. Necessary to restrict access to trusted users.
         These 3 files must match the names defined in \"$WATCHTOWER_PATH/.env\":
            a) 'SSL_CERT=wt.crt'
            b) 'SSL_CERT_KEY=wt.key'
            c) 'SSL_CLIENT_CERT=ca.crt'
    4.2) Enter the IP address (typically the reverse proxy address) allowed to access this machine in \"$WATCHTOWER_PATH/.env\":
            'ALLOWED_CLIENT_IP=x.x.x.x'
5) To use a microcontroller, you will need to:
    5.1) Enable serial access via 'sudo raspiconfig'
    5.2) Set 'SERIAL_ENABLED=1' in \"$WATCHTOWER_PATH/.env\"
    5.3) Configure servo angles in \"$WATCHTOWER_PATH/config/watchtower_config.json\"
6) Configure the reverse proxy with an upstream location to this machine. See \"$WATCHTOWER_PATH/ancillary/nginx/reverse_proxy\"
7) Configure \"$WATCHTOWER_PATH/config/watchtower_config.json\" with Dropbox support. See watchtower_config_advanced.json for an example.

Once running, to view logs from all containers, run:
    docker-compose logs
"