## 1. 入口文件重命名

- [x] 1.1 将 `cli` 重命名为 `cli.py`
- [x] 1.2 更新 `cli.py` docstring 中的 Usage 示例（`python cli` → `mediakit`）

## 2. pyproject.toml 配置

- [x] 2.1 在 `pyproject.toml` 中添加 `[project.scripts]` 段：`mediakit = "cli:main"`
- [x] 2.2 验证项目仍可通过 `uv run python cli.py` 正常运行

## 3. 安装为全局命令

- [x] 3.1 运行 `uv tool install --editable .` 安装 `mediakit` 到系统
- [x] 3.2 验证 `~/.local/bin/mediakit` 已创建且可通过 PATH 访问（需把 `~/.local/bin` 加到 PATH）
- [x] 3.3 验证 `mediakit --help` 或 `mediakit compress --help` 输出正确信息

## 4. 文档更新

- [x] 4.1 更新 `README.md` 中的所有调用示例（`uv run python cli` → `mediakit`）
- [x] 4.2 更新 `AGENTS.md` 中的所有 CLI 命令示例
- [x] 4.3 更新 `base/AGENTS.md`、`utils/AGENTS.md` 中的 CLI 命令示例（如适用）
- [x] 4.4 搜索项目内其他 `.md` 文件中 `python cli` 的引用，确认是否需要更新

## 5. 验证

- [x] 5.1 运行完整测试套件 `pytest -vv` 确认无回归（65 passed, 3 skipped）
- [x] 5.2 运行 `uv run python cli.py compress --help` 确认 fallback 兼容
- [x] 5.3 运行 `mediakit compress --help` 确认新入口正常工作
