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
mediakit compress -t video -f /path/to/video/directory
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

限流器由三层组成:
- **`CPULimiterCoordinator`** — 调度器层，管理所有 worker 进程的限流器实例，处理手动覆盖、SIGUSR1 信号和文件覆盖
- **`ProcessThrottler`** — 每个被监控进程一个 daemon 线程，采样 CPU 使用率并通过 duty cycle controller 计算 SIGSTOP/SIGCONT 时长
- **`macos_sample_cpu_time()`** — CPU 使用率采样层，macOS 优先使用 `ps` 子进程（规避 `proc_pidinfo` ctypes struct 在 macOS 26 上的兼容性问题），回退到 `proc_pidinfo` 或 Linux `/proc/stat`

#### 方式一: 自动模式 (默认)

通过环境变量 `CPU_LIMIT` 配置（默认 `CPU_LIMIT=100`，即 100%），直接作为总预算分配给所有 worker：

| 环境变量 | 每个 worker 配额 |
|---------|----------------|
| `CPU_LIMIT=100` (默认) | 100% / worker 数量 |
| `CPU_LIMIT=50` | 50% / worker 数量 |
| `CPU_LIMIT=1` | 1% / worker 数量 (最低 1%) |

#### 方式二: CLI 参数

```sh
# -c/--cpu-limit: 设置 CPU 上限 (100 = 单核, 即 100%)
mediakit compress -t video -f /path/to/dir -c 50   # 限制为 50%
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

**注意**: 需要向主进程发送信号（即 `mediakit ...` 的进程，而不是 ffmpeg 子进程）。信号处理器通过 `signal.signal()` 注册，即使在 `subprocess.communicate()` 阻塞主线程时仍能可靠执行（Python 内部通过 self-pipe 技巧实现信号唤醒）。

#### 方式四: 文件覆盖

创建特殊文件设置临时 CPU 限制:

```sh
# 格式: /tmp/media_handler_cpu_<百分比>
touch /tmp/media_handler_cpu_25   # 设置 25% 限制
```

文件被读取后会自动删除。

#### 多 Worker 情况

当使用 `-w/--workers` 参数并行处理时，CPU 配额会平均分配给所有 worker，但每个 worker 最低不低于 1%（-c 手动模式下）或 25%（自动模式下）。

例如: `-c 100 -w 4` 时，手动模式下每个 worker 获得 25% 配额；自动模式 `CPU_LIMIT=50 -w 4` 时，每个 worker 获得 12%（不低于 25% 自动模式安全下限）。

#### 配置优先级

1. 文件覆盖 (最高优先级)
2. CLI `--cpu-limit` 参数 (手动模式)
3. 环境变量 `CPU_LIMIT`（自动模式下默认预算）
4. 自动模式（默认，使用 CPU_LIMIT 直接分配）

#### Duty Cycle 控制

当 ffmpeg 进程的 CPU 使用率超过目标值时，限流器不会立即停止进程——它会计算一个成比例的停止时间：

```
stop_time = window_duration × (actual_CPU / target - 1)
```

例如：500% 的进程目标为 25%，则 stop_time = 1.0 × (500/25 - 1) = 19 秒。这意味着进程每运行 1 秒就停止约 19 秒，有效 CPU 约为 25%。

这种方法比固定时长停止更精确，能适应不同 CPU 密集度的进程。停止时长的最小值为 0.5 秒，最大值为 30 秒。

#### macOS 兼容性说明

macOS 26（Sequoia）上 `proc_pidinfo()` 的 ctypes struct 布局与内核输出不匹配，导致采样值偏差约 42 倍。限流器优先使用 `ps` 子进程进行 CPU 采样，`proc_pidinfo` 留作回退方案。
