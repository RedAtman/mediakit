#!/bin/bash

# crontab -e
# */1 * * * * cd /Users/nut/Dropbox/dev/tools/mediakit && /bin/bash watcher.sh
# current_directory=$(dirname "$0")
# # echo "Current file path: $current_directory"
# cd $current_directory
source .venv/bin/activate
. watcher_.sh | /usr/sbin/rotatelogs -D -l -f logs/watcher.log.%Y-%m-%d.log 86400
