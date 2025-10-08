import React, { useCallback, useMemo, useState } from "react";
import StepIndicator, { StepDefinition } from "./components/StepIndicator";
import MotifPanel from "./components/steps/MotifPanel";
import MelodyPanel from "./components/steps/MelodyPanel";
import MidiPanel from "./components/steps/MidiPanel";
import MixPanel, { MixSettings } from "./components/steps/MixPanel";
import RenderPanel from "./components/steps/RenderPanel";
import {
  generate,
  renderProject,
  renderAudioPreview,
  resolveAssetUrl,
  RenderSuccess,
} from "./api";

/**
 * App 组件：Round E 金属主题界面与分阶段音乐生成流程的核心容器。
 * - 顶部展示步骤导航，底部提供状态栏与进度条；
 * - 内部分为五个阶段：Motif → Melody → MIDI → Mixing → Final Track；
 * - 每个阶段完成后才会自动解锁下一阶段，确保流程结构化。
 */
const steps: StepDefinition[] = [
  { id: 1, label: "Motif" },
  { id: 2, label: "Melody" },
  { id: 3, label: "MIDI" },
  { id: 4, label: "Mixing" },
  { id: 5, label: "Final Track" },
];

const DEFAULT_PROMPT =
  "Forged synth metal intro, hybrid orchestra hits, halftime breakdown, neon skyline energy";

const App: React.FC = () => {
  const [step, setStep] = useState<number>(1); // 当前步骤索引。
  const [prompt, setPrompt] = useState<string>(DEFAULT_PROMPT); // Motif 生成使用的 Prompt。
  const [motifState, setMotifState] = useState<RenderSuccess | null>(null); // 保存后端生成的完整规格。
  const [motifLoading, setMotifLoading] = useState(false); // Motif 生成的加载态。
  const [motifError, setMotifError] = useState<string | null>(null); // Motif 生成的错误文案。

  const [melodyNotes, setMelodyNotes] = useState<string>(""); // Melody 阶段记录的旋律笔记。
  const [melodyLocked, setMelodyLocked] = useState(false); // Melody 阶段是否已经确认。

  const [arrangementNotes, setArrangementNotes] = useState<string>(""); // MIDI 阶段的结构规划。
  const [arrangementLoading, setArrangementLoading] = useState(false); // MIDI 渲染加载态。
  const [arrangementError, setArrangementError] = useState<string | null>(null); // MIDI 渲染错误。
  const [midiUrl, setMidiUrl] = useState<string | null>(null); // 最新的 MIDI 下载地址。

  const [mixSettings, setMixSettings] = useState<MixSettings>({
    reverb: 35,
    pan: 0,
    volume: -6,
    intensity: 55,
    preset: "metal-suite",
    style: "cinematic",
  }); // 混音参数集合。
  const [mixLoading, setMixLoading] = useState(false); // 混音阶段加载态。
  const [mixError, setMixError] = useState<string | null>(null); // 混音阶段错误提示。
  const [audioUrl, setAudioUrl] = useState<string | null>(null); // 最终音频地址。

  const [projectId] = useState<string>(() => {
    // 使用时间戳生成项目 ID，保证界面刷新前保持稳定。
    return `MM-${Date.now().toString(36).toUpperCase()}`;
  });

  const projectTitle = motifState?.project?.title ?? null;
  const motifSummary = motifState?.summary ?? null;

  const progress = useMemo(() => step / steps.length, [step]); // 计算底部进度条比例。

  const handleMotifGenerate = useCallback(async () => {
    setMotifLoading(true);
    setMotifError(null);
    try {
      const result = await generate(prompt);
      setMotifState(result);
      setMidiUrl(resolveAssetUrl(result.midi));
      setStep(2);
    } catch (error) {
      const message = (error as Error).message || "Failed to generate motif. Please retry.";
      setMotifError(message);
    } finally {
      setMotifLoading(false);
    }
  }, [prompt]);

  const handleMelodyConfirm = useCallback(() => {
    setMelodyLocked(true);
    setStep(3);
  }, []);

  const handleArrange = useCallback(async () => {
    if (!motifState) {
      setArrangementError("Generate a motif first.");
      return;
    }
    setArrangementLoading(true);
    setArrangementError(null);
    try {
      const result = await renderProject(motifState.project);
      setMotifState(result);
      setMidiUrl(resolveAssetUrl(result.midi));
      setStep(4);
    } catch (error) {
      const message = (error as Error).message || "Failed to arrange MIDI. Please try again.";
      setArrangementError(message);
    } finally {
      setArrangementLoading(false);
    }
  }, [motifState]);

  const handleMixRender = useCallback(async () => {
    if (!midiUrl) {
      setMixError("Arrange a MIDI file before mixing.");
      return;
    }
    setMixLoading(true);
    setMixError(null);
    setAudioUrl(null);
    try {
      const midiResponse = await fetch(midiUrl);
      if (!midiResponse.ok) {
        throw new Error("Unable to fetch the MIDI file for rendering.");
      }
      const midiBlob = await midiResponse.blob();
      const midiName = (() => {
        try {
          const parsed = new URL(midiUrl);
          const candidate = parsed.pathname.split("/").pop();
          if (candidate && candidate.trim().length > 0) {
            return candidate;
          }
        } catch (error) {
          // ignore URL parsing error and fallback to stored spec path
        }
        const fallback = motifState?.midi?.split(/[/\\]/).pop();
        return fallback && fallback.length > 0 ? fallback : "mix_render.mid";
      })();
      const midiFile = new File([midiBlob], midiName, {
        type: midiResponse.headers.get("Content-Type") ?? "audio/midi",
      });

      const { audio_url } = await renderAudioPreview({
        midiFile,
        style: mixSettings.style,
        intensity: mixSettings.intensity,
        reverb: mixSettings.reverb,
        pan: mixSettings.pan,
        volume: mixSettings.volume,
        preset: mixSettings.preset,
      });

      const resolved = resolveAssetUrl(audio_url);
      if (!resolved) {
        throw new Error("Audio render failed. Please try again later.");
      }
      setAudioUrl(resolved);
      setStep(5);
    } catch (error) {
      const message = (error as Error).message || "Audio render failed. Please try again later.";
      setMixError(message);
    } finally {
      setMixLoading(false);
    }
  }, [midiUrl, mixSettings, motifState?.midi]);

  const renderStage = () => {
    switch (step) {
      case 1:
        return (
          <MotifPanel
            prompt={prompt}
            onPromptChange={setPrompt}
            onGenerate={handleMotifGenerate}
            loading={motifLoading}
            error={motifError}
            summary={motifSummary}
            projectTitle={projectTitle}
          />
        );
      case 2:
        return (
          <MelodyPanel
            notes={melodyNotes}
            onNotesChange={setMelodyNotes}
            onConfirm={handleMelodyConfirm}
            disabled={!motifState}
          />
        );
      case 3:
        return (
          <MidiPanel
            arrangement={arrangementNotes}
            onArrangementChange={setArrangementNotes}
            onArrange={handleArrange}
            loading={arrangementLoading}
            disabled={!melodyLocked}
            midiUrl={midiUrl}
            error={arrangementError}
          />
        );
      case 4:
        return (
          <MixPanel
            settings={mixSettings}
            onSettingsChange={setMixSettings}
            onRender={handleMixRender}
            loading={mixLoading}
            disabled={!midiUrl}
            error={mixError}
            audioUrl={audioUrl}
          />
        );
      case 5:
      default:
        return (
          <RenderPanel
            audioUrl={audioUrl}
            midiUrl={midiUrl}
            projectTitle={projectTitle}
            projectId={projectId}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-metal-radial pb-24 text-gray-200">
      <header className="sticky top-0 z-40 border-b border-bloodred/30 bg-black/60 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-6 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-bloodred">MotifMaker</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Metal Forge Pipeline</h1>
          </div>
          <StepIndicator steps={steps} currentStep={step} />
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        <div key={step} className="animate-metal-fade">
          {renderStage()}
        </div>
      </main>
      <footer className="fixed bottom-0 left-0 right-0 border-t border-bloodred/30 bg-black/70 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-6 py-4 text-xs uppercase tracking-[0.25em] text-gray-500 md:flex-row md:items-center md:justify-between">
          <span>Phase {step} of {steps.length}</span>
          <div className="flex flex-1 items-center gap-4 md:justify-end">
            <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-gray-700">
              <div
                className="h-full bg-gradient-to-r from-bloodred via-red-600 to-red-400"
                style={{ width: `${Math.max(progress, 0.05) * 100}%` }}
              />
            </div>
            <span className="text-sm normal-case tracking-[0.1em] text-gray-300">
              {steps[Math.min(step - 1, steps.length - 1)].label}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
