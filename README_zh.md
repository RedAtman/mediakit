# mediakit

[![CI](https://github.com/RedAtman/mediakit/actions/workflows/ci.yml/badge.svg)](https://github.com/RedAtman/mediakit/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/RedAtman/mediakit)](https://github.com/RedAtman/mediakit/releases)

[English](README.md) | 中文

对文件夹树做批量媒体处理的 CLI：压缩、缩放、转封装、反转、合成、拼接、转录、改写元数据、去重。ffmpeg 通过 subprocess 调用；每个任务的状态都记在 SQLite 里，中断的批次可以续跑；`--watch` 能把任意 action 变成常驻守护进程，文件落地就处理。

ffmpeg 的 CPU 占用由 mediakit 自己控制：它对自己启动的子进程发 `SIGSTOP`/`SIGCONT`，把子进程压在你设定的每核预算之内。

- **有状态，不是一发了之** —— 每个媒体文件一行记录，失败写 `failed (-2)` 而不是丢失
- **批次可续跑** —— 重跑同一个 action 会跳过已完成的部分
- **watch 模式** —— debounce + 文件稳定性判定，文件写完才处理，不会压缩到一半的拷贝
- **CPU 预算** —— 默认每个 worker 一个核，运行期可用 `SIGUSR1` 或标记文件调整
- **Windows / macOS / Linux 二进制** —— 发布的构建不需要装 Python

> 英文版 [README.md](README.md) 是主文档，本文件与之逐节对应；两者内容不一致时以英文版为准。

## 目录

- [依赖](#依赖)
- [安装](#安装)
- [快速开始](#快速开始)
- [命令](#命令)
- [选项](#选项)
- [watch 模式](#watch-模式)
- [停止守护进程](#停止守护进程)
- [去重](#去重)
- [状态、数据库与日志](#状态数据库与日志)
- [CPU 节流](#cpu-节流)
- [元数据与转录](#元数据与转录)
- [配置](#配置)
- [macOS LaunchAgent](#macos-launchagent)
- [疑难排查](#疑难排查)
- [开发](#开发)

## 依赖

| | |
| --- | --- |
| **ffmpeg + ffprobe** | 必需，**不打进二进制**。必须在 `PATH` 上，或放在 `FFMPEG_BIN_DIR` |
| **transcriber** | 只有 `save_text` 需要 —— `brew install RedAtman/tap/transcriber` |
| **Python 3.14** | 只有从源码安装才需要（`>=3.14,<3.15`，上限是因为 pyobjc 还没有 3.15 的 wheel） |

## 安装

### Homebrew（macOS 推荐）

```sh
brew install RedAtman/tap/mediakit
brew install ffmpeg
```

公式安装的是自包含二进制；`brew upgrade mediakit` 即可升级。

### 预编译二进制

每个 release 都为 macOS arm64/x86_64、Linux x86_64、Windows x86_64 提供 `mediakit-<os>-<arch>`：

```sh
curl -L -o mediakit https://github.com/RedAtman/mediakit/releases/latest/download/mediakit-macos-arm64
chmod +x mediakit && ./mediakit -v
```

### 从源码

```sh
git clone https://github.com/RedAtman/mediakit.git
cd mediakit
uv venv --python 3.14 && source .venv/bin/activate
uv sync
uv tool install --editable . --python 3.14    # 把 `mediakit` 装到 PATH
```

## 快速开始

```sh
# 压缩文件夹里所有视频，一次一个，限制在半个核
mediakit compress -t video -f ~/Movies/inbox -w 1 -c 50

# 同样的任务做成守护进程：来新文件就处理
mediakit compress -t video --watch -f ~/Movies/inbox

# 每个 worker 半个核，输出降到 1920x1080 / 30fps
mediakit compress -t video -f ~/Movies/inbox --resolution FHD --fps 30 -c 50
```

## 命令

```
mediakit <action> [选项]
```

| Action | 做什么 | 需要的参数 |
| --- | --- | --- |
| `compress` | x265(libx265) 重编码，`crf=22`，可选降分辨率与帧率 | `-f` |
| `scale` | 缩放到目标分辨率（默认 1920×1080） | `-f` |
| `convert_format` | 转封装/重编码到另一种容器 | `-f` |
| `change_file_extension` | 批量改扩展名（不重编码） | `-f --old_ext --ext` |
| `combine` | 一遍完成 logo 叠加 + 背景音淡入淡出 + 裁剪 | `-f`，见下方说明 |
| `reverse` | 反转视频流 | `-f` |
| `decode` | 解码为普通容器（默认 `mp4`） | `-f` |
| `delete_voice` | 去掉音轨 | `-f` |
| `save_metadata` | 把 ffmetadata 导出为 `<title>_metadata.txt` | `-f` |
| `set_metadata` | 把标题/关键词/作者写回文件 | `-f` |
| `images_to_video` | 用图片序列生成视频 | `--images-path` |
| `concat` | 通过 concat demuxer 拼接片段 | `--concat-list` |
| `save_text` | 调用外部 `transcriber` CLI 转录 | `-f`，且 `transcriber` 在 PATH |
| `dedupe` | 把内容完全相同的副本移入废纸篓（macOS） | 见 [去重](#去重) |
| `stop` | 停止正在运行的 watch 守护进程 | 见 [停止守护进程](#停止守护进程) |

`combine` 的水印路径是**硬编码的开发者机器路径**：文件不存在时 ffmpeg 直接失败。请把它当成"先配好 logo 再用"，而不是零配置可用。

作用范围说明：`change_file_extension` 作用于文件夹本身，`images_to_video` 作用于 `--images-path`（产物写在图片所在目录），`concat` 作用于列表文件并把 `concat_output.mov` 写在列表文件旁边 —— 这三个都忽略 `-f`。其余 action 处理 `-f` 下找到的媒体。

## 选项

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `-f, --folder` | `MEDIA_FILE_FOLDER`（`samples`） | 要处理的文件夹 |
| `-t, --type` | `all` | `video` / `audio` / `image`。**只在 `save_text` 和 `--watch` 生效**；其余 action 目前固定按 video 处理 |
| `-w, --max_workers` | `MAX_WORKERS`（`1`） | 并行任务数，上限为 `os.cpu_count()` |
| `-c, --cpu-limit` | `CPU_LIMIT`（`100`） | **每个 worker** 的 CPU 预算，100 = 一个核。见 [CPU 节流](#cpu-节流) |
| `--resolution` | `COMPRESS_RESOLUTION`（`HD`） | `compress` 的输出分辨率：枚举名（`HD`、`FHD`、`WQHD`、`UHD`…）或 `1920x1080`，大小写不敏感。**只缩不放** |
| `--fps` | `COMPRESS_FPS`（`24`） | `compress` 输出帧率，`>= 1` |
| `--watch` | 关 | 把该 action 跑成守护进程（见 [watch 模式](#watch-模式)） |
| `--folder-file` | 解析到的 `var/folder.sh` | 文件夹列表文件 |
| `--recursive` | 关 | 同时监听子目录 |
| `--no-scan-existing` | 关 | 跳过启动扫描，只处理之后到达的文件 |
| `--old_ext`, `--ext` | — | `change_file_extension` 的原/目标扩展名 |
| `--force` | 关 | `stop`：用 SIGKILL 杀进程组，而不是 SIGTERM |
| `--apply` | 关 | `dedupe`：真正移动副本，而不是干跑 |
| `--db` | `db.db` | `dedupe`：用于决定保留哪个副本的数据库 |
| `--concat-list` | — | `concat`：concat demuxer 列表文件（`file '...'` 行） |
| `--images-path`, `--image-format`, `--bit-rate` | —、`jpg`、`5000k` | `images_to_video` 的输入 |
| `-v, --version` | — | 打印版本（读包元数据） |
| `-d, --daemon` | `True` | 仅为兼容保留，当前未使用 |

## watch 模式

`--watch` 把 action 变成响应文件系统事件的前台守护进程：

```sh
mediakit compress -t video --watch -f ~/Movies/inbox
mediakit compress -t video --watch --folder-file var/folder.sh -w 2 -c 50
mediakit compress -t video --watch --recursive --no-scan-existing --folder-file var/folder.sh
```

文件夹列表的解析顺序：

1. 命令行给了 `--folder-file <path>`
2. 环境变量 `WATCH_FOLDER_FILE`
3. 从当前目录逐层向上找 `var/folder.sh`
4. 从工具自身所在位置逐层向上找 `var/folder.sh`（覆盖 launchd 这种 cwd 为 `/` 的场景）
5. 都没有则用 `-f` / `MEDIA_FILE_FOLDER` 作为单个文件夹

列表文件一行一个文件夹；空行和 `#` 注释忽略，路径会做 `~` 展开、规范化、去重，然后才进入调度。

### "被监听"意味着什么

每个配置的文件夹都是**独立的一份监听**：自己的文件系统流、在配置重载 diff 里自己的一条、自己的一次启动扫描。守护进程中编辑列表只会增删真正变化的那些行，无需重启；新加入的文件夹会立刻被扫描一遍已存在的文件。

`--recursive` 同时监听子目录，此时列表里被父目录覆盖的嵌套条目会被折叠——因为父目录确实覆盖子目录。**没有 `--recursive` 时父目录并不覆盖子目录**，嵌套条目各自独立，所以不要用几个祖先根替换一长串列表：那样删掉一行会停掉上百个文件夹的监听，而且会开始处理没人配置过的目录。

### 时序（可观测行为，不是调参旋钮）

| 阶段 | 值 |
| --- | --- |
| debounce 平静期 | 最后一次写入后 5 秒 |
| debounce 最大攒批 | 即使一直有写入，也 60 秒后处理 |
| 稳定性判定 | 大小 + mtime 连续 3 次采样（每秒 1 次）不变 |
| 稳定性放弃 | 30 秒 |
| 配置文件轮询 | 5 秒 |

一个文件要"安静 5 秒 + 稳定 3 秒"才被处理 —— 正在拷贝的文件不会被压成半成品，卡住的传输 30 秒后放弃。

成本，在 224 个配置文件夹上实测：227 个线程、约 2100 个 fd、约 8 MB 内存，以及全部流排完需要约 23 秒（每条约 95 ms；macOS 会串行化流的创建，无法并行）。这是"每个文件夹独立身份"的代价，不是效率问题。

### 日志与 pid 文件

守护进程启动时写 `~/.mediakit/daemon.pid`，优雅退出时删除；日志写入 `logs/` 目录（见 [状态、数据库与日志](#状态数据库与日志)）。

## 停止守护进程

```sh
mediakit stop           # SIGTERM：跑完手上的任务再退出
mediakit stop --force   # SIGKILL 整个进程组，包括 ffmpeg 子进程
```

没有在跑的守护进程时，它打印 `No running daemon found.` 并以 0 退出。

## 去重

两个文件 md5 相同，就是同一份内容的不同副本。`dedupe` 扫描监听的文件夹，保留一份（优先保留数据库里记录的那条路径，避免媒体表失效），其余移入废纸篓 —— 可恢复，不是删除。**仅 macOS**：它通过 `osascript` 调 Finder，其他平台上移动步骤什么也不做。

```sh
mediakit dedupe                                   # 干跑：会移动什么
mediakit dedupe --apply                           # 真的移入废纸篓
mediakit dedupe --apply --folder-file my-list.txt  # 默认用解析到的 var/folder.sh
mediakit dedupe --apply --db /path/to/db.db        # 保留哪一份由这个库决定
```

默认干跑是刻意的：它打印的每一行，都是即将从原目录消失的文件。

## 状态、数据库与日志

每个 action 都把每个媒体的状态记进 SQLite，所以重跑是"续跑"而不是重做：

| 值 | 含义 |
| --- | --- |
| `2` | 已完成 |
| `-1` | 未处理 / 对该 action 不适用 |
| `-2` | 失败 —— 下次运行会重试 |
| `0` … `1` | 编码中的进度比例，由 `compress` 写入 |

数据库与日志的位置：

| 安装方式 | 位置 |
| --- | --- |
| 从源码 | `config.py` 旁边（`db.db`、`logs/`） |
| Homebrew / 二进制（macOS） | `~/Library/Application Support/mediakit/` |
| Homebrew / 二进制（Windows） | `%LOCALAPPDATA%\mediakit\` |
| Homebrew / 二进制（Linux） | `~/.local/state/mediakit/` |

二进制绝不写在自己旁边：`brew upgrade` 会整个替换 Cellar 的版本目录，数据库和日志会随之消失。需要固定位置就设置 `SQLITE_DATABASE`。

日志按级别拆成 `default.log`、`info.log`、`warning.log`、`error.log`、`critical.log`，轮转份数由 `LOG_BACKUP_COUNT` 控制。`LOG_LEVEL` 接受任意大小写（`info`、`INFO`、`20`）；无法识别的值会回落到 `WARNING`，而不是让程序起不来。

## CPU 节流

ffmpeg 是 mediakit 自己启动的，所以能在进程内节流：采样子进程 CPU，再按占空比 `SIGSTOP`/`SIGCONT`。不用 `nice`，不用 `cpulimit`，而且多 worker 同时生效。

三层：

- **`CPULimiterCoordinator`** —— 每个 worker 进程一个节流器，负责分配预算、手动覆盖、`SIGUSR1` 与文件覆盖（`utils/throttle/coordinator.py`）
- **`ProcessThrottler`** —— 每个被监控进程一个守护线程：采样 CPU 并计算停止/运行的占空比（`utils/throttle/throttler.py`）
- **`macos_sample_cpu_time()`** —— 采样层：macOS 用 `ps` 子进程（规避 `proc_pidinfo` 的 ctypes 结构不匹配，该问题在 macOS 26 上会带来约 42 倍误差），Linux 用 `/proc/stat`（`utils/throttle/sampling.py`）

其他平台上协调器只记一条警告并以不节流方式运行，不会因此失败。

### 方式 1 —— 环境变量默认值

`CPU_LIMIT`（默认 `100`）是**总预算**，在 worker 间平均分配：

| `CPU_LIMIT` | `-w 4` 时每个 worker 的预算 |
| --- | --- |
| `100`（默认） | 各 25% |
| `50` | 各 12% |
| `1` | 各 1%（下限） |

### 方式 2 —— 命令行

```sh
mediakit compress -t video -f ~/Movies/inbox -c 50        # 每个 worker 50%
mediakit compress -t video -f ~/Movies/inbox -w 4 -c 100  # 各 25%
```

### 方式 3 —— 运行期信号

```sh
kill -SIGUSR1 <pid>   # 循环：不限制(auto) -> 100% -> 50% -> 25% -> 不限制
```

Unix 信号无法携带数值，所以档位是固定循环。请发给 mediakit 主进程，不要发给 ffmpeg：处理器用 `signal.signal()` 注册，即使主线程阻塞在 `subprocess.communicate()` 里也能执行。

### 方式 4 —— 标记文件（精确数值）

```sh
touch /tmp/mediakit_cpu_25   # 25%，文件被读取后自动删除
```

### 优先级

标记文件 → `-c/--cpu-limit` → `CPU_LIMIT` → 内置默认值。

### 占空比

当进程超过目标时，停止时长按比例计算而不是固定值：

```
stop_time = window_duration × (actual_cpu / target - 1)
```

一个跑在 500% 的进程、目标 25%，运行约 1 秒后停止 `1.0 × (500/25 - 1) = 19` 秒，平均下来约 25%。停止时长限制在 0.5–30 秒；停止期间目标值变化会立刻唤醒进程。代码里唯一的下限是每个 worker 1%（`MIN_PER_WORKER`），手动与自动模式都适用。

## 元数据与转录

`set_metadata` 把标题、关键词、作者写进文件。关键词会经百度翻译 API 翻译，并用 `config.py` 里的 `CAMERA`、`LENS`、`CATEGORY`、`ARTIST` 映射做补充；没有百度凭证时，走到翻译这一步会抛错，所以它需要：

```sh
BAIDU_TRANSLATE_APP_ID=...
BAIDU_TRANSLATE_SECRET_KEY=...
BAIDU_TRANSLATE_SALT=...
```

`save_text` 调用外部的 `transcriber` CLI（基于 whisper.cpp）：

```sh
brew install RedAtman/tap/transcriber
mediakit save_text -t video -f ~/Movies/inbox
```

转录由 `TRANSCRIBER_MODEL`（默认 `base`）和 `TRANSCRIBER_INITIAL_PROMPT` 配置，输出落在源文件旁边，命名为 `<title>.txt`。

## 配置

所有设置都是环境变量（会加载当前目录的 `.env`，找不到则回落到 `~/.env`）：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `MEDIA_FILE_FOLDER` | `samples` | `-f` 的默认值 |
| `MAX_WORKERS` | `1` | `-w` 的默认值 |
| `CPU_LIMIT` | `100` | CPU 总预算（见 [CPU 节流](#cpu-节流)） |
| `COMPRESS_RESOLUTION` | `HD` | `--resolution` 的默认值（1280×720） |
| `COMPRESS_FPS` | `24` | `--fps` 的默认值 |
| `SQLITE_DATABASE` | `db.db` | 数据库路径（相对状态目录） |
| `MEDIA_FILE_PATH` | `samples/zh.mp4` | 临时脚本用的样例 |
| `WATCH_FOLDER_FILE` | `var/folder.sh` | watch/dedupe 的文件夹列表 |
| `FFMPEG_BIN_DIR` | `""`（用 `PATH`） | 存放 `ffmpeg`/`ffprobe` 的目录 |
| `LOG_LEVEL` | logger 为 `WARNING`，ffmpeg `-loglevel` 为 `DEBUG` | 详细程度，任意大小写（`info`、`INFO`、`20`） |
| `LOG_BACKUP_COUNT` | `5` | 日志轮转份数 |
| `ENV` | — | `development` 切换到相对路径/彩色日志格式 |
| `TRANSCRIBER_MODEL` / `TRANSCRIBER_INITIAL_PROMPT` | `base` / 内置提示词 | 转录 |
| `BAIDU_TRANSLATE_*` | — | 关键词翻译 |

## macOS LaunchAgent

要无人值守运行，就把 watcher 装成 LaunchAgent。示例 plist 在 `macOS/LaunchAgents/mediakit.plist`。

```sh
# 1. 确认 venv 和 ffmpeg 已就位（见"安装"）
# 2. 把 ProgramArguments 指向 watcher.sh 的绝对路径
# 3. 加载
launchctl bootstrap gui/$(id -u) macOS/LaunchAgents/mediakit.plist

# 停止并卸载
launchctl bootout gui/$(id -u) macOS/LaunchAgents/mediakit.plist
```

`watcher.sh` 会激活 `.venv` 并转交 `watcher_.sh`；在后者里改 `ENV` 可在 `development`/`production` 之间切换。`watcher_.sh` 拒绝重复启动，残留进程不会被再起一份。plist 关键字段：`ProgramArguments`、`WorkingDirectory`（项目根目录）、`StandardOutPath` / `StandardErrorPath`，定时运行则用 `StartInterval`。

## 疑难排查

| 症状 | 原因 / 处理 |
| --- | --- |
| `ffmpeg: command not found` / 退出码 127 | ffmpeg 不打进二进制 —— `brew install ffmpeg`，或设置 `FFMPEG_BIN_DIR` |
| `transcriber CLI not found` | `brew install RedAtman/tap/transcriber`，或不用 `save_text` |
| 启动时打印 `Folder path does not exist, skipping: ...` | 列表里有失效条目；它们会被跳过，但清理掉能加快启动 |
| `mediakit trim` 被拒绝 | `trim` 还没有 CLI（它需要时间区间）；用库 API `Folder.trim` |
| watch 守护进程刚启动像没在工作 | 几百个文件夹时每条要排约 95 ms（224 条约 23 秒），排完才全部生效 |
| `brew upgrade` 之后数据库或日志不见了 | 它们在平台状态目录里；用 `SQLITE_DATABASE` 固定位置 |
| 完全没有节流 | 节流只实现了 macOS 与 Linux；其他平台记一条警告后不节流 |

退出码：`0` 成功，`1` action 失败，`2` 参数错误（argparse）。

## 开发

```sh
uv sync
uv run pytest -q                                   # 全量测试
uv run ruff check --select F401,F841,I . && uv run ruff format --check .
pre-commit run --all-files                         # 与 CI 完全一致
```

测试、lint/format 门禁和四平台二进制都在每次 push 与 PR 上跑 CI —— 当前状态看上面的徽章，本文件不写死数字。

代码走向：`cli.py`（入口）→ `utils/cli.py`（参数解析）→ `src/schedulers/folder.py`（每个 action 一个 scheduler）→ `base/`（按媒体类型分的 ffmpeg 封装）→ `utils/`（共享：command、db、throttle、progress）。架构、不变量与反模式详见 `AGENTS.md`。

发版流程：改 `pyproject.toml` 的 `[project].version`，打 `v<version>` 标签；`.github/workflows/release.yml` 会重跑测试、校验标签与版本一致，然后发布 wheel、四个平台二进制和 Homebrew 公式。

## 许可

MIT —— 见 [LICENSE](LICENSE)。
