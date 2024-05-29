#!/bin/bash

# crontab -e
# */1 * * * * cd /Users/nut/Dropbox/dev/tools/media_handler && /bin/bash watcher.sh

sh watcher_.sh | /usr/sbin/rotatelogs -D -l -f logs/watcher.log.%Y-%m-%d.log 86400
