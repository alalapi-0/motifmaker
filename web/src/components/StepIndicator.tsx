import React from "react";
import clsx from "clsx";

export interface StepDefinition {
  id: number;
  label: string;
  description?: string;
}

interface StepIndicatorProps {
  steps: StepDefinition[];
  currentStep: number;
  highestUnlocked: number;
  onStepChange: (stepId: number) => void;
  onBack: () => void;
  onNext: () => void;
  canGoBack: boolean;
  canGoNext: boolean;
  nextLabel?: string;
  nextDisabledReason?: string | null;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({
  steps,
  currentStep,
  highestUnlocked,
  onStepChange,
  onBack,
  onNext,
  canGoBack,
  canGoNext,
  nextLabel = "Next",
  nextDisabledReason,
}) => {
  return (
    <div className="flex w-full flex-col gap-4">
      <nav aria-label="Workflow progress" className="flex flex-col gap-2">
        <ol className="flex flex-wrap items-center gap-4 text-xs uppercase tracking-[0.3em] text-gray-300">
          {steps.map((step, index) => {
            const isActive = step.id === currentStep;
            const isCompleted = step.id < currentStep;
            const isLocked = step.id > highestUnlocked;
            const isClickable = !isLocked && step.id !== currentStep;
            return (
              <li key={step.id} className="flex items-center gap-4">
                <button
                  type="button"
                  className={clsx(
                    "group flex min-w-[120px] flex-col items-start rounded-md border px-3 py-2 text-left text-[11px] tracking-[0.2em] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/80 focus-visible:ring-offset-2 focus-visible:ring-offset-black",
                    isActive
                      ? "border-bloodred/70 bg-bloodred/20 text-white shadow-[0_0_0_1px_rgba(229,9,20,0.35)]"
                      : isCompleted
                      ? "border-bloodred/30 bg-black/40 text-gray-100 hover:border-bloodred/60"
                      : isLocked
                      ? "border-gray-700/60 bg-black/20 text-gray-500"
                      : "border-gray-600/60 bg-black/30 text-gray-200 hover:border-bloodred/60"
                  )}
                  onClick={() => isClickable && onStepChange(step.id)}
                  disabled={!isClickable}
                  aria-current={isActive ? "step" : undefined}
                  aria-disabled={isLocked}
                >
                  <span className="text-[10px] font-semibold text-bloodred/80">STEP {step.id}</span>
                  <span className="mt-1 text-sm font-semibold tracking-[0.1em] text-white">{step.label}</span>
                  {step.description && (
                    <span className="mt-1 text-[10px] normal-case tracking-normal text-gray-400">{step.description}</span>
                  )}
                </button>
                {index < steps.length - 1 && (
                  <div className="h-px w-12 bg-gradient-to-r from-transparent via-bloodred/40 to-transparent" aria-hidden="true" />
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-gray-300">
          <span className="text-bloodred">{`0${currentStep}`.slice(-2)}</span>
          <span className="text-gray-500">/</span>
          <span>{`0${steps.length}`.slice(-2)}</span>
        </div>
        <div className="h-px flex-1 bg-gradient-to-r from-bloodred/40 via-red-500/30 to-transparent" aria-hidden="true" />
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="metal-button rounded-md px-4 py-2 text-xs"
            onClick={onBack}
            disabled={!canGoBack}
          >
            Back
          </button>
          <button
            type="button"
            className="metal-button rounded-md px-4 py-2 text-xs"
            onClick={onNext}
            disabled={!canGoNext}
          >
            {nextLabel}
          </button>
        </div>
      </div>
      {!canGoNext && nextDisabledReason && (
        <p className="text-[11px] text-gray-300">
          {nextDisabledReason}
        </p>
      )}
    </div>
  );
};

export default StepIndicator;
