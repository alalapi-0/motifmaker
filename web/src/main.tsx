import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";
import App from "./App";

// 入口函数：在 #root 节点挂载 React 应用。
ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
