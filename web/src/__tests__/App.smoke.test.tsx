// 中文注释：此测试为 UI 冒烟用例，确保核心布局在渲染初期即可正常展示。
import { render, screen } from '@testing-library/react';

import App from '../App';

describe('App UI smoke test', () => {
  it('renders title and key actions', () => {
    // 中文注释：渲染顶层 App 组件，检查页面结构是否加载。
    render(<App />);

    // 中文注释：标题应展示产品名称，验证主框架挂载成功。
    expect(screen.getByText('Metal Forge Pipeline')).toBeInTheDocument();

    // 中文注释：步骤导航至少包含 Motif 阶段，确保流程入口未缺失。
    expect(screen.getAllByText('Motif').length).toBeGreaterThan(0);

    // 中文注释：首屏 Motif 面板应展示生成按钮，验证关键交互入口。
    expect(screen.getByText('Generate Motif')).toBeInTheDocument();
  });
});
