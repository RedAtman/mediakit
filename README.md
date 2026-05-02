# Media Handler

Media Handler is a tool to operate on media files. It can compress  convert  and scale media files.

More features will be added in the future.

## Create virtual environment

```sh
brew install ffmpeg

uv venv .venv && source .venv/bin/activate && uv sync
```

## Usage

```sh
source .venv/bin/activate &&
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

### Dynamic CPU Throttling / CPU 动态限流

项目内置了基于 SIGSTOP/SIGCONT 信号的 CPU 动态限流器，实时监控每个 ffmpeg 进程的 CPU 使用率并动态调整。

#### 方式一: 自动模式 (默认)

根据系统负载自动调整每个 worker 的 CPU 配额:

| 系统负载 | CPU 配额 |
|---------|---------|
| 高 (>80%) | 25% 每核心 |
| 中 (50%-80%) | 50% 每核心 |
| 低 (<50%) | 100% 每核心 |

#### 方式二: CLI 参数

```sh
# -c/--cpu-limit: 设置 CPU 上限 (100 = 单核, 即 100%)
python cli compress -t video -f /path/to/dir -c 50   # 限制为 50%
```

#### 方式三: 信号切换 (SIGUSR1)

运行时动态循环切换预设配置 (无限 → 100% → 50% → 25%):

```sh
# 查找进程 PID
ps aux | grep python

# 每发送一次 SIGUSR1 就切换到下一个配置
kill -SIGUSR1 <pid>   # → 100%
kill -SIGUSR1 <pid>   # → 50%
kill -SIGUSR1 <pid>   # → 25%
kill -SIGUSR1 <pid>   # → 无限 (自动模式)
```

**设计说明**: SIGUSR1 是 Unix 信号，本身不能携带数值参数。因此无法通过 `kill -SIGUSR1 <值> <pid>` 的方式直接指定 CPU 百分比。解决方案是固定周期循环：每次收到 SIGUSR1 就跳到预设配置链中的下一个。如果需要精确指定数值，请使用方式四 (文件覆盖)。

**注意**: 需要向主进程发送信号 (同时运行多个 ffmpeg 的进程)。

#### 方式四: 文件覆盖

创建特殊文件设置临时 CPU 限制:

```sh
# 格式: /tmp/media_handler_cpu_<百分比>
touch /tmp/media_handler_cpu_25   # 设置 25% 限制
```

文件被读取后会自动删除。

#### 多 Worker 情况

当使用 `-w/--workers` 参数并行处理时，CPU 配额会平均分配给所有 worker，但每个 worker 最低不低于 25%。

例如: `-c 100 -w 4` 时，每个 worker 获得 25% 配额。

#### 配置优先级

1. 文件覆盖 (最高优先级)
2. CLI `--cpu-limit` 参数
3. 环境变量 `CPU_LIMIT`
4. 自动模式 (默认)
