# 测试指南

Motifmaker 的测试策略遵循“单元 → 组件 → 端到端”的金字塔结构。所有测试均应在文本与 JSON 范畴内完成，不得生成二进制文件。

## 测试层级
1. **单元测试**：验证动机生成、节奏密度映射、和声复杂度等核心函数，文件位于 `tests/`（如 `test_motif.py`、`test_harmony_levels.py`）。
2. **组件测试**：使用 CLI 或 API 作为入口，确认参数解析、错误处理与日志行为，典型示例为 `test_cli_args.py` 与 `test_regenerate_section.py`。
3. **端到端测试**：`test_end_to_end.py` 从自然语言 prompt 贯通整个流程，断言生成的 `spec.json` 与 `summary.txt` 可用，且不会产出 MIDI。

## 运行命令
```bash
pytest -q
```
可配合质量检查：
```bash
black --check .
isort --check-only .
mypy src
```

## 新增算子测试流程
1. 在对应模块编写函数级单元测试（如新增节奏算子，需覆盖节奏模式与边界情况）。
2. 更新 `docs/ALGORITHMS.md` 描述算法逻辑。
3. 若算法会影响端到端结果，请扩展 `test_end_to_end.py` 或添加新的集成测试。

## 端到端检查“无二进制输出”
- 所有测试使用 `tmp_path` 或 Typer 的隔离文件系统，确保输出目录为空。
- 调用 `render_project(..., emit_midi=False)` 或 CLI `--no-emit-midi`，以防误写 `.mid` 文件。
- 测试应断言目录下不存在 `.mid`、`.wav` 等文件，如需验证渲染结果请读取 JSON 或文本摘要。

## 常见问题
- **pretty_midi 缺失头文件**：确保按照 `requirements-dev.txt` 安装依赖，必要时重新编译 `mido`/`pretty_midi`。
- **mypy 报错**：确认新增函数带有完整类型注解与返回类型；使用 `TypedDict` 或 `Protocol` 明确结构。
- **pytest 找不到模块**：`tests/conftest.py` 已将 `src/` 加入 `sys.path`，若新增子包请保证 `__init__.py` 存在。

更多细节参见 [CONTRIBUTING.md](../CONTRIBUTING.md)。
