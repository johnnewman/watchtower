set -e

sudo apt update
sudo apt upgrade -y
sudo apt install -y libavutil56 libcairo-gobject2 libgtk-3-0 libpango-1.0-0 libavcodec58 libcairo2 libswscale5 libtiff5 libatk1.0-0 libavformat58 libgdk-pixbuf2.0-0 libilmbase23 libjasper1 libopenexr23 libpangocairo-1.0-0 libwebp6 libatlas-base-dev libgstreamer1.0-0 git python3-venv nginx

# Set up watchtower
python3 -m venv watchtower/venv
source watchtower/venv/bin/activate
pip install -r watchtower/requirements.txt
deactivate

# Set up the servo app
git clone https://github.com/johnnewman/PiServoServer.git
python3 -m venv PiServoServer/venv
source PiServoServer/venv/bin/activate
pip install -r PiServoServer/requirements.txt
deactivate

# enable serial and camera via raspi-config
# setup cron job
# upload certificates
# liblapack-dev

