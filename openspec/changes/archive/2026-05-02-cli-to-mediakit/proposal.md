## Why

`uv run python cli <action> [args]` 是当前项目入口的标准调用方式。每次输入 4 个前缀词（`uv run python cli`）才能执行一个操作，既繁琐又容易打错，降低了 CLI 工具的日常使用体验。需要简化为一个干净的 `mediakit <action> [args]` 形式，让工具像系统原生命令一样可用。

## What Changes

- 将项目入口从无扩展名的 `cli` 文件重构为可导入的 `cli.py` 模块
- 在 `pyproject.toml` 中通过 `[project.scripts]` 注册 `mediakit` 入口点
- 使用 `uv tool install --editable .` 将 `mediakit` 安装为系统级命令
- 调用方式从 `uv run python cli compress ...` 简化为 `mediakit compress ...`
- 更新所有文档中的调用示例

## Capabilities

### New Capabilities
- `cli-entry-point`: 将 CLI 入口从 `cli` 文件转为 Python 包注册的 `mediakit` 命令，支持通过 `uv tool install` 托管安装

### Modified Capabilities

无。这是纯调用接口变更，不涉及功能层面的 spec 变更。

## Impact

- **cli 文件**：重命名为 `cli.py`，添加 shebang，更新 docstring
- **pyproject.toml**：添加 `[project.scripts]` 段
- **文档**：`README.md`、`AGENTS.md`、`cli` 文件内 docstring 中的所有调用示例需从 `uv run python cli` 更新为 `mediakit`
- **系统 PATH**：`~/.local/bin/mediakit` 将作为全局命令可用（由 `uv tool install` 管理）
- **反向兼容**：`uv run python cli` 不再工作（`cli` 文件不再存在）。`cli.py` 可通过 `uv run python cli.py` 调用，但建议迁移到 `mediakit`
