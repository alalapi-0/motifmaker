import React from "react";
import clsx from "clsx";

/**
 * StepIndicator 组件：顶栏步骤导航，突出当前阶段并告知整体进度。
 * - 使用红色光条凸显激活步骤；
 * - 结合金属质感的字体与分隔线，营造工业风格。
 */
export interface StepDefinition {
  id: number;
  label: string;
  description?: string;
}

interface StepIndicatorProps {
  steps: StepDefinition[];
  currentStep: number;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ steps, currentStep }) => {
  return (
    <nav className="flex items-center gap-8 text-xs uppercase tracking-[0.3em] text-gray-400">
      {steps.map((step, index) => {
        const isActive = step.id === currentStep;
        const isCompleted = step.id < currentStep;
        return (
          <div
            key={step.id}
            className={clsx(
              "flex flex-col items-center text-center transition-colors duration-200",
              isActive ? "text-white glow-line" : isCompleted ? "text-gray-200" : "text-gray-500"
            )}
          >
            <div className="text-[0.65rem]">{`${step.id.toString().padStart(2, "0")}/${steps.length}`}</div>
            <div className="mt-1 font-semibold">{step.label}</div>
            {index < steps.length - 1 && (
              <div className="mt-3 h-px w-16 bg-gradient-to-r from-transparent via-bloodred/40 to-transparent" />
            )}
          </div>
        );
      })}
    </nav>
  );
};

export default StepIndicator;
