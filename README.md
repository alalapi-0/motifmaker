# Motifmaker

Motifmaker 是一个面向实验创作的分层式音乐生成原型，通过“感觉 → 骨架 → 动机 → 结构 → 和声 → 渲染”的流程，将自然语言 Prompt 转化为可追踪的音乐草图。系统默认仅生成 JSON 与文本摘要，确保在研究与测试阶段不会产生 MIDI 或音频等二进制文件（除非显式要求）。

## 架构总览

```
感受 Prompt ──► Prompt Parser ──► 骨架 JSON ──► Motif Engine ──► Form Expander ──► Harmony Engine ──► Renderer
      (parsing.py)        (schema.py)        (motif.py)          (form.py)           (harmony.py)          (render.py)
```

ASCII 图中的每一层均对应 `src/motifmaker/` 下的模块，详细说明请参阅 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。数据沿箭头依次流动：解析自然语言、构造 `ProjectSpec`、生成动机、展开段落、匹配和声，最后输出文本摘要与 JSON 规格（MIDI 需显式开启）。

## 功能特性
- **动机风格模板**：支持 `ascending_arc`、`wavering`、`zigzag` 三种轮廓，可通过 CLI/API 选择或由 Prompt 自动推断。
- **节奏密度控制**：`low`、`medium`、`high` 三档密度，覆盖克制、均衡与紧张场景。
- **和声复杂度档位**：`basic` 提供基础三和弦，`colorful` 引入七和弦与小调借用音。
- **局部再生**：`motifmaker regenerate-section` 可在不动原始 Prompt 的情况下重算指定段落，并记录再生次数。
- **日志开关**：CLI 提供 `--verbose` 与 `--debug`，API 端自动记录 INFO 级别事件，便于调试。

## 安装与环境
1. 克隆仓库并创建虚拟环境：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```
2. 安装预提交钩子：`pre-commit install`
3. 推荐命令：
   ```bash
   black --check .
   isort --check-only .
   mypy src
   pytest -q
   ```

## 快速开始
### 使用 CLI 生成文本草图
```bash
motifmaker init-from-prompt "城市夜景、温暖而克制、B 段最高张力、现代古典+电子" \
  --out outputs/demo_text_only --no-emit-midi
cat outputs/demo_text_only/spec.json
cat outputs/demo_text_only/summary.txt
```
输出目录中仅包含 `spec.json` 与 `summary.txt`，未生成任何 `.mid` 文件。

### 局部再生
```bash
motifmaker regenerate-section --spec outputs/demo_text_only/spec.json \
  --section B --out outputs/demo_text_only
cat outputs/demo_text_only/summary.txt
```
再生后的段落会更新 `regeneration_count` 字段，其他段保持不变。

### 启动 API 并调用
```bash
uvicorn motifmaker.api:app --reload
```
在另一终端使用：
```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"雨后城市夜景，慢中速，A-B-Bridge-A′，现代古典融合电子","options":{"rhythm_density":"medium","harmony_level":"basic"}}'
```
响应返回输出目录与段落摘要，`midi` 字段默认为 `null`。

## 参数说明
### CLI (`motifmaker init-from-prompt`)
| 参数 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `prompt` | 必填 | 自然语言描述 |
| `--out` | 必填 | 输出目录，自动创建 |
| `--motif-style` | 自动推断 | `ascending_arc` / `wavering` / `zigzag` |
| `--rhythm-density` | 自动推断 | `low` / `medium` / `high` |
| `--harmony-level` | 自动推断 | `basic` / `colorful` |
| `--emit-midi/--no-emit-midi` | `--no-emit-midi` | 是否写出 MIDI |
| `--verbose` | 关闭 | INFO 日志 |
| `--debug` | 关闭 | DEBUG 日志 |

`motifmaker render` 与 `motifmaker regenerate-section` 共享 `--emit-midi` 及日志选项，详见 `motifmaker --help`。

### API 选项
- `GenerationOptions.motif_style`：同 CLI。
- `GenerationOptions.rhythm_density`：同 CLI。
- `GenerationOptions.harmony_level`：同 CLI。
- `GenerationOptions.emit_midi`：默认 `false`。
- `/render` 端点可设置 `emit_midi` 来覆写已有规格。

## 开发指南
- 代码结构参见 `src/motifmaker/`，主要模块与职责：
  - `parsing.py`：Prompt 解析与关键字映射。
  - `schema.py`：`ProjectSpec` 定义与默认构造。
  - `motif.py`：动机生成、节奏模板。
  - `form.py`：曲式展开与变奏算子。
  - `harmony.py`：和声进程与复杂度切换。
  - `render.py`：文本摘要、再生计数与可选 MIDI。
  - `cli.py` / `api.py`：对外接口与日志配置。
- 新增动机或和声算子时：
  1. 在对应模块实现并添加详尽 docstring 与日志。
  2. 更新 [docs/ALGORITHMS.md](docs/ALGORITHMS.md) 记录规则与伪代码。
  3. 编写单元测试与必要的端到端测试。
- 日志建议使用 `logging.getLogger(__name__)`，INFO 描述阶段摘要，DEBUG 输出细节。

## 故障排查
| 问题 | 可能原因 | 解决方案 |
| ---- | -------- | -------- |
| 安装 `pretty_midi` 失败 | 缺少编译工具或依赖 | 使用 `pip install -r requirements-dev.txt`，必要时安装 `libfluidsynth`/`libasound2-dev` |
| 运行 CLI 生成了 `.mid` | 未显式关闭 | 使用 `--no-emit-midi`（默认值），或删除已生成文件后重试 |
| mypy 报错 | 缺少类型注解或 TypedDict | 检查新增函数，确保返回类型与字典键定义清晰 |
| pytest 找不到模块 | `src` 未在路径上 | `tests/conftest.py` 已加入路径，如新增包请补充 `__init__.py` |
| Windows / macOS 行结束差异 | Git 配置不一致 | 仓库提供 `.editorconfig` 与 `.gitattributes`，请保持 LF 行尾 |

## 路线图
- 扩展曲式模板（Rondo、Through-Composed 等）。
- 引入风格迁移与语义解析模型，提升 Prompt 理解力。
- 加强再生机制，支持段落级参数微调与自动差分。
- 探索与 DAW 的桥接方案，提供实时导出能力。

## 许可证与致谢
- 许可证：MIT（见 [LICENSE](LICENSE)）。
- 致谢：感谢 pretty_midi、music21、mido 等开源项目提供的基础设施。

## 验证步骤
在提交前可使用以下命令快速验证，本列表同样用于持续集成检查：
```bash
# 1) 安装依赖
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -r requirements-dev.txt
pre-commit install

# 2) 代码质量检查
black --check .
isort --check-only .
mypy src

# 3) 运行测试
pytest -q

# 4) 从自然语言 Prompt 生成：只产生 JSON 与文本日志
motifmaker init-from-prompt "城市夜景、温暖而克制、B 段最高张力、现代古典+电子" --out outputs/demo_text_only

# 5) 局部再生：只更新 JSON 与文本描述
motifmaker regenerate-section --spec outputs/demo_text_only/spec.json --section B --out outputs/demo_text_only

# 6) 启动 API 并使用 cURL
uvicorn motifmaker.api:app --reload
# 另一个终端：
curl -s -X POST http://127.0.0.1:8000/generate -H "Content-Type: application/json" \
  -d '{"prompt":"雨后城市夜景，慢中速，A-B-Bridge-A′，现代古典融合电子","options":{"rhythm_density":"medium","harmony_level":"basic"}}'
```
若任何命令产生二进制文件，请检查是否误启用 `--emit-midi` 或手动删除相关文件后再次执行。
