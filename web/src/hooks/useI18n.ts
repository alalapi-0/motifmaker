import { useContext } from "react";
import I18nContext, { TranslationKey, Lang } from "../i18n";

/**
 * useI18n Hook：封装对 I18nContext 的访问，避免组件直接操作 Context 对象。
 * 若出现未在 Provider 内使用的情况，会主动抛错提醒开发者修复。
 */
export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n 必须在 <I18nProvider> 内使用");
  }
  return context;
}

export type { TranslationKey, Lang };
