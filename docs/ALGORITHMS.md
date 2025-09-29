# 算法概览

本文件对 Motifmaker 中的关键算法进行说明，涵盖动机轮廓、节奏模板、和声走向以及常见变奏算子。

## 动机轮廓生成
- **ascending_arc**：以主音为起点，逐渐上行至属音，再缓慢回落，营造“上行回落”的弧线。
- **wavering**：在主音附近做小幅往复，强调“波浪感”或细腻的摆动。
- **zigzag**：在大二度与大三度间快速交替，制造锯齿状张力。

伪代码：
```
scale = major if mode == "major" else minor
steps = contour_template(style)
for index, step in enumerate(steps):
    pitch = root_pitch + scale[clamp(step)]
    duration = rhythm_cycle[index % len(rhythm_cycle)]
    append(MotifNote(pitch, duration))
```

## 节奏模板
| 密度 | 模板 (beats) | 特性 |
| ---- | ------------- | ---- |
| low | 1.0, 1.0, 2.0 | 长音支撑，适合“克制”
| medium | 0.75, 1.25, 1.0, 1.0 | 均衡的律动，适配大多数提示
| high | 0.5, 0.5, 0.5, 0.5, 1.0 | 密集短音，突出紧张感

别名 `sparse`、`syncopated`、`dense` 被保留以兼容旧版接口。

## 和声走向
- **basic**：以 I-IV-V-I（或 i-iv-V-i）为基础，每四拍切换一次。
- **colorful**：在上述框架上加入七和弦与小调借用音；属和弦添加降九度，iv 和弦加入六度音。

伪代码：
```
progression = major or minor template
for block in blocks_of_four_beats(section):
    degree = decode(progression[index])
    chord = triad(root_pitch, mode, degree)
    if colorful:
        chord = add_extensions(chord, label)
    emit HarmonyEvent(start, duration=4, chord, bass=chord[0]-12)
```

## 变奏算子
- **增值 (Augmentation)**：`_stretch_motif` 按比例放大节奏。
- **缩值 (Diminution)**：通过 `factor < 1` 的 stretch 或 `section_beats // motif_beats` 控制重复。
- **倒影 (Inversion)**：当前版本保留接口，未来可在 `_motif_variant` 中扩展。
- **转位 (Transposition)**：`_transpose_motif` 将 B 段提升全音增强张力。
- **序列 (Sequence)**：`expand_form` 根据段落长度重复动机，形成序列结构。
- **延长尾音**：`_tail_extend` 在 A' 尾部追加 0.5 拍，模拟再现段缓和。

## 再生计数
`render.regenerate_section` 会在段落摘要中记录 `regeneration_count`，初始值为 0，每次局部再生递增，方便比对差异。
