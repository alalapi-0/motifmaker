import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import { I18nProvider } from "./i18n"; // 引入轻量级多语言 Provider，确保所有子组件可访问 t()。

/**
 * 应用入口：负责挂载 React 根节点并加载全局样式。
 * Vite 会以该文件为起点构建依赖图，确保组件热更新有效。
 */
const rootElement = document.getElementById("root");

if (!rootElement) {
  // 运行时异常也统一改为英文提示，避免打包后仍出现中文文案。
  throw new Error("Failed to locate #root element. Unable to bootstrap the web app.");
}

// createRoot 会启用 React 18 的并发特性，提升交互体验。
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    {/* 通过 I18nProvider 包裹 App，提供 t() 等接口；当前仅启用英文语言包以统一界面。*/}
    <I18nProvider>
      <App />
    </I18nProvider>
  </React.StrictMode>
);
