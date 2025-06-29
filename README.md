# Media Handler

Media Handler is a tool to operate on media files. It can compress, convert, and scale media files.

More features will be added in the future.

## Create virtual environment

```sh
brew install ffmpeg
brew install cpulimit

conda create -n media_handler python=3.11.5 -y &&
conda activate media_handler &&
pip install -r requirements.txt
```

## Usage

```sh
conda activate media_handler &&
python cli compress -t video -f /path/to/video/directory
```

### Timed execution

** macOS **

```sh
launchctl load macOS/LaunchAgents/media_handler.plist
launchctl unload macOS/LaunchAgents/media_handler.plist
```
