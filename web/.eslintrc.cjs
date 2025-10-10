module.exports = {
  // 中文注释：设为根配置，避免被上层 ESLint 配置污染。
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended'
  ],
  settings: { react: { version: 'detect' } },
  env: { browser: true, es2022: true, node: true },
  ignorePatterns: ['dist/', 'node_modules/'],
  rules: {
    // 中文注释：React 18+ 自动注入 JSX 转换函数，关闭历史遗留规则避免噪音。
    'react/react-in-jsx-scope': 'off',
    // 中文注释：历史代码大量使用 any 类型，保留灵活性并后续逐步治理。
    '@typescript-eslint/no-explicit-any': 'off',
    // 中文注释：部分组件内部会保留中间变量，关闭未使用变量的强制错误。
    '@typescript-eslint/no-unused-vars': 'off',
    // 中文注释：复杂依赖数组后续再细化，暂时关闭 hooks 依赖校验避免误报。
    'react-hooks/exhaustive-deps': 'off'
  }
};
