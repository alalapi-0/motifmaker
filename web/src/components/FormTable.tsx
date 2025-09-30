import React from "react";
import { ProjectSpec } from "../api";

interface FormTableProps {
  project: ProjectSpec | null;
  onUpdateSection: (
    index: number,
    updates: { bars?: number; tension?: number; motif_label?: string }
  ) => void;
  onRegenerate: (index: number, keepMotif: boolean) => void;
  onFreezeMotif: (motifTag: string) => void;
}

const FormTable: React.FC<FormTableProps> = ({
  project,
  onUpdateSection,
  onRegenerate,
  onFreezeMotif,
}) => {
  if (!project) {
    return (
      <div className="rounded-md border border-slate-700 p-4 text-sm text-slate-400">
        请先生成项目，随后可在此编辑段落与触发局部再生。
      </div>
    );
  }

  const motifOptions = Object.keys(project.motif_specs);

  return (
    <div className="overflow-x-auto rounded-md border border-slate-700">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-slate-800 uppercase text-slate-300">
          <tr>
            <th className="px-3 py-2">段落</th>
            <th className="px-3 py-2">小节数</th>
            <th className="px-3 py-2">张力</th>
            <th className="px-3 py-2">动机</th>
            <th className="px-3 py-2">操作</th>
          </tr>
        </thead>
        <tbody>
          {project.form.map((section, index) => (
            <tr key={`${section.section}-${index}`} className="odd:bg-slate-900">
              <td className="px-3 py-2 font-semibold">{section.section}</td>
              <td className="px-3 py-2">
                <input
                  type="number"
                  className="w-20 rounded-md bg-slate-800 p-1"
                  value={section.bars}
                  onChange={(event) =>
                    onUpdateSection(index, { bars: Number(event.target.value) })
                  }
                />
              </td>
              <td className="px-3 py-2">
                <input
                  type="number"
                  step="0.05"
                  min={0}
                  max={1}
                  className="w-20 rounded-md bg-slate-800 p-1"
                  value={section.tension}
                  onChange={(event) =>
                    onUpdateSection(index, { tension: Number(event.target.value) })
                  }
                />
              </td>
              <td className="px-3 py-2">
                <select
                  className="rounded-md bg-slate-800 p-1"
                  value={section.motif_label}
                  onChange={(event) =>
                    onUpdateSection(index, { motif_label: event.target.value })
                  }
                >
                  {motifOptions.map((label) => (
                    <option key={label} value={label}>
                      {label}
                    </option>
                  ))}
                </select>
              </td>
              <td className="space-y-1 px-3 py-2">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-md bg-cyan-500 px-2 py-1 text-xs font-semibold text-slate-900"
                    onClick={() => onRegenerate(index, true)}
                  >
                    局部再生成
                  </button>
                  <button
                    type="button"
                    className="rounded-md bg-amber-400 px-2 py-1 text-xs font-semibold text-slate-900"
                    onClick={() => onRegenerate(index, false)}
                  >
                    更换动机再生
                  </button>
                  <button
                    type="button"
                    className="rounded-md bg-fuchsia-500 px-2 py-1 text-xs font-semibold text-slate-900"
                    onClick={() => onFreezeMotif(section.motif_label)}
                  >
                    冻结动机
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default FormTable;
