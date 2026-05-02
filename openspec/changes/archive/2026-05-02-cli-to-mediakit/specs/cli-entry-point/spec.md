## ADDED Requirements

### Requirement: mediakit 命令可用
系统 SHALL 提供一个名为 `mediakit` 的命令，无需任何前缀即可从终端直接调用。

#### Scenario: 从终端直接调用 mediakit
- **WHEN** 用户在终端输入 `mediakit`
- **THEN** 系统 SHALL 输出 CLI 帮助信息（等价于当前 `python cli` 的行为）

#### Scenario: 从任意目录调用
- **WHEN** 用户在非项目目录下输入 `mediakit compress -t video -f /path/to/folder`
- **THEN** 系统 SHALL 正常执行 compress 操作

### Requirement: 调用方式简化
`uv run python cli <action> [args]` SHALL 简化为 `mediakit <action> [args]`。

#### Scenario: 替换 compress 调用
- **WHEN** 用户输入 `mediakit compress -t video -w 1 -c 50 -f /path/to/folder`
- **THEN** 系统 SHALL 执行 compress 操作，效果等价于 `uv run python cli compress -t video -w 1 -c 50 -f /path/to/folder`

#### Scenario: 替换其他 action
- **WHEN** 用户输入 `mediakit scale -t video -f /path/to/folder`
- **THEN** 系统 SHALL 执行 scale 操作，效果等价于 `uv run python cli scale -t video -f /path/to/folder`

### Requirement: 开发期间代码修改即时生效
`mediakit` 命令 SHALL 在 `--editable` 模式下安装，使得对 `cli.py` 或其他项目代码的修改立即反映在下一次调用中，无需重新安装或构建。

#### Scenario: 修改后立即生效
- **WHEN** 开发者修改 `cli.py` 或其他源代码文件
- **THEN** 下一次调用 `mediakit` 时 SHALL 自动使用最新代码

### Requirement: uv tool install 管理
`mediakit` SHALL 通过 `uv tool install --editable .` 安装和管理。

#### Scenario: 安装
- **WHEN** 运行 `uv tool install --editable .`
- **THEN** 系统 SHALL 创建 `~/.local/share/uv/tools/mediakit/` 和 `~/.local/bin/mediakit` shim

#### Scenario: 更新
- **WHEN** 代码变更后运行 `uv tool install --editable .`
- **THEN** 系统 SHALL 更新 `~/.local/share/uv/tools/mediakit/` 中的代码

#### Scenario: 卸载
- **WHEN** 运行 `uv tool uninstall mediakit`
- **THEN** 系统 SHALL 删除 `~/.local/bin/mediakit` shim 和 tools 目录

### Requirement: pyproject.toml 入口点注册
`pyproject.toml` SHALL 包含 `[project.scripts]` 段以注册 `mediakit` 入口点。

#### Scenario: entry point 定义生效
- **WHEN** 检查 `pyproject.toml` 中的 `[project.scripts]`
- **THEN** SHALL 包含 `mediakit = "cli:main"`

### Requirement: 反向兼容
重命名后 `cli.py` 文件 SHALL 保持可通过 `python cli.py` 直接调用作为 fallback。

#### Scenario: 直接调用 cli.py
- **WHEN** 用户输入 `python cli.py compress -t video -f /path`
- **THEN** 系统 SHALL 正常执行 compress 操作

### Requirement: docstring 更新
`cli.py` 的文档字符串 SHALL 反映新的调用方式。

#### Scenario: 帮助信息准确
- **WHEN** 用户阅读 `cli.py` 开头的 Usage 注释
- **THEN** SHALL 显示 `mediakit compress ...` 而非 `python cli compress ...`
