/**
 * TailwindCSS 配置：限定扫描范围并允许按需生成原子类，
 * 避免在生产环境打包冗余样式。
 */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"], // 扫描模板与组件内的类名。
  theme: {
    extend: {}, // 可按需扩展主题色/字体，此处保持默认即可。
  },
  plugins: [], // 当前无需额外插件，后续可根据设计体系引入。
};
