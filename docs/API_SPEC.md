# API 规格

FastAPI 服务暴露两类端点：基于 Prompt 的生成与基于现有规格的渲染。所有响应均为 JSON，默认只生成文本与 JSON 文件；如需 MIDI 需显式设置 `emit_midi=true`。

## 全局说明
- 基础 URL：`http://127.0.0.1:8000`
- 响应字段：
  - `output_dir`：服务端生成的输出目录（相对路径）。
  - `spec`：`spec.json` 的绝对路径。
  - `summary`：`summary.txt` 的绝对路径。
  - `midi`：若未生成则为 `null`。
  - `project`：返回的 `ProjectSpec`（可用于后续再渲染）。
  - `sections`：段落摘要字典，包含 `note_count`、`chords`、`regeneration_count` 等字段。

## POST /generate
根据自然语言 Prompt 生成全新的 `ProjectSpec` 并渲染文本输出。

### 请求体
```json
{
  "prompt": "雨后城市夜景，慢中速，A-B-Bridge-A′，现代古典融合电子",
  "options": {
    "motif_style": "wavering",
    "rhythm_density": "medium",
    "harmony_level": "basic",
    "emit_midi": false
  }
}
```

- `motif_style`：可选 `ascending_arc`、`wavering`、`zigzag`。
- `rhythm_density`：可选 `low`、`medium`、`high`。
- `harmony_level`：可选 `basic`、`colorful`。
- `emit_midi`：默认 `false`。

### 示例 cURL
```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"雨后城市夜景，慢中速，A-B-Bridge-A′，现代古典融合电子", "options":{"rhythm_density":"medium","harmony_level":"basic"}}'
```

## POST /render
对客户端传入的 `ProjectSpec` 再渲染。适合在局部调整后获得新的摘要或开启 MIDI 输出。

### 请求体
```json
{
  "project": { ... ProjectSpec ... },
  "emit_midi": true
}
```

### 错误码
- `400`：输入不合法（如 JSON 结构不符合 `ProjectSpec`，或渲染时出现异常）。
- `422`：Pydantic 无法校验输入（FastAPI 默认响应）。

## 输出约定
- 服务端会在 `outputs/` 下为每次请求创建唯一子目录，如 `prompt_a1b2c3d4`。
- 若 `emit_midi=false`，`midi` 字段返回 `null`，目录中也不会生成 `.mid` 文件。
- `sections` 字典可用于局部再生操作，`regeneration_count` 会在调用 CLI `regenerate-section` 时递增。

更多实现细节参见 [docs/ARCHITECTURE.md](./ARCHITECTURE.md)。
