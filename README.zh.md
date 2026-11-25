# MediaKit

MediaKit 是一款批量媒体处理 CLI 工具，支持压缩、格式转换、缩放、裁剪等操作。使用 ffmpeg 子进程进行处理，内置基于 SIGSTOP/SIGCONT 的 CPU 动态限流器，使用 SQLAlchemy 进行状态追踪，采用中间件-调度器模式进行 CLI 分发。

## 安装

### 前置要求

| 依赖 | 说明 |
| --- | --- |
| `ffmpeg` / `ffprobe` | **不随包分发**，必须在 `PATH` 上（`brew install ffmpeg` / `apt install ffmpeg`）。在 launchd/cron 下 `PATH` 很小，需要设 `FFMPEG_BIN_DIR=/opt/homebrew/bin` 或在环境里补 `PATH`（仓库自带的 plist 用的是后者） |
| Python 3.14 | 仅源码/uv 安装需要；`uv` 可代为安装（`uv python install 3.14`）。上界钉在 `<3.15` 是因为 pyobjc 还没有 3.15 的 wheel |
| `transcriber` CLI | 可选，只有转写动作需要（`brew install RedAtman/tap/transcriber`） |
| macOS / Linux | CPU 限流只在两者上实现；Windows 下守护进程不限流，只打一条 warning |

### 方式一：Homebrew（macOS）

```sh
brew install RedAtman/tap/mediakit ffmpeg
mediakit -v
```

### 方式二：预编译二进制（无需 Python）

每个 release 都附带 `mediakit-<os>-<arch>`（`mediakit-macos-arm64`、`mediakit-macos-x86_64`、
`mediakit-linux-x86_64`、`mediakit-windows-x86_64.exe`），下载后给执行权限并放进 `PATH`：

```sh
chmod +x mediakit-macos-arm64 && sudo mv mediakit-macos-arm64 /usr/local/bin/mediakit
```

### 方式三：uv / 源码

```sh
git clone https://github.com/RedAtman/mediakit && cd mediakit
uv sync                                          # 创建 Python 3.14 的 .venv
uv tool install --editable . --python 3.14       # 可选：把 mediakit 装到 PATH
```

## 首次运行

```sh
# 1. 生成带注释的起始配置到 ~/.config/mediakit/config.toml（已存在则拒绝覆盖）
mediakit --init-config

# 2. 告诉它要盯哪些目录 —— 两种写法任选
printf '%s\n' "~/Downloads/rs" >> ~/.config/mediakit/folders.txt
#    再由配置引用:  [watch] folders_file = "~/.config/mediakit/folders.txt"
#    或直接写条目:
#    [[watch.folders]]
#    path = "~/Downloads/rs"

# 3. 先拿一个目录试跑（一次性，不起守护进程）
mediakit compress -t video -f ~/Movies/rs

# 4. 作为守护进程运行（Ctrl-C 或另开一个终端 `mediakit stop`）
mediakit compress -t video --watch
```

仓库里提供了模板：`config.toml.example`、`folders.txt.example`。

### 状态文件位置

| 内容 | 源码 / uv 安装 | Homebrew 或预编译二进制 |
| --- | --- | --- |
| 配置 | `~/.config/mediakit/config.toml`（`$XDG_CONFIG_HOME`） | 同左 |
| 数据库 | `<仓库>/db.db`，或 `[database] path` | `~/Library/Application Support/mediakit/db.db`（macOS）、`~/.local/state/mediakit/db.db`（Linux）、`%LOCALAPPDATA%\mediakit\db.db`（Windows） |
| 日志 | `<仓库>/logs/` | 同一平台状态目录下的 `logs/` |
| 守护进程 pid | `~/.mediakit/daemon.pid` | 同左 |

冻结二进制把**状态放在平台状态目录而不是可执行文件旁边**，所以 `brew upgrade` 不会丢掉数据库；`.env`（当前目录
或 `~`）里设置 `SQLITE_DATABASE` 仍然可以覆盖它。

## 使用

```sh
mediakit compress -t video -f /path/to/video/directory
```

### 监控配置（`~/.config/mediakit/config.toml`）

监控模式的配置是一个 TOML 文件，默认位置 `~/.config/mediakit/config.toml`（遵循 `XDG_CONFIG_HOME`，
macOS 上同样使用 `~/.config`；状态目录 `logs/`、`db.db` 仍在平台状态目录，配置与状态分开）。
查找顺序：`--config` → `MEDIAKIT_CONFIG` → `~/.config/mediakit/config.toml` → `~/.config/mediakit/folders.txt` → `-f DIR`。

```toml
[watch]
cpu_limit    = 200                                # 全局；-c 优先
folders_file = "~/.config/mediakit/folders.txt"   # 仍然支持"一行一路径 + # 注释"的纯文本清单

[compress]                                        # 全局压缩缺省；--resolution/--fps 优先
fps = 24

[database]                                        # db.db 位置；环境变量 SQLITE_DATABASE 会盖过它
path = "~/Library/Application Support/mediakit/db.db"

[[watch.folders]]                                 # 逐目录覆盖（最长前缀匹配，显式条目优先）
path       = "~/Downloads/rs/jp.gv"
media_type = "video"                              # video | audio | image
recursive  = true                                 # 只对这一条
compress   = { resolution = "HD", fps = 30 }
```

先用模板生成，不要手写：

```sh
mediakit --init-config              # 写到 ~/.config/mediakit/config.toml（已存在则拒绝覆盖）
mediakit --init-config --config /path/to/config.toml
```

仓库里还有 `config.toml.example` 与 `folders.txt.example`；测试保证前者与 `--init-config` 写出的内容逐字节一致，
示例不会跟 schema 漂移。

- `[database] path` 在任何调度器之前生效，因此 `db.db` 可以放在项目之外（冻结二进制本来就放在平台状态目录）。
  注意优先级：环境变量或 `.env` 里的 `SQLITE_DATABASE` **优先于**这一行 —— 想让它生效需要先删掉那边；
  否则启动时会打一条 warning 同时列出两个路径。`mediakit dedupe` 默认也跟随同一个库，`--db` 仍可覆盖。
- 配置写错（未知键、相对路径、未知 `media_type`、`resolution="1080p"`、`fps=0`）会**直接拒绝启动**并打印一行
  `config error: …`，不会静默忽略。
- **一个目录都没有配**同样硬失败：`nothing to watch: no media folders configured`，并列出三条修复途径
  （`--init-config` / `--folder-file` / `-f`），不会再静默去盯一个相对路径。
- 运行中编辑：目录增删与 `resolution`/`fps` 热生效（清单文件自身也参与轮询）；`recursive` 变更需重启。
- `cpu_limit` 是全局的（限流协调器是单例）；`max_workers` 目前也是全局的（一次 flush 一个线程池）。

### 停止监控

优雅停止或强制停止正在运行的 watch 守护进程：

```sh
# 优雅停止（等待正在处理的媒体完成）
mediakit stop

# 强制停止（立即杀死守护进程及所有 ffmpeg 子进程）
mediakit stop --force
```

| 参数      | 说明                                 | 默认值  |
| --------- | ------------------------------------ | ------- |
| `--force` | 立即杀死所有 mediakit 和 ffmpeg 进程 | `False` |

通过 `~/.mediakit/daemon.pid` PID 文件追踪守护进程。详见 `src/schedulers/folder.py:_stop()` 和 `src/schedulers/watcher.py`。

### 媒体去重

查找 md5 相同（内容相同但文件名不同）的媒体文件，并将重复文件移入 macOS 废纸篓（可恢复，非永久删除）：

```sh
# 预演：仅列出将要删除的文件（默认）
mediakit dedupe

# 实际将重复文件移入废纸篓
mediakit dedupe --apply
```

| 参数      | 说明                                                 | 默认值  |
| --------- | ---------------------------------------------------- | ------- |
| `--apply` | 将重复文件移入废纸篓（默认仅预演）                   | `False` |
| `--db`    | 媒体数据库路径（优先保留 DB 中记录的文件作为幸存者） | `db.db` |

### 可用命令

| 命令                    | 说明                                          |
| ----------------------- | --------------------------------------------- |
| `compress`              | 压缩媒体文件（H.264/H.265，质量/大小控制）    |
| `scale`                 | 调整视频分辨率                                |
| `change_file_extension` | 批量修改文件扩展名                            |
| `convert_format`        | 转换容器格式                                  |
| `save_text`             | 提取字幕/文本轨道                             |
| `dedupe`                | 查找 md5 相同的媒体文件，将重复文件移入废纸篓 |
| `stop`                  | 停止正在运行的 watch 守护进程（优雅或强制）   |

## macOS LaunchAgent（后台守护进程）

可以通过 launchd 托管监控守护进程：注销后继续运行、崩溃后自动重启。**没有 shell 包装脚本**了 ——
launchd 直接执行入口程序，其余职责都在应用内部。

### 步骤一：先配好监控

写好 `~/.config/mediakit/config.toml`（见上文"监控配置"），并确认能正常加载：

```sh
mediakit compress -t video --watch --no-scan-existing   # 打印 "Watching N folders" 后 Ctrl-C
```

### 步骤二：按你的安装方式改 plist

`macOS/LaunchAgents/mediakit.plist` 里默认指向仓库的 venv 入口；若用 brew 安装，改成
`/opt/homebrew/bin/mediakit`。`WorkingDirectory` 保持指向拥有 `.env`、`db.db`、`logs/` 的那个目录。

### 步骤三：安装

```sh
# 1. 先清扩展属性：Dropbox/下载目录里的 plist 带 com.apple.quarantine，
#    launchd 会拒绝并只报一句 "Bootstrap failed: 5: Input/output error"（plutil -lint 却是 OK）
xattr -c macOS/LaunchAgents/mediakit.plist
cp macOS/LaunchAgents/mediakit.plist ~/Library/LaunchAgents/
xattr -c ~/Library/LaunchAgents/mediakit.plist

# 2. 载入（立即启动，且每次登录自动启动）
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mediakit.plist

# 3. 验证
launchctl print gui/$(id -u)/com.nut.mediakit | grep -E 'state|pid'
tail -3 logs/launchd.err
```

### 步骤四：停止 / 卸载

```sh
mediakit stop                                            # 优雅停止；launchd 不会再拉起
launchctl bootout gui/$(id -u)/com.nut.mediakit          # 彻底移除服务
launchctl kickstart -k gui/$(id -u)/com.nut.mediakit     # 原地重启
```

### 说明

- **单实例**：再起一个 `mediakit compress --watch` 会打印 `watch daemon already running (PID …)` 并退出；
  守卫在应用内部，不依赖 launchd 也不依赖 shell 脚本。
- **`KeepAlive = { SuccessfulExit: false }`**：崩溃会重启，`mediakit stop`（SIGTERM，退出码 0）后保持停止。
- **PATH**：launchd 不继承登录 shell 的 PATH（只有 `/usr/bin:/bin`），所以 plist 里显式设了
  `EnvironmentVariables.PATH`（Homebrew 在前）。缺了它 ffmpeg/ffprobe 找不到，每个任务都会失败。
- **日志**：launchd 的 stdout/stderr 落在 `logs/launchd.{out,err}`；真正有用的是应用自己的
  `logs/{info,warning,error}.log`（自动轮转）。

## 构建

```sh
# 静态检查 + 测试（与 CI 相同的门禁）
pre-commit run --all-files
uv run pytest -q

# sdist + wheel → dist/
uv build

# 单文件二进制（打包的唯一真源是 PyInstaller spec）
uv run --with pyinstaller==6.22.3 pyinstaller mediakit.spec --distpath dist --workpath build
```

冻结构建的几个要点：

- `mediakit.spec` 承载了静态分析看不见的部分：`utils/media_types.json`、发行版元数据（`mediakit -v` 从它读版本）、
  以及动态 import 的 logger/signal 模块。新增动态 import 必须同步写进 spec，否则二进制运行时才会炸。
- `ffmpeg` **不打包**，二进制同样调用系统 `PATH` 上的 ffmpeg，与 pip/uv 安装行为一致。
- `multiprocessing` 是被**故意排除**的：PyInstaller 的运行时钩子会拉起一个辅助进程，反过来重新进入这个 CLI，
  于是参数解析被破坏。项目本身不用多进程（`utils/executor.py` 只有线程池）。

## 发布

```sh
# 1. bump 唯一的版本源
$EDITOR pyproject.toml          # [project].version
uv lock                         # 同步 lock 里的 mediakit 版本

# 2. 提交，然后给这个提交打 tag 并推送
git commit -am "chore(release): x.y.z"
git tag vX.Y.Z && git push origin vX.Y.Z
```

随后 `.github/workflows/release.yml` 会：跑 pre-commit + 测试（tag 可以指向任何提交，所以发布必须以测试为门禁）、
校验 tag 与 `[project].version` 一致、构建 sdist+wheel、为 macOS arm64/x86_64 / Linux x86_64 / Windows 构建二进制、
把全部产物挂到 GitHub Release，并触发 Homebrew formula bump。tag 里含 `alpha`/`beta`/`rc` 会发成 prerelease。
tag 指向的提交必须能从 `main` 到达 —— 工作流也会检查这一点。

## CPU 动态限流

项目内置了基于 SIGSTOP/SIGCONT 信号的 CPU 动态限流器，实时监控每个 ffmpeg 进程的 CPU 使用率并动态调整。

限流器由三层组成：

- **`CPULimiterCoordinator`** — 调度器层：管理所有 worker 进程的限流器实例，处理手动覆盖、SIGUSR1 信号和文件覆盖
- **`ProcessThrottler`** — 每个被监控进程一个 daemon 线程：采样 CPU 使用率并通过 duty cycle controller 计算 SIGSTOP/SIGCONT 时长
- **`macos_sample_cpu_time()`** — CPU 使用率采样层：macOS 优先使用 `ps` 子进程（规避 `proc_pidinfo` ctypes struct 在 macOS 26 上的兼容性问题），回退到 `proc_pidinfo` 或 Linux `/proc/stat`

### 方式一：自动模式（默认）

通过环境变量 `CPU_LIMIT` 配置（默认 `CPU_LIMIT=100`，即 100%），直接作为总预算分配给所有 worker：

| 环境变量                | 每个 worker 配额            |
| ----------------------- | --------------------------- |
| `CPU_LIMIT=100`（默认） | 100% / worker 数量          |
| `CPU_LIMIT=50`          | 50% / worker 数量           |
| `CPU_LIMIT=1`           | 1% / worker 数量（最低 1%） |

### 方式二：CLI 参数

```sh
# -c/--cpu-limit：设置 CPU 上限（100 = 单核，即 100%）
mediakit compress -t video -f /path/to/dir -c 50   # 限制为 50%
```

### 方式三：信号切换（SIGUSR1）

运行时动态循环切换预设配置（无限 → 100% → 50% → 25%）：

```sh
# 查找进程 PID
ps aux | grep python

# 每发送一次 SIGUSR1 就切换到下一个配置
kill -SIGUSR1 <pid>   # → 100%
kill -SIGUSR1 <pid>   # → 50%
kill -SIGUSR1 <pid>   # → 25%
kill -SIGUSR1 <pid>   # → 无限（自动模式）
```

**设计说明**：SIGUSR1 是 Unix 信号，本身不能携带数值参数，因此无法通过 `kill -SIGUSR1 <值> <pid>` 直接指定 CPU 百分比。解决方案是固定周期循环：每次收到 SIGUSR1 就跳到预设配置链中的下一个。如需精确数值，请使用方式四（文件覆盖）。

**注意**：需要向主进程发送信号（即 `mediakit ...` 的进程，而不是 ffmpeg 子进程）。信号处理器通过 `signal.signal()` 注册，即使在 `subprocess.communicate()` 阻塞主线程时仍能可靠执行（Python 内部通过 self-pipe 技巧实现信号唤醒）。

### 方式四：文件覆盖

创建特殊文件设置临时 CPU 限制：

```sh
# 格式：/tmp/mediakit_cpu_<百分比>
touch /tmp/mediakit_cpu_25   # 设置 25% 限制
```

文件被读取后会自动删除。

### 多 Worker 情况

当使用 `-w/--workers` 参数并行处理时，CPU 配额会平均分配给所有 worker，但每个 worker 最低不低于 1%（`-c` 手动模式下）或 25%（自动模式下）。

例如：`-c 100 -w 4` 时，手动模式下每个 worker 获得 25% 配额；自动模式 `CPU_LIMIT=50 -w 4` 时，每个 worker 获得 12%（不低于 25% 自动模式安全下限）。

### 配置优先级

1. 文件覆盖（最高优先级）
2. CLI `--cpu-limit` 参数（手动模式）
3. 环境变量 `CPU_LIMIT`（自动模式下默认预算）
4. 自动模式（默认，使用 CPU_LIMIT 直接分配）

### Duty Cycle 控制

当 ffmpeg 进程的 CPU 使用率超过目标值时，限流器不会立即停止进程——它会计算一个成比例的停止时间：

```
stop_time = window_duration × (actual_CPU / target - 1)
```

例如：500% 的进程目标为 25%，则 `stop_time = 1.0 × (500/25 - 1) = 19` 秒。进程运行约 1 秒后停止约 19 秒，有效 CPU 约为 25%。

这种方法比固定时长停止更精确，能适应不同 CPU 密集度的进程。停止时长下限为 0.5 秒，上限为 30 秒。当目标值在停止期间发生变化时，限流器会重新计算并可能立即唤醒进程。

### macOS 兼容性说明

macOS 26（Sequoia）上 `proc_pidinfo()` 的 ctypes struct 布局与内核输出不匹配，导致采样值偏差约 42 倍。限流器优先使用 `ps` 子进程进行 CPU 采样，`proc_pidinfo` 留作回退方案。
