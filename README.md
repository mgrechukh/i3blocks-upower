config example:

[battery]
command=while :; do ~/.config/i3blocks/blocklets/upower-listen.py; done
interval=persist

Script will run persistent, restarting only if killed
