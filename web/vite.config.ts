import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite 配置文件：集中处理开发服务器、别名与插件配置。
 * 这里全部使用中文注释，方便团队了解每个选项的作用。
 */
export default defineConfig({
  plugins: [
    // 启用 React 插件，自动处理 JSX/TSX 转换与快速刷新功能。
    react(),
  ],
  resolve: {
    alias: {
      // 设置 "@" 为 src 目录别名，便于在组件中引用文件且避免相对路径地狱。
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    host: "0.0.0.0", // 监听 0.0.0.0，方便容器或局域网内其他设备访问。
    port: 5173, // 固定端口号为 5173，与 README 中的访问指引一致。
  },
});
