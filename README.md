# Motifmaker

## 项目简介
Motifmaker 是一个最小可运行的分层式音乐生成原型。系统接收自然语言 Prompt，经过解析后逐层生成骨架 JSON、动机、曲式旋律草图与和声占位，并最终导出分轨 MIDI。本仓库提供命令行工具与 FastAPI 服务，便于实验不同风格与场景的音乐草图。

## 架构说明
整体流程如下：
1. Prompt 解析：`parsing.parse_natural_prompt` 将自然语言转换为内部参数。
2. 骨架构建：`schema.default_from_prompt_meta` 根据参数生成 `ProjectSpec`。
3. 动机生成：`motif.generate_motif` 产生核心动机及 MIDI 表示。
4. 曲式展开：`form.expand_form`（内部函数）基于曲式模板输出旋律草图。
5. 和声填充：`harmony.generate_harmony` 为每个段落提供和声与低音。
6. 渲染输出：`render.render_project` 合成分轨并写出 MIDI 与 JSON。

## 安装步骤
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 快速开始
### 使用 CLI
```bash
motifmaker init-from-prompt "温暖的城市夜景，带一点电子质感" --out outputs/demo_cli
```
生成后的骨架 JSON 位于 `outputs/demo_cli/spec.json`，MIDI 文件位于 `outputs/demo_cli/track.mid`。

### 使用 API
先启动服务：
```bash
uvicorn motifmaker.api:app --reload
```
使用 `curl` 调用：
```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "温暖的城市夜景，带一点电子质感"}'
```
响应中包含输出目录与文件信息。

## 示例 Prompt 与输出
示例 Prompt：
> 城市夜景、温暖而克制、B 段最高张力、现代古典加电子、钢琴弦乐合成与轻刷打击、约 2 分钟

解析后的骨架 JSON 可通过 CLI 生成：
```bash
motifmaker init-from-prompt "$(cat examples/prompt_city_night.txt)" --out outputs/demo_city_night
cat outputs/demo_city_night/spec.json
```

## 目录结构
```
.
├── src/motifmaker       # 核心包
├── tests                # 单元测试
├── examples             # 示例 Prompt 与脚本
├── outputs              # 默认输出目录
└── .github/workflows    # CI 配置
```

## 开发命令
```bash
pre-commit install
pytest
black src tests
isort src tests
mypy src
```

## 示例脚本说明
`examples/generate_from_example.sh` 将 `prompt_city_night.txt` 的内容传给 CLI 并生成 `outputs/demo_city_night`。在 Windows PowerShell 中可使用 `Get-Content examples/prompt_city_night.txt | %{ $_ }` 的方式拼接字符串，再调用 `motifmaker init-from-prompt`。

## 后续路线图与 TODO
- 丰富 Prompt 解析映射，支持更多调性与节奏变化
- 引入旋律与和声的概率模型或深度学习模块
- 增加人机交互界面与可视化
- 为 MIDI 导出添加音色配置与混响参数
