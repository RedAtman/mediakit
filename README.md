# Media Handler

Media Handler is a tool to operate on media files. It can compress  convert  and scale media files.

More features will be added in the future.

## Create virtual environment

```sh
brew install ffmpeg

conda create -n media_handler python=3.12 -y &&
conda activate media_handler &&
pip install -r requirements.txt
```

## Usage

```sh
conda activate media_handler &&
python cli compress -t video -f /path/to/video/directory
```


### macOS 定时服务启动

本项目支持通过 macOS 的 LaunchAgent 以定时服务方式自动运行推荐用于无人值守的批量处理

#### 步骤一: 配置虚拟环境
确保已完成依赖安装和虚拟环境配置(见上文)

#### 步骤二: 编辑 watcher.sh
`watcher.sh` 会自动激活虚拟环境并调用 watcher_.sh 进行主循环处理你可以根据需要修改 watcher_.sh 里的 ENV 变量(development/production)

#### 步骤三: 配置 LaunchAgent
已提供示例配置文件: `macOS/LaunchAgents/media_handler.plist`

主要字段说明:
- `ProgramArguments`: 指向 watcher.sh 的绝对路径
- `StartInterval`: 定时执行间隔(单位: 秒，例: 60 表示每分钟执行一次)
- `WorkingDirectory`: 工作目录(需为项目根目录)
- `StandardOutPath`/`StandardErrorPath`: 日志输出路径

#### 步骤四: 安装/卸载服务
```sh
# 安装(开机自启+定时)
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/media_handler.plist
# 卸载
launchctl bootout gui/$(id -u) macOS/LaunchAgents/media_handler.plist
```

#### 步骤五: 查看日志
日志文件位于 logs/ 目录下，如 logs/watcher.log.YYYY-MM-DD.log

#### 其他说明
- watcher.sh 会自动激活 .venv 环境并调用 watcher_.sh
- watcher_.sh 会检测脚本是否已在运行，避免重复进程
- 支持通过 crontab 或手动运行 watcher.sh 进行调试

### Dynamic CPU Throttling

An in-process dynamic CPU throttler monitors each ffmpeg process's CPU usage and sends SIGSTOP/SIGCONT to maintain target utilization:

- **Auto mode**: Adjusts per-worker budget based on system load (high→25%, moderate→50%, low→100% per core)
- **Manual override via SIGUSR1**: Cycles through profiles (unlimited → 100% → 50% → 25% per core)
  - `kill -SIGUSR1 <pid>` while a job is running
- **File override**: `touch /tmp/media_handler_cpu_<percentage>` to set a specific limit
- **Parallel workers**: Budget is evenly distributed across all workers (min 25% per worker)
