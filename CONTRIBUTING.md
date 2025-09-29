# Contributing Guide

感谢关注 Motifmaker。本项目致力于探索“感觉 → 骨架 → 动机 → 结构 → 和声 → 渲染”的分层音乐生成流程。为保持代码质量与一致性，请在贡献前阅读以下指南。

## 开发环境
1. 克隆仓库并创建虚拟环境：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```
2. 安装预提交钩子：
   ```bash
   pre-commit install
   ```
3. 推荐使用支持 `.editorconfig` 的编辑器以保持缩进与换行风格一致。

## 代码风格
- **Black**：使用 `black` 进行代码格式化。
- **isort**：统一管理 import 顺序。
- **mypy**：所有 Python 代码需通过静态类型检查。请确保函数、类、模块具有完整类型注解。
- **Docstring**：采用 Google 或 NumPy 风格，解释用途、参数、返回值及注意事项。
- **Logging**：关键阶段使用 `logging` 输出 INFO 摘要，细节采用 DEBUG 等级，避免在库代码中使用 `print`。

## 分支策略
- `main` 为稳定分支。
- 新功能请从 `main` 派生功能分支（如 `feature/motif-templates`）。
- 修复缺陷可使用 `fix/` 前缀。
- 合并前请保持分支与 `main` 同步并解决冲突。

## 提交信息
- 使用 [Conventional Commits](https://www.conventionalcommits.org/) 简要格式：
  - `feat: 添加新的动机风格模板`
  - `fix: 修复节奏密度取值错误`
  - `docs: 更新 API 文档`

## 运行测试与质量检查
在提交前请运行：
```bash
black --check .
isort --check-only .
mypy src
pytest -q
```

## 启动本地 API 与 CLI
- CLI：
  ```bash
  motifmaker init-from-prompt "城市夜景、温暖而克制" --out outputs/demo --no-emit-midi
  ```
- FastAPI：
  ```bash
  uvicorn motifmaker.api:app --reload
  ```
  使用 `curl` 调用：
  ```bash
  curl -s -X POST http://127.0.0.1:8000/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt":"温暖克制的城市夜景"}'
  ```

## 新增算法模块
- 在 `src/motifmaker/` 下按功能划分模块（如 `motif.py`、`harmony.py`）。
- 为新算子（如节奏或和声变换）编写详尽 docstring，阐述输入输出与伪代码。
- 添加 INFO/DEBUG 级日志描述关键步骤。

## 测试策略
- 单元测试：位于 `tests/`，使用 `pytest`。
- 为新增算法提供针对性的单元测试和一个端到端测试。
- 测试执行过程中不得生成二进制文件（MIDI、音频、图片等）。如需测试渲染，请断言文本输出或 JSON 结构。

## 提交 PR
- 请在 PR 描述中概述变更、测试情况及影响面。
- 如涉及文档更新，请同步修改 README 与 `docs/` 目录。

欢迎通过 Issue 与 PR 参与交流，共建更具可控性的音乐生成工具。
