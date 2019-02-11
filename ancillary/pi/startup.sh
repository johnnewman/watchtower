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

cd /home/<username>/PiServoServer
python main.py &

source /usr/local/bin/virtualenvwrapper.sh
workon cv
cd /home/<username>/PiSecurityCam
python pi_sec_cam.py &
