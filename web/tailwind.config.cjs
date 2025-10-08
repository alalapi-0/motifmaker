/**
 * TailwindCSS 配置：限定扫描范围并允许按需生成原子类，
 * 避免在生产环境打包冗余样式。本轮扩展金属质感主题色，
 * 以便在组件中直接使用统一色板与字体。
 */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"], // 扫描模板与组件内的类名。
  theme: {
    extend: {
      colors: {
        // 金属黑红主题：深色背景与高饱和红色用于强调交互状态。
        darkmetal: "#0b0b0b",
        bloodred: "#e50914",
        graysteel: "#2a2a2a",
        gunmetal: "#1b1b1b",
      },
      fontFamily: {
        // Orbitron 字体体现未来感，搭配金属 UI 风格。
        orbitron: ["Orbitron", "sans-serif"],
      },
      boxShadow: {
        // 自定义内凹阴影模拟金属面板的压铸质感。
        metal: "inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 24px rgba(0,0,0,0.5)",
      },
      backgroundImage: {
        // Radial 渐变用于应用背景，制造聚光灯效果。
        "metal-radial": "radial-gradient(circle at 50% 50%, #1b1b1b 0%, #0a0a0a 100%)",
      },
    },
  },
  plugins: [], // 当前无需额外插件，后续可根据设计体系引入。
};
