## Context

当前项目入口是一个无扩展名的 `cli` 文件，位于项目根目录。它没有 shebang 行，无可执行权限，不能通过 Python `import` 机制加载。调用时必须通过 `uv run python cli <action> [args]`，每次输入 4 个前缀词。

系统上 `/usr/local/bin/cli` 已被另一个 macOS 服务管理工具占用，因此不能简单地将 `cli` 放到 PATH 上。

用户需要一个全新的命令名 `mediakit`，实现零前缀调用。

## Goals / Non-Goals

**Goals:**
- 将入口点注册为 `mediakit` 系统命令
- 调用方式从 `uv run python cli compress ...` 变为 `mediakit compress ...`
- 开发期代码改动即时生效，无需每次重建
- 所有文档中的调用示例同步更新

**Non-Goals:**
- 不改变任何功能逻辑
- 不改变 `src/`、`utils/`、`base/` 等核心模块
- 不涉及 PyInstaller 等二进制打包（后续可追加，两者不冲突）

## Decisions

### Decision 1: `cli` → `cli.py` 重命名

`cli` 文件没有 `.py` 扩展名，Python 的 import 系统无法将其识别为模块。而 `[project.scripts]` 入口点需要引用一个可 import 的模块（`cli:main`），因此必须重命名。

- **备选方案 A**：新建一个包装模块（如 `src/__main__.py`），通过它引入 `cli` 内容
  - **否决**：额外引入一层间接调用，且 `cli` 文件本身仍需要处理
- **备选方案 B**：在 `cli` 中保持原名，通过自定义加载器注入
  - **否决**：过度工程化，没有必要
- **选择**：直接重命名 `cli` → `cli.py`。这是最直接的做法，且重命名后 `python cli.py` 仍然可以工作作为 fallback

### Decision 2: 使用 `uv tool install --editable` 而非 PyInstaller

`uv tool install` 是 uv 内置的全局工具安装机制：
- 创建隔离的 venv 在 `~/.local/share/uv/tools/mediakit/`
- 在 `~/.local/bin/mediakit` 生成入口 shim（Python 脚本）
- `--editable` 模式：代码修改后即时生效，无需重新安装

PyInstaller 二进制方案的问题是：
- 每次代码变更都需要 `pyinstaller --onefile` 重建（~30秒/次）
- Python 3.14 兼容性不确定
- SQLAlchemy / Pydantic / whisper 等 C extension 需要手动维护 `--hidden-import`
- 构建产物 ~30MB，每个版本都要重新打包

权衡：对于活跃开发的项目，`uv tool install --editable` 是最优选择。将来如需分发，可在 CI 中追加 PyInstaller 构建步骤。

### Decision 3: 不添加 shebang 到 cli.py

添加 shebang（`#!/usr/bin/env python3`）会让文件在直接执行时可用，但对于 uv 管理的工具安装而言不必要。`uv tool install` 生成的 shim 已经处理了解释器路径。

不过为了开发调试便利，保留 `#!/usr/bin/env python3` shebang 作为可选项——不影响功能，只影响直接 `./cli.py` 执行的行为。

## Risks / Trade-offs

- **[Breaking change] `cli` 文件消失** → 任何依赖 `python cli` 的脚本、别名、文档都会失效。所有调用示例需要同步更新到 `mediakit`
- **[反向兼容] `~/.local/bin` 不在 PATH 上** → `uv tool install` 会自动将 `~/.local/bin` 加入 shell 配置（通过修改 `.zshrc`/`.bashrc`），但用户需要重新加载 shell 或手动确认
- **[环境依赖] 需要 uv** → `mediakit` 命令依赖 uv 运行时。如果系统没有 uv，命令不可用。这对开发者环境不是问题，但对分发给终端用户时需要 PyInstaller 方案
- **[命名冲突] `/usr/local/bin/cli`** → 已经存在，使用 `mediakit` 名称彻底避免冲突

## Open Questions

- ~~需要确认是否添加 shebang 到 cli.py~~ → 保留 `#!/usr/bin/env python3` 作为可选项
