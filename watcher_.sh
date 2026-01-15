#!/bin/bash
# */1 * * * * cd ~/Dropbox/dev/tools/media_handler && /bin/bash watcher_.sh | /usr/sbin/rotatelogs -D -l -f logs/watcher.log.%Y-%m-%d 86400 >> ./logs/watcher_.log 2>&1
# /Users/nut/Dropbox/dev/tools/media_handler/watcher_.sh | /usr/sbin/rotatelogs -D -l -f /Users/nut/Dropbox/dev/tools/media_handler/logs/watcher.log.%Y-%m-%d 86400

export ENV="development"
export ENV="production"
echo $(date +"%Y-%m-%d %H:%M:%S:") "ENV: $ENV"
current_directory=$(dirname "$0")
echo "Current file path: $current_directory"
which pip
cd $current_directory
source .venv/bin/activate
function run_context() {
    # Check if the script is already running
    local name=$1
    # echo "Checking if $name is running"
    if pgrep -f "$name" > /dev/null
    then
        echo $(date +"%Y-%m-%d %H:%M:%S:") "ENV: $ENV": "$name is running" "PYTHON: $PYTHON"
        exit 1
    fi
}
current_file_name=$(basename $0)
run_context $current_file_name

CONFIG_FILE="var/folder.sh"
# CONDA_ENV="media_handler"
# PYTHON=$(which python)"
PYTHON=".venv/bin/python"
# eval $PYTHON cli compress -t video -f "./samples/zh.mp4"

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
# echo "Use python interpreter: $PYTHON"


function execute_command() {
    run_context "ffmpeg"
    run_context "ffprobe"
    echo "Executing command: $PYTHON $1"
    # echo "Executing command: $(date +"%Y-%m-%d %H:%M:%S:") $1"
    # eval $PYTHON cli compress -t video -f $1 >> log/watcher.log 2>&1
    eval $PYTHON cli compress -t video -w 1 -f \"$1\"
    # result=$?
    # echo "Result: $result"
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

    execute_command "$line"
done 10<$CONFIG_FILE
