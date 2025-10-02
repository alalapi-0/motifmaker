import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

/**
 * 应用入口：负责挂载 React 根节点并加载全局样式。
 * Vite 会以该文件为起点构建依赖图，确保组件热更新有效。
 */
const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("未找到 #root 节点，无法启动前端应用。");
}

// createRoot 会启用 React 18 的并发特性，提升交互体验。
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    {/* StrictMode 可在开发期提示潜在的副作用问题。*/}
    <App />
  </React.StrictMode>
);
