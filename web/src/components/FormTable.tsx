import React from "react";
import { FormSection, ProjectSpec } from "../api";

/**
 * FormTable 组件：以表格形式展示并编辑 ProjectSpec.form 段落信息。
 * 用户可以调整小节数、张力及动机标签，并针对单独段落触发局部再生，
 * 从而在不重新生成整首曲子的前提下快速迭代局部内容。
 */
export interface FormTableProps {
  projectSpec: ProjectSpec | null; // 当前的工程规格，可能尚未生成。
  onUpdateSection: (index: number, updates: Partial<FormSection>) => void; // 编辑单元格后的回调。
  onRegenerateSection: (index: number, keepMotif: boolean) => void; // 局部再生按钮触发的回调。
}

const FormTable: React.FC<FormTableProps> = ({
  projectSpec,
  onUpdateSection,
  onRegenerateSection,
}) => {
  if (!projectSpec) {
    return (
      <section className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
        生成后可在此查看曲式段落，并对每段进行细节调整。
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-sm">
      <header className="space-y-1">
        <h2 className="text-sm font-semibold text-slate-200">曲式段落表</h2>
        <p className="text-xs text-slate-400">
          表格中的修改会实时更新前端缓存的 ProjectSpec；点击“局部再生成”时，会携带这些修改提交给后端。
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-800 text-xs">
          <thead className="bg-slate-900/80">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-slate-300">段落</th>
              <th className="px-3 py-2 text-left font-medium text-slate-300">小节数</th>
              <th className="px-3 py-2 text-left font-medium text-slate-300">张力</th>
              <th className="px-3 py-2 text-left font-medium text-slate-300">动机标签</th>
              <th className="px-3 py-2 text-left font-medium text-slate-300">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {projectSpec.form.map((section, index) => (
              <tr
                key={`${section.section}-${index}`}
                className="hover:bg-slate-800/60"
              >
                <td className="px-3 py-2 font-medium text-slate-200">{section.section}</td>
                <td className="px-3 py-2">
                  <sl-input
                    value={String(section.bars)}
                    type="number"
                    min="1"
                    onSlChange={(event) => {
                      const target = event.target as HTMLInputElement;
                      onUpdateSection(index, { bars: Number(target.value) });
                    }}
                  ></sl-input>
                </td>
                <td className="px-3 py-2">
                  <sl-input
                    value={String(section.tension)}
                    type="number"
                    min="0"
                    max="10"
                    onSlChange={(event) => {
                      const target = event.target as HTMLInputElement;
                      onUpdateSection(index, { tension: Number(target.value) });
                    }}
                  ></sl-input>
                </td>
                <td className="px-3 py-2">
                  <sl-input
                    value={section.motif_label}
                    onSlChange={(event) => {
                      const target = event.target as HTMLInputElement;
                      onUpdateSection(index, { motif_label: target.value });
                    }}
                  ></sl-input>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-2">
                    <sl-button
                      size="small"
                      variant="primary"
                      onClick={() => onRegenerateSection(index, true)}
                    >
                      保留动机再生
                    </sl-button>
                    <sl-button
                      size="small"
                      variant="default"
                      onClick={() => onRegenerateSection(index, false)}
                    >
                      重新分配动机
                    </sl-button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-400">
        为什么要局部再生？因为整曲重新生成成本较高，局部再生可以在保留整体结构的前提下迭代局部细节，显著缩短等待时间。
      </p>
    </section>
  );
};

export default FormTable;
