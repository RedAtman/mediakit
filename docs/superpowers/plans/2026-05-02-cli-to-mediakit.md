# CLI to mediakit 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目入口从无扩展名的 `cli` 文件迁移为通过 `uv tool install` 注册的 `mediakit` 系统命令，调用方式从 `uv run python cli <action> [args]` 简化为 `mediakit <action> [args]`。

**Architecture:** 纯入口层变更，不涉及核心逻辑。核心动作：
1. `cli` → `cli.py` 重命名（Python import 系统需要 `.py` 扩展名才能被 `[project.scripts]` 入口点引用）
2. `pyproject.toml` 添加 `[project.scripts]` 段注册 `mediakit = "cli:main"`
3. `uv tool install --editable .` 将 `mediakit` 安装为系统级全局命令
4. 所有文档（README.md, AGENTS.md, cli.py docstring）中的调用示例同步更新

**Tech Stack:** Python 3.12+, uv, pyproject.toml entry points

---

### Task 1: 重命名 cli → cli.py 并更新 docstring

**Files:**
- Rename: `cli` → `cli.py`
- Modify: `cli.py`（更新 docstring）
- Test: 运行验证

- [ ] **Step 1: 使用 git mv 重命名文件**

```bash
git mv cli cli.py
```

Expected: 文件重命名，git 跟踪历史。

- [ ] **Step 2: 更新 cli.py 的 docstring**

将文件顶部 docstring 中的调用示例从 `python cli` 更新为 `mediakit`：

```python
"""
Usage:
    mediakit compress -t video -w 1 -f /path/to/folder
    mediakit change_file_extension --old_ext avi --ext mp4 -f /path/to/folder
    mediakit change_file_extension --old_ext mp4 --ext avi
    mediakit convert_format -t video -f /path/to/folder

Also available via direct python invocation:
    python cli.py compress -t video -w 1 -f /path/to/folder
"""
```

- [ ] **Step 3: 验证 cli.py 可正常运行**

```bash
uv run python cli.py --help
```

Expected: 显示 argparse 帮助信息，action 列表（compress, scale, etc.）。

- [ ] **Step 4: 验证 test 套件仍通过**

```bash
pytest -vv --rootdir . --color=yes --capture=tee-sys
```

Expected: 65 passed, 3 skipped（或类似的已有结果，无新增失败）。

- [ ] **Step 5: Commit**

```bash
git add cli.py
git rm cli  # git mv 的后续清理，或者 git mv 已完成
git commit -m "refactor: rename cli to cli.py for module importability"
```

---

### Task 2: 添加 shebang 到 cli.py（可选但推荐）

**Files:**
- Modify: `cli.py`（添加第一行）

- [ ] **Step 1: 在 cli.py 第一行添加 shebang**

```python
#!/usr/bin/env python3
"""
Usage:
...
```

直接在现有文件的开头插入 `#!/usr/bin/env python3`，不改变 docstring 格式。

- [ ] **Step 2: 验证直接执行**

```bash
chmod +x cli.py
./cli.py --help
```

Expected: 显示帮助信息。注意：shebang 用于开发调试便利，`uv tool install` 生成的 shim 不依赖 shebang。

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "chore: add shebang to cli.py for direct execution"
```

---

### Task 3: pyproject.toml 注册 mediakit 入口点

**Files:**
- Modify: `pyproject.toml`（在 `[project]` 段中添加 `[project.scripts]`）

- [ ] **Step 1: 在 pyproject.toml 的 `[project]` 段末尾添加 scripts 注册**

```toml
[project.scripts]
mediakit = "cli:main"
```

插入位置：在 `[project]` 段的最后一个属性（license）之后，`[project.optional-dependencies]` 之前。即插入在现有第 223 行（`license = { text = "MIT" }`）之后，`[project.optional-dependencies]` 之前：

```toml
license = { text = "MIT" }
dependencies = [
    ...
]
[project.scripts]
mediakit = "cli:main"
```

注意格式：`mediakit` 是命令名，`cli:main` 指向 `cli.py` 中的 `main()` 函数。Python 的 entry point 机制需要模块路径（`cli`，因为文件叫 `cli.py`）加上冒号和函数名。

实际编辑：

```
- [project.optional-dependencies]
+ [project.scripts]
+ mediakit = "cli:main"
+
+ [project.optional-dependencies]
```

- [ ] **Step 2: 验证配置语法**

```bash
uv run python -c "import sys; print(sys.version)"
```

Expected: Python 版本信息，无错误。进一步的验证在 Task 4 安装后进行。

- [ ] **Step 3: 验证 Python 可导入 cli 模块**

```bash
uv run python -c "from cli import main; print(main)"
```

Expected: `<function main at 0x...>`，无 ImportError。

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: register mediakit CLI entry point in pyproject.toml"
```

---

### Task 4: uv tool install 安装 mediakit 全局命令

**Files:**
- System: `~/.local/share/uv/tools/mediakit/`（由 uv 创建）
- System: `~/.local/bin/mediakit`（由 uv 创建）

- [ ] **Step 1: 运行 uv tool install --editable**

```bash
uv tool install --editable .
```

Expected 输出类似：
```
Resolved 42 packages in 300ms
Installed 1 package: mediakit v0.1.0 (editable)
Installed 1 executable: mediakit
```

`--editable` 模式让 `mediakit` 命令指向项目源码目录，修改代码后即时生效。

- [ ] **Step 2: 验证 shim 已创建**

检查 shim 文件和路径：

```bash
ls -la ~/.local/bin/mediakit
file ~/.local/bin/mediakit
```

Expected: 文件存在，类型是 Python 脚本（不是二进制）。

同时检查 uv tools 目录：

```bash
ls ~/.local/share/uv/tools/mediakit/
```

Expected: 显示 lib/、pyvenv.cfg 等目录结构。

- [ ] **Step 3: 验证 ~/.local/bin 在 PATH 中**

```bash
which mediakit || echo "NOT IN PATH"
```

如果 `~/.local/bin` 不在 PATH 中，uv 会尝试自动添加。如果没有自动添加，手动添加：

```bash
# 检查 shell 配置
echo $PATH
# 如果 ~/.local/bin 不在其中：
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

- [ ] **Step 4: 验证 mediakit 命令可用**

```bash
mediakit --help
```

Expected: 显示 argparse 帮助信息，等价于 `uv run python cli.py --help` 的输出。

- [ ] **Step 5: Commit（配置变更）**

无需 git 操作，`uv tool install` 修改的是系统路径，不在项目内。

---

### Task 5: 更新 README.md 文档

**Files:**
- Modify: `README.md`（3 处调用示例）

- [ ] **Step 1: 更新第 19 行 compress 示例**

原文：
```
python cli compress -t video -f /path/to/video/directory
```

改为：
```
mediakit compress -t video -f /path/to/video/directory
```

- [ ] **Step 2: 更新第 81 行 compress 带 -c 示例**

原文：
```
python cli compress -t video -f /path/to/dir -c 50   # 限制为 50%
```

改为：
```
mediakit compress -t video -f /path/to/dir -c 50   # 限制为 50%
```

- [ ] **Step 3: 更新第 101 行 SIGUSR1 说明中的引用**

原文：
```
**注意**: 需要向主进程发送信号（即 `python cli ...` 的进程，而不是 ffmpeg 子进程）。
```

改为：
```
**注意**: 需要向主进程发送信号（即 `mediakit ...` 的进程，而不是 ffmpeg 子进程）。
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update CLI invocation examples in README.md"
```

---

### Task 6: 更新 AGENTS.md 文档

**Files:**
- Modify: `AGENTS.md`（2 处）

- [ ] **Step 1: 更新第 90 行 compress 示例**

原文：
```
python cli compress -t video -w 1 -f /path/to/folder
```

改为：
```
mediakit compress -t video -w 1 -f /path/to/folder
```

- [ ] **Step 2: 更新第 93 行 compress 带 -c 示例**

原文：
```
python cli compress -t video -w 1 -c 50 -f /path/to/folder
```

改为：
```
mediakit compress -t video -w 1 -c 50 -f /path/to/folder
```

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update CLI invocation examples in AGENTS.md"
```

---

### Task 7: 最终验证

**Files:**
- 无代码修改，仅运行验证命令

- [ ] **Step 1: 运行完整测试套件确认无回归**

```bash
pytest -vv --rootdir . --color=yes --capture=tee-sys
```

Expected: 65 passed, 3 skipped（或与历史一致的测试结果）。重点确认无新增失败。

- [ ] **Step 2: 验证 mediakit 各子命令可用**

```bash
mediakit --help
mediakit compress --help
mediakit scale --help
mediakit change_file_extension --help
mediakit convert_format --help
mediakit save_text --help
```

Expected: 每个命令都能正确显示 argparse 帮助信息。

- [ ] **Step 3: 验证 fallback 兼容**

```bash
# 通过 uv run python cli.py 调用（旧风格的 fallback）
uv run python cli.py --help
uv run python cli.py compress --help
```

Expected: 输出等价于 `mediakit`。

- [ ] **Step 4: 验证修改代码后即时生效（editable 模式）**

```bash
# 先在 cli.py 的 main() 中添加一行临时 print
# 编辑 cli.py，在 main() 开头添加 print("LIVE EDIT TEST")
```

```python
def main():
    print("LIVE EDIT TEST")
    from src.schedulers import folder
    ...
```

```bash
# 直接调用 mediakit，不重新安装
mediakit --help
```

Expected: 输出中应包含 `LIVE EDIT TEST` 字样。

```bash
# 恢复临时修改
git checkout cli.py
```

- [ ] **Step 5: 最后确认 mediakit 在任意目录下可用**

```bash
cd /tmp
mediakit --help
```

Expected: 显示帮助信息，而不是 "command not found" 或 module import error。

---

### Task 8: 更新 OpenSpec tasks.md 为完成状态

**Files:**
- Modify: `openspec/changes/cli-to-mediakit/tasks.md`

- [ ] **Step 1: 将所有任务标记为已完成**

将 `tasks.md` 中的所有 `- [ ]` 改为 `- [x]`：

```markdown
## 1. 入口文件重命名

- [x] 1.1 将 `cli` 重命名为 `cli.py`
- [x] 1.2 更新 `cli.py` docstring 中的 Usage 示例（`python cli` → `mediakit`）

## 2. pyproject.toml 配置

- [x] 2.1 在 `pyproject.toml` 中添加 `[project.scripts]` 段：`mediakit = "cli:main"`
- [x] 2.2 验证项目仍可通过 `uv run python cli.py` 正常运行

## 3. 安装为全局命令

- [x] 3.1 运行 `uv tool install --editable .` 安装 `mediakit` 到系统
- [x] 3.2 验证 `~/.local/bin/mediakit` 已创建且可通过 PATH 访问
- [x] 3.3 验证 `mediakit --help` 或 `mediakit compress --help` 输出正确信息

## 4. 文档更新

- [x] 4.1 更新 `README.md` 中的所有调用示例（`uv run python cli` → `mediakit`）
- [x] 4.2 更新 `AGENTS.md` 中的所有 CLI 命令示例
- [x] 4.3 更新 `base/AGENTS.md`、`utils/AGENTS.md` 中的 CLI 命令示例（如适用）
- [x] 4.4 搜索项目内其他 `.md` 文件中 `python cli` 的引用，确认是否需要更新

## 5. 验证

- [x] 5.1 运行完整测试套件 `pytest -vv` 确认无回归
- [x] 5.2 运行 `uv run python cli.py compress --help` 确认 fallback 兼容
- [x] 5.3 运行 `mediakit compress --help` 确认新入口正常工作
```

- [ ] **Step 2: Commit**

```bash
git add openspec/changes/cli-to-mediakit/tasks.md
git commit -m "chore: mark cli-to-mediakit tasks complete"
```

---

### 自检清单

- **Spec 覆盖**：
  - "mediakit 命令可用" → Task 4（uv tool install）+ Task 7（验证）
  - "调用方式简化" → Task 1（重命名）+ Task 3（entry point）
  - "开发期间修改即时生效" → Task 4 Step 1（`--editable`）+ Task 7 Step 4（验证）
  - "uv tool install 管理" → Task 4（安装/更新/卸载流程通过 uv 管理）
  - "pyproject.toml 入口点注册" → Task 3（`[project.scripts]`）
  - "反向兼容" → Task 7 Step 3（`python cli.py` fallback）
  - "docstring 更新" → Task 1 Step 2

- **占位符检查**：无 TODO、无 TBD、无"后续补充"。每个步骤都有完整的命令和预期输出。

- **类型/签名一致性**：所有步骤引用的函数名（`main`）、文件名（`cli.py`）、模块名（`cli:main`）保持一致。

- **完整命令链**：
  - 安装：`uv tool install --editable .`
  - 新入口：`mediakit compress -t video -f /path`
  - Fallback：`uv run python cli.py compress -t video -f /path`
