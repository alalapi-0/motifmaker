/**
 * PostCSS 配置：按照 Tailwind 官方推荐顺序挂载插件，
 * 先运行 TailwindCSS，再使用 Autoprefixer 兼容不同浏览器。
 */
module.exports = {
  plugins: {
    tailwindcss: {}, // 负责解析 @tailwind 指令并生成工具类。
    autoprefixer: {}, // 自动补全浏览器厂商前缀，减少手动适配成本。
  },
};
