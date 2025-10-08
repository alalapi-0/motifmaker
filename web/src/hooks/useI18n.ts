import { useContext } from "react";
import I18nContext, { TranslationKey, Lang } from "../i18n";

/**
 * useI18n Hook：封装对 I18nContext 的访问，避免组件直接操作 Context 对象。
 * 若出现未在 Provider 内使用的情况，会主动抛错提醒开发者修复。
 */
export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    // 为保持错误信息英文化，仅在注释中说明原因，避免 UI 出现中文残留。
    throw new Error("useI18n must be used within <I18nProvider>.");
  }
  return context;
}

export type { TranslationKey, Lang };
