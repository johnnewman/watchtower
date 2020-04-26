#@IgnoreInspection BashAddShebang
#
# startup.sh
#
# John Newman
# 2018-02-10
#
# This startup file is executed as a non-root user from rc.local.
# It starts PiServoServer, switches to the Python virtual
# environment used for PiSecurityCam, and starts an instance.

source /home/pi/PiServoServer/venv/bin/activate
cd /home/pi/PiServoServer
python3 main.py &
deactivate

source /home/pi/PiSecurityCam/venv/bin/activate
cd /home/pi/PiSecurityCam
python3 pi_sec_cam.py &
deactivate
