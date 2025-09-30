import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 使用中文注释说明：该配置启用 React 插件并开放开发服务器主机，方便容器调试。
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
});
