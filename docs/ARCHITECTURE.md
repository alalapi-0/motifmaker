# 架构说明

Motifmaker 将音乐创作拆分为多个可控层次，使得从自然语言感受转化为可执行结构的每一步都可追踪、可调试。

## 分层概览

```
+---------------------------+
|  Prompt Parser            |
|  (自然语言 → 元数据)      |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Skeleton Builder          |
|  (骨架 JSON + 表单)        |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Motif Generator           |
|  (动机轮廓 + 节奏密度)     |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Form Expander             |
|  (结构展开 → 段落草图)     |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Harmony Engine            |
|  (和声走向 → 局部功能)     |
+-------------+-------------+
              |
              v
+-------------+-------------+
|  Renderer                  |
|  (文本摘要 / JSON / MIDI*) |
+---------------------------+
```

> 注：`*` 表示 MIDI 仅在显式开启 `--emit-midi` 时生成。

## 数据流说明

1. **Prompt Parser**：`parsing.py` 分析关键词，推断调式、速度、节奏密度、动机风格以及编制建议，并输出结构化 `meta`。
2. **Skeleton Builder**：`schema.default_from_prompt_meta` 根据 `meta` 创建 `ProjectSpec`，包含表单结构、动机配置与全局参数。
3. **Motif Generator**：`motif.generate_motif` 使用轮廓与节奏密度生成确定性动机，并输出 `Motif`。
4. **Form Expander**：`form.expand_form` 将动机映射到各段落，根据段落类型应用变奏算子（增值、转位等），形成 `SectionSketch`。
5. **Harmony Engine**：`harmony.generate_harmony` 依据调式与段落张力生成和声事件，支持 `basic` 与 `colorful` 两档复杂度。
6. **Renderer**：`render.render_project` 汇总旋律与和声，生成段落摘要、JSON 规格与可选 MIDI；`render.regenerate_section` 支持局部再生，更新对应段落的再生计数。

每一层都使用 `logging` 输出 INFO 摘要与 DEBUG 细节，可通过 CLI `--verbose/--debug` 控制，API 端亦记录关键事件。
