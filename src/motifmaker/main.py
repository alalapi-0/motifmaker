"""交互式主程序入口。

该模块提供一个统一的主菜单，启动时先询问用户使用控制台调试模式
还是直接运行现有的 FastAPI + Web UI。控制台模式覆盖 CLI 与 Web 所有
核心能力：从 Prompt 构建工程、查看与编辑规格、生成动机/曲式/和声
分析、局部再生、渲染与保存。每一步操作都会输出详细的反馈信息，
便于调试与定位问题。

运行方式：

* ``python -m motifmaker.main``
* 进入 UI 模式时，会在当前进程启动 Uvicorn，按 ``Ctrl+C`` 退出。
* 控制台模式提供菜单引导，可随时返回上层或退出程序。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import uvicorn

from .config import settings
from .form import SectionSketch, expand_form
from .harmony import HarmonyEvent, generate_harmony
from .motif import Motif, MotifSpec, generate_motif
from .parsing import parse_natural_prompt
from .render import RenderResult, regenerate_section, render_project
from .schema import FormSection, ProjectSpec, default_from_prompt_meta
from .utils import configure_logging, ensure_directory


@dataclass
class GenerationDetails:
    """汇总一次生成过程中关键的中间结果，供调试输出使用。"""

    motifs: Dict[str, Motif]
    sketches: List[SectionSketch]
    harmony: Dict[str, List[HarmonyEvent]]


_ROOT_PITCH_MAP: Dict[str, int] = {
    "C": 60,
    "G": 67,
    "D": 62,
    "A": 69,
    "E": 64,
    "F": 65,
    "Bb": 70,
}


def _prompt(text: str, *, allow_empty: bool = False) -> str:
    """读取用户输入，必要时循环直到给出有效值。"""

    while True:
        value = input(text).strip()
        if value or allow_empty:
            return value
        print("输入不能为空，请重新输入。")


def _prompt_int(
    text: str,
    *,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
    allow_empty: bool = False,
) -> Optional[int]:
    """读取整数输入，并按照给定区间校验。"""

    while True:
        raw = input(text).strip()
        if not raw and allow_empty:
            return None
        try:
            value = int(raw)
        except ValueError:
            print("请输入合法的整数。")
            continue
        if minimum is not None and value < minimum:
            print(f"取值需大于等于 {minimum}。")
            continue
        if maximum is not None and value > maximum:
            print(f"取值需小于等于 {maximum}。")
            continue
        return value


def _prompt_bool(text: str, *, allow_empty: bool = False) -> Optional[bool]:
    """解析是/否输入，支持空值保留原值。"""

    mapping = {"y": True, "yes": True, "n": False, "no": False}
    while True:
        raw = input(text).strip().lower()
        if not raw and allow_empty:
            return None
        if raw in mapping:
            return mapping[raw]
        print("请输入 y/yes 或 n/no。")


def _prompt_menu(title: str, options: Sequence[str]) -> int:
    """打印菜单并返回用户选择的编号（从 1 开始）。"""

    print(f"\n{title}")
    print("-" * len(title))
    for idx, label in enumerate(options, start=1):
        print(f"{idx}. {label}")
    while True:
        choice = input("请选择操作编号：").strip()
        if not choice.isdigit():
            print("请输入数字编号。")
            continue
        index = int(choice)
        if 1 <= index <= len(options):
            return index
        print("超出选项范围，请重新输入。")


def _motif_params_from_spec(
    spec: ProjectSpec, motif_spec: Dict[str, object]
) -> MotifSpec:
    """根据项目与单个动机设置拼装 :class:`MotifSpec`。"""

    return {
        "contour": motif_spec.get("contour", spec.motif_style),
        "motif_style": motif_spec.get("motif_style", spec.motif_style),
        "rhythm_density": motif_spec.get("rhythm_density", spec.rhythm_density),
        "mode": spec.mode,
        "root_pitch": _ROOT_PITCH_MAP.get(spec.key, 60),
    }


def collect_generation_details(spec: ProjectSpec) -> GenerationDetails:
    """执行一次完整的动机 → 曲式 → 和声生成，返回中间结果。"""

    motifs: Dict[str, Motif] = {}
    for label, motif_spec in spec.motif_specs.items():
        params = _motif_params_from_spec(spec, motif_spec)
        motif = generate_motif(params)
        motifs[label] = motif

    sketches = expand_form(spec, motifs)
    harmony = generate_harmony(
        spec,
        sketches,
        use_secondary_dominant=spec.use_secondary_dominant,
        use_borrowed_chords=spec.use_borrowed_chords,
    )
    return GenerationDetails(motifs=motifs, sketches=sketches, harmony=harmony)


class ConsoleDebugger:
    """封装控制台调试流程，确保每一步都有详细反馈。"""

    def __init__(self) -> None:
        self.spec: ProjectSpec | None = None
        self.last_render: RenderResult | None = None

    # ------------------------------------------------------------------
    # 公共流程
    # ------------------------------------------------------------------
    def run(self) -> None:
        """进入主循环，根据当前状态展示不同菜单。"""

        print("\n欢迎进入 MotifMaker 调试控制台。随时输入 Ctrl+C 退出。")
        running = True
        while running:
            try:
                if self.spec is None:
                    running = self._entry_menu()
                else:
                    self._project_menu()
            except KeyboardInterrupt:
                print("\n检测到中断信号，已返回主菜单。")
                self.spec = None
                self.last_render = None
                running = False

    # ------------------------------------------------------------------
    # 起始菜单
    # ------------------------------------------------------------------
    def _entry_menu(self) -> bool:
        choice = _prompt_menu(
            "主菜单",
            (
                "从 Prompt 创建新工程",
                "从 JSON 文件加载工程",
                "退出控制台",
            ),
        )
        if choice == 1:
            self._create_from_prompt()
        elif choice == 2:
            self._load_from_json()
        else:
            print("已退出控制台模式。")
            return False
        return True

    # ------------------------------------------------------------------
    # 工程菜单
    # ------------------------------------------------------------------
    def _project_menu(self) -> None:
        assert self.spec is not None  # for type checker
        choice = _prompt_menu(
            "工程调试菜单",
            (
                "查看规格概览",
                "运行生成步骤并查看详细反馈",
                "调整全局参数",
                "编辑曲式段落",
                "局部再生成段落",
                "渲染工程并导出",
                "保存规格到 JSON",
                "返回主菜单",
            ),
        )
        actions = {
            1: self._display_summary,
            2: self._inspect_generation_pipeline,
            3: self._edit_global_settings,
            4: self._edit_form_section,
            5: self._regenerate_section,
            6: self._render_project,
            7: self._save_to_json,
            8: self._reset,
        }
        handler = actions.get(choice)
        if handler:
            handler()

    # ------------------------------------------------------------------
    # 起始操作实现
    # ------------------------------------------------------------------
    def _create_from_prompt(self) -> None:
        prompt = _prompt("请输入自然语言 Prompt：")
        meta = parse_natural_prompt(prompt)
        print("\nPrompt 解析结果：")
        for key, value in meta.items():
            print(f"  - {key}: {value}")

        overrides: Dict[str, object] = {}
        motif_style = _prompt(
            "是否指定动机风格(ascending_arc/wavering/zigzag等)？留空保持自动：",
            allow_empty=True,
        )
        if motif_style:
            overrides["motif_style"] = motif_style
            overrides["primary_contour"] = motif_style

        rhythm_density = _prompt(
            "是否指定节奏密度(low/medium/high)？留空保持自动：",
            allow_empty=True,
        )
        if rhythm_density:
            overrides["rhythm_density"] = rhythm_density
            overrides["primary_rhythm"] = rhythm_density

        harmony_level = _prompt(
            "是否指定和声复杂度(basic/colorful)？留空保持自动：",
            allow_empty=True,
        )
        if harmony_level:
            overrides["harmony_level"] = harmony_level

        meta.update(overrides)
        spec = default_from_prompt_meta(meta)
        print("\n成功构造 ProjectSpec，关键字段如下：")
        self._print_spec_brief(spec)
        self.spec = spec
        self.last_render = None

    def _load_from_json(self) -> None:
        path_str = _prompt("请输入 JSON 文件路径：")
        path = Path(path_str).expanduser()
        try:
            content = path.read_text(encoding="utf-8")
            spec = ProjectSpec.model_validate_json(content)
        except Exception as exc:  # pragma: no cover - 具体错误由 pydantic 抛出
            print(f"读取或解析失败：{exc}")
            return
        print(f"成功加载 {path}，工程信息如下：")
        self._print_spec_brief(spec)
        self.spec = spec
        self.last_render = None

    # ------------------------------------------------------------------
    # 工程操作实现
    # ------------------------------------------------------------------
    def _display_summary(self) -> None:
        assert self.spec is not None
        print("\n当前工程规格概览：")
        self._print_spec_brief(self.spec)
        self._print_section_details(self.spec.form)
        if self.last_render:
            print("\n最近一次渲染结果：")
            self._print_render_summary(self.last_render)

    def _inspect_generation_pipeline(self) -> None:
        assert self.spec is not None
        print("\n正在执行完整生成流程……")
        details = collect_generation_details(self.spec)
        print("\n步骤 1：动机生成")
        for label, motif in details.motifs.items():
            total = motif.total_beats
            print(
                f"  - 动机 {label}: 音符数 {len(motif.notes)}，总时值 {total:.2f} 拍"
            )
        print("\n步骤 2：曲式展开")
        for sketch in details.sketches:
            beats = sum(note.duration_beats for note in sketch.notes)
            print(
                f"  - 段落 {sketch.name}: 音符数 {len(sketch.notes)}，累计 {beats:.2f} 拍"
            )
        print("\n步骤 3：和声推导")
        for name, events in details.harmony.items():
            chords = ", ".join(event.chord_name for event in events[:5])
            more = "…" if len(events) > 5 else ""
            print(f"  - {name}: 生成 {len(events)} 个和声事件，预览 {chords}{more}")
        print("\n生成流程完成，可在曲式或参数调整后重新运行以对比差异。")

    def _edit_global_settings(self) -> None:
        assert self.spec is not None
        spec = self.spec
        print("\n请输入新的全局参数（留空则保留当前取值）：")
        tempo = _prompt_int(
            f"  速度 BPM [{spec.tempo_bpm}]: ",
            minimum=40,
            maximum=220,
            allow_empty=True,
        )
        meter = _prompt(
            f"  拍号 [{spec.meter}] (只允许 4/4 或 3/4): ", allow_empty=True
        )
        key = _prompt(f"  调性 [{spec.key}]: ", allow_empty=True)
        mode = _prompt(f"  大小调 [{spec.mode}] (major/minor): ", allow_empty=True)
        style = _prompt(f"  风格标签 [{spec.style}]: ", allow_empty=True)
        rhythm = _prompt(
            f"  节奏密度 [{spec.rhythm_density}] (low/medium/high): ",
            allow_empty=True,
        )
        motif_style = _prompt(
            f"  动机风格 [{spec.motif_style}]: ", allow_empty=True
        )
        harmony_level = _prompt(
            f"  和声复杂度 [{spec.harmony_level}] (basic/colorful): ",
            allow_empty=True,
        )
        instruments = _prompt(
            "  配器列表（以逗号分隔，留空保持不变）：",
            allow_empty=True,
        )
        sec_dom = _prompt_bool(
            f"  启用二级属? (当前 {'是' if spec.use_secondary_dominant else '否'}) y/n 或回车跳过：",
            allow_empty=True,
        )
        borrowed = _prompt_bool(
            f"  启用借用和弦? (当前 {'是' if spec.use_borrowed_chords else '否'}) y/n 或回车跳过：",
            allow_empty=True,
        )
        humanize = _prompt_bool(
            f"  启用人性化渲染? (当前 {'是' if spec.humanization else '否'}) y/n 或回车跳过：",
            allow_empty=True,
        )

        updates: Dict[str, object] = {}
        if tempo is not None:
            updates["tempo_bpm"] = tempo
        if meter:
            updates["meter"] = meter
        if key:
            updates["key"] = key
        if mode:
            updates["mode"] = mode
        if style:
            updates["style"] = style
        if rhythm:
            updates["rhythm_density"] = rhythm
        if motif_style:
            updates["motif_style"] = motif_style
        if harmony_level:
            updates["harmony_level"] = harmony_level
        if instruments:
            updates["instrumentation"] = [
                item.strip() for item in instruments.split(",") if item.strip()
            ]
        if sec_dom is not None:
            updates["use_secondary_dominant"] = sec_dom
        if borrowed is not None:
            updates["use_borrowed_chords"] = borrowed
        if humanize is not None:
            updates["humanization"] = humanize

        if not updates:
            print("未检测到任何修改。")
            return
        try:
            self.spec = spec.model_copy(update=updates)
        except Exception as exc:  # pragma: no cover - 具体错误由模型抛出
            print(f"参数更新失败：{exc}")
            return
        print("参数已更新，最新概览如下：")
        self._print_spec_brief(self.spec)

    def _edit_form_section(self) -> None:
        assert self.spec is not None
        spec = self.spec
        self._print_section_details(spec.form)
        index = _prompt_int(
            "\n请输入要编辑的段落序号（从 1 开始）：",
            minimum=1,
            maximum=len(spec.form),
        )
        assert index is not None
        section = spec.form[index - 1]
        print(f"正在编辑段落 {section.section}。留空表示维持原值。")
        new_label = _prompt(
            f"  段落名称 [{section.section}]: ", allow_empty=True
        )
        new_bars = _prompt_int(
            f"  小节数 [{section.bars}]: ", minimum=1, maximum=128, allow_empty=True
        )
        new_tension = _prompt_int(
            f"  张力 [{section.tension} 0-100]: ",
            minimum=0,
            maximum=100,
            allow_empty=True,
        )
        new_motif = _prompt(
            f"  动机标签 [{section.motif_label}] (现有: {', '.join(spec.motif_specs)}): ",
            allow_empty=True,
        )
        updates: Dict[str, object] = {}
        if new_label:
            updates["section"] = new_label
        if new_bars is not None:
            updates["bars"] = new_bars
        if new_tension is not None:
            updates["tension"] = new_tension
        if new_motif:
            if new_motif not in spec.motif_specs:
                print("动机标签不存在，已忽略修改。")
            else:
                updates["motif_label"] = new_motif
        if not updates:
            print("段落未发生变化。")
            return
        form = list(spec.form)
        try:
            form[index - 1] = section.model_copy(update=updates)
            self.spec = spec.model_copy(update={"form": form})
        except Exception as exc:  # pragma: no cover - 具体错误由模型抛出
            print(f"段落更新失败：{exc}")
            return
        print("段落已更新，新的曲式概览如下：")
        self._print_section_details(self.spec.form)

    def _regenerate_section(self) -> None:
        assert self.spec is not None
        spec = self.spec
        self._print_section_details(spec.form)
        index = _prompt_int(
            "\n选择需要再生成的段落序号：",
            minimum=1,
            maximum=len(spec.form),
        )
        assert index is not None
        section_name = spec.form[index - 1].section
        keep = _prompt_bool(
            "是否保留当前动机标签？(y 保留 / n 自动切换)：",
            allow_empty=False,
        )
        keep_flag = True if keep is None else keep
        try:
            updated, summaries = regenerate_section(
                spec, section_name, keep_motif=keep_flag
            )
        except Exception as exc:
            print(f"再生成失败：{exc}")
            return
        self.spec = updated
        section_summary = summaries.get(section_name, {})
        print("局部再生成完成，最新段落摘要：")
        print(json.dumps(section_summary, ensure_ascii=False, indent=2))

    def _render_project(self) -> None:
        assert self.spec is not None
        output_dir_input = _prompt(
            f"请输入输出目录（默认 {settings.output_dir}，回车使用默认）：",
            allow_empty=True,
        )
        output_dir = (
            Path(output_dir_input).expanduser() if output_dir_input else Path(settings.output_dir)
        )
        emit_midi_flag = _prompt_bool(
            "是否生成 MIDI 文件？y/n：",
            allow_empty=False,
        )
        emit_midi = bool(emit_midi_flag)
        ensure_directory(output_dir)
        try:
            result = render_project(self.spec, output_dir, emit_midi=emit_midi)
        except Exception as exc:  # pragma: no cover - 渲染异常由下层定义
            print(f"渲染失败：{exc}")
            return
        self.last_render = result
        print("渲染成功，输出摘要如下：")
        self._print_render_summary(result)

    def _save_to_json(self) -> None:
        assert self.spec is not None
        path_str = _prompt("请输入保存路径（例如 ./projects/demo.json）：")
        path = Path(path_str).expanduser()
        ensure_directory(path.parent)
        payload = self.spec.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"规格已保存至 {path}")

    def _reset(self) -> None:
        print("已返回主菜单，可重新创建或加载工程。")
        self.spec = None
        self.last_render = None

    # ------------------------------------------------------------------
    # 辅助打印函数
    # ------------------------------------------------------------------
    @staticmethod
    def _print_spec_brief(spec: ProjectSpec) -> None:
        print(f"  调性: {spec.key} {spec.mode}")
        print(f"  速度: {spec.tempo_bpm} BPM, 拍号: {spec.meter}")
        print(f"  风格: {spec.style}")
        print(f"  节奏密度: {spec.rhythm_density}, 动机风格: {spec.motif_style}")
        print(f"  和声复杂度: {spec.harmony_level}")
        print(
            "  特性: 二级属{0}、借用和弦{1}、人性化渲染{2}".format(
                "已启用" if spec.use_secondary_dominant else "未启用",
                "已启用" if spec.use_borrowed_chords else "未启用",
                "已启用" if spec.humanization else "未启用",
            )
        )
        print("  配器: " + ", ".join(spec.instrumentation))

    @staticmethod
    def _print_section_details(sections: Iterable[FormSection]) -> None:
        print("\n曲式段落：")
        for idx, section in enumerate(sections, start=1):
            print(
                f"  {idx}. {section.section} | {section.bars} 小节 | 张力 {section.tension} | 动机 {section.motif_label}"
            )

    @staticmethod
    def _print_render_summary(result: RenderResult) -> None:
        print(f"  规格文件：{result['spec']}")
        print(f"  段落概要：{result['summary']}")
        midi_path = result.get("midi")
        if midi_path:
            print(f"  MIDI 输出：{midi_path}")
        else:
            print("  MIDI 输出：未生成")
        print("  分轨统计：")
        for track in result.get("track_stats", []):
            print(
                "    - {name}: {notes} 个音符, 时长 {duration_sec}s".format(
                    name=track.get("name"),
                    notes=track.get("notes"),
                    duration_sec=track.get("duration_sec"),
                )
            )


def launch_ui() -> None:
    """启动 FastAPI + Uvicorn，为 Web UI 提供后端。"""

    host = _prompt("请输入监听地址 [127.0.0.1]：", allow_empty=True) or "127.0.0.1"
    port_input = _prompt("请输入端口 [8000]：", allow_empty=True)
    try:
        port = int(port_input) if port_input else 8000
    except ValueError:
        print("端口必须是数字，已回退到 8000。")
        port = 8000
    log_level = settings.log_level.lower()
    config = uvicorn.Config(
        "motifmaker.api:app", host=host, port=port, log_level=log_level, reload=False
    )
    server = uvicorn.Server(config)
    print(
        f"\nFastAPI 服务启动中，请在另一终端运行前端 (web/) 或访问 http://{host}:{port}/docs 进行调试。"
    )
    print("按 Ctrl+C 可安全停止服务。\n")
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n已停止 FastAPI 服务。")


def main() -> None:
    """主入口：选择 UI 或控制台模式。"""

    configure_logging(logging.INFO)
    while True:
        choice = _prompt_menu(
            "MotifMaker 主程序",
            (
                "进入控制台调试模式",
                "启动 FastAPI + Web UI",
                "退出程序",
            ),
        )
        if choice == 1:
            ConsoleDebugger().run()
        elif choice == 2:
            launch_ui()
        else:
            print("再见！")
            break


if __name__ == "__main__":  # pragma: no cover - 手动运行入口
    main()

