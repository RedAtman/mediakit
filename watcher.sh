#!/bin/bash

# crontab -e
# */10 * * * * /bin/bash ~/Dropbox/dev/tools/media_handler/watcher.sh >> ~/Dropbox/dev/tools/media_handler/log/watcher.log 2>&1

# Check ffmpeg is running
if pgrep -x "ffmpeg" > /dev/null
then
    echo $(date +"%Y-%m-%d %H:%M:%S:") "ffmpeg is running"
    exit 1
fi
if pgrep -x "ffprobe" > /dev/null
then
    echo $(date +"%Y-%m-%d %H:%M:%S:") "ffprobe is running"
    exit 1
fi

cd ~/Dropbox/dev/tools/media_handler

# ENV="production"
# ENV="development"
CONFIG_FILE="var/folder.sh"
CONDA_ENV="media_handler"
# PYTHON=$(which python)"
PYTHON="/opt/homebrew/Caskroom/miniconda/base/envs/media_handler/bin/python"

# # Find the path to the conda executable
# CONDA_PATH=$(which conda)
# # Remove the 'bin/conda' part from the end of the path
# BASE_PATH=${$CONDA_PATH%condabin/conda}
# # echo "Conda base path: $BASE_PATH"
# # Activate the conda environment
# PROFILE_PATH=${BASE_PATH}etc/profile.d/conda.sh
# # echo "Conda profile path: $PROFILE_PATH"
# source $PROFILE_PATH
# conda activate $CONDA_ENV

# ENV_PATH=$(conda env list | grep $CONDA_ENV | awk '{print $3}')
# echo "Conda environment path: $ENV_PATH"

# Which python
echo "Use python interpreter: $PYTHON"


function excute_command() {
    echo "Executing command: $1"
    # eval $PYTHON cli compress -t video -f $1 >> log/watcher.log 2>&1
    eval $PYTHON cli compress -t video -f \"$1\"
    return $?  # Return the exit status of the last command
    # eval $1
    # return 1
}

# Read every line from a text file
# while IFS= read -r line
while read -u 10 line; do
    # echo "$line"

    # Skip empty lines
    if [[ -z "$line" ]]; then
        continue
    fi

    # Skip comments
    # if [[ $line == "#"* ]]; then
    if [[ $line == \#* ]]; then
        continue
    fi

    excute_command "$line"
done 10<$CONFIG_FILE
