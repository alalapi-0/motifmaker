import React, { useCallback, useMemo, useRef, useState } from "react";
import { ProjectSpec } from "../api";
import { useI18n } from "../hooks/useI18n";

export type RegenerateMode = "melody" | "melody-harmony";

export interface FormTableProps {
  projectSpec: ProjectSpec | null; // 当前的工程规格，可能尚未生成。
  onUpdateSection: (index: number, updates: Partial<ProjectSpec["form"][number]>) => void; // 编辑单元格后的回调。
  onRegenerateSection: (index: number, mode: RegenerateMode) => Promise<void> | void; // 局部再生按钮触发的回调。
  regenerating: boolean; // 是否处于局部再生中，禁用按钮避免重复提交。
  onFreezeMotifs: (motifTags: string[]) => Promise<void> | void; // 批量冻结选中的动机。
  freezeLoading: boolean; // 冻结请求状态。
}

const editableFields: Array<keyof ProjectSpec["form"][number]> = ["bars", "tension", "motif_label"];

/**
 * FormTable 组件：以无障碍友好的表格展示并编辑 ProjectSpec.form。
 * - 支持方向键导航、Enter 编辑、Esc 取消；
 * - 新增冻结列，可批量勾选后提交 /freeze-motif；
 * - 行内提供再生成模式切换（仅旋律 / 旋律+和声）。
 */
const FormTable: React.FC<FormTableProps> = ({
  projectSpec,
  onUpdateSection,
  onRegenerateSection,
  regenerating,
  onFreezeMotifs,
  freezeLoading,
}) => {
  const { t } = useI18n();
  const tableRef = useRef<HTMLTableElement | null>(null);
  const [editing, setEditing] = useState<{ row: number; field: keyof ProjectSpec["form"][number] } | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [selectedMotifs, setSelectedMotifs] = useState<string[]>([]);
  const [regenerateModes, setRegenerateModes] = useState<Record<number, RegenerateMode>>({});

  const rows = projectSpec?.form ?? [];
  const motifOptions = useMemo(
    () => Object.keys(projectSpec?.motif_specs ?? {}),
    [projectSpec?.motif_specs]
  );

  const handleStartEdit = useCallback(
    (rowIndex: number, field: keyof ProjectSpec["form"][number]) => {
      const row = rows[rowIndex];
      if (!row || !editableFields.includes(field)) return;
      setEditing({ row: rowIndex, field });
      setDraft(String(row[field] ?? ""));
    },
    [rows]
  );

  const focusCell = useCallback((rowIndex: number, field: keyof ProjectSpec["form"][number]) => {
    const cell = tableRef.current?.querySelector<HTMLElement>(
      `[data-cell-id="${rowIndex}-${field}"]`
    );
    cell?.focus();
  }, []);

  const validateDraft = useCallback(
    (field: keyof ProjectSpec["form"][number], value: string) => {
      if (field === "bars") {
        const num = Number(value);
        if (!Number.isInteger(num) || num < 1 || num > 128) {
          return t("form.validation.bars");
        }
      }
      if (field === "tension") {
        const num = Number(value);
        if (!Number.isInteger(num) || num < 0 || num > 100) {
          return t("form.validation.tension");
        }
      }
      if (field === "motif_label") {
        if (!value.trim()) {
          return t("form.validation.motif");
        }
      }
      return null;
    },
    [t]
  );

  const handleCommit = useCallback(async () => {
    if (!editing) return;
    const { row, field } = editing;
    const error = validateDraft(field, draft);
    if (error) {
      setErrors((prev) => ({ ...prev, [`${row}-${field}`]: error }));
      return;
    }
    setErrors((prev) => ({ ...prev, [`${row}-${field}`]: null }));
    const nextValue = field === "motif_label" ? draft.trim() : Number(draft);
    onUpdateSection(row, { [field]: nextValue } as Partial<ProjectSpec["form"][number]>);
    setEditing(null);
    focusCell(row, field);
  }, [draft, editing, focusCell, onUpdateSection, validateDraft]);

  const handleKeyDownCell = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>, rowIndex: number, field: keyof ProjectSpec["form"][number]) => {
      const columns = editableFields;
      const columnIndex = columns.indexOf(field);
      if (event.key === "Enter") {
        event.preventDefault();
        handleStartEdit(rowIndex, field);
      }
      if (event.key === "ArrowRight" && columnIndex < columns.length - 1) {
        event.preventDefault();
        focusCell(rowIndex, columns[columnIndex + 1]);
      }
      if (event.key === "ArrowLeft" && columnIndex > 0) {
        event.preventDefault();
        focusCell(rowIndex, columns[columnIndex - 1]);
      }
      if (event.key === "ArrowDown" && rowIndex < rows.length - 1) {
        event.preventDefault();
        focusCell(rowIndex + 1, field);
      }
      if (event.key === "ArrowUp" && rowIndex > 0) {
        event.preventDefault();
        focusCell(rowIndex - 1, field);
      }
    },
    [focusCell, handleStartEdit, rows.length]
  );

  const handleFreeze = useCallback(async () => {
    if (!selectedMotifs.length) return;
    await onFreezeMotifs(Array.from(new Set(selectedMotifs)));
    setSelectedMotifs([]);
  }, [onFreezeMotifs, selectedMotifs]);

  if (!projectSpec) {
    return (
      <section className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
        {t("form.empty")}
      </section>
    );
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("form.title")}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("form.subtitle")}</p>
        </div>
        <button
          type="button"
          className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 transition hover:border-slate-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
          onClick={handleFreeze}
          disabled={!selectedMotifs.length || freezeLoading}
        >
          {t("form.freezeSelected")}
        </button>
      </header>
      <div className="overflow-x-auto">
        <table
          ref={tableRef}
          className="min-w-full divide-y divide-slate-200 text-xs dark:divide-slate-700"
          role="grid"
        >
          <thead className="bg-slate-100 dark:bg-slate-800">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.section")}</th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.bars")}</th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.tension")}</th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.motif")}</th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.freeze")}</th>
              <th className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300">{t("form.column.actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {rows.map((section, index) => {
              const motifMeta = projectSpec.motif_specs?.[section.motif_label];
              const isFrozen = Boolean(motifMeta?._frozen);
              const mode = regenerateModes[index] ?? "melody-harmony";
              return (
                <tr key={`${section.section}-${index}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/60">
                  <td className="px-3 py-2 font-medium text-slate-900 dark:text-slate-100">{section.section}</td>
                  {editableFields.slice(0, 3).map((field) => {
                    if (field === "motif_label") {
                      return null; // 单独处理动机列，保持顺序。
                    }
                    const cellId = `${index}-${field}`;
                    const isEditing = editing?.row === index && editing.field === field;
                    return (
                      <td key={field} className="px-3 py-2 align-top">
                        {isEditing ? (
                          <input
                            value={draft}
                            type="number"
                            min={field === "bars" ? 1 : 0}
                            max={field === "bars" ? 128 : 100}
                            className="w-full rounded border border-slate-300 px-2 py-1 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                            onChange={(event) => setDraft(event.target.value)}
                            onBlur={handleCommit}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                handleCommit();
                              }
                              if (event.key === "Escape") {
                                event.preventDefault();
                                setEditing(null);
                              }
                            }}
                            autoFocus
                          />
                        ) : (
                          <div
                            role="gridcell"
                            tabIndex={0}
                            data-cell-id={cellId}
                            className="cursor-text rounded px-2 py-1 focus:outline focus:outline-2 focus:outline-cyan-500"
                            onKeyDown={(event) => handleKeyDownCell(event, index, field)}
                            onDoubleClick={() => handleStartEdit(index, field)}
                          >
                            {section[field]}
                          </div>
                        )}
                        {errors[cellId] && (
                          <p className="mt-1 text-[11px] text-red-500">{errors[cellId]}</p>
                        )}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2 align-top">
                    {editing?.row === index && editing.field === "motif_label" ? (
                      <div className="space-y-1">
                        <input
                          list={`motif-options-${index}`}
                          value={draft}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-xs text-slate-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                          onChange={(event) => setDraft(event.target.value)}
                          onBlur={handleCommit}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              handleCommit();
                            }
                            if (event.key === "Escape") {
                              event.preventDefault();
                              setEditing(null);
                            }
                          }}
                          autoFocus
                        />
                        <datalist id={`motif-options-${index}`}>
                          {motifOptions.map((option) => (
                            <option key={option} value={option} />
                          ))}
                        </datalist>
                      </div>
                    ) : (
                      <div
                        role="gridcell"
                        tabIndex={0}
                        data-cell-id={`${index}-motif_label`}
                        className="cursor-text rounded px-2 py-1 focus:outline focus:outline-2 focus:outline-cyan-500"
                        onKeyDown={(event) => handleKeyDownCell(event, index, "motif_label")}
                        onDoubleClick={() => handleStartEdit(index, "motif_label")}
                      >
                        <span className="font-medium text-slate-900 dark:text-slate-100">{section.motif_label}</span>
                        {isFrozen && (
                          <span className="ml-2 rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] text-amber-700 dark:bg-amber-500/30 dark:text-amber-200">
                            {t("form.frozenTag")}
                          </span>
                        )}
                      </div>
                    )}
                    {errors[`${index}-motif_label`] && (
                      <p className="mt-1 text-[11px] text-red-500">{errors[`${index}-motif_label`]}</p>
                    )}
                  </td>
                  <td className="px-3 py-2 align-top">
                    <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                      <input
                        type="checkbox"
                        checked={selectedMotifs.includes(section.motif_label)}
                        disabled={isFrozen || freezeLoading}
                        onChange={(event) => {
                          const next = new Set(selectedMotifs);
                          if (event.target.checked) {
                            next.add(section.motif_label);
                          } else {
                            next.delete(section.motif_label);
                          }
                          setSelectedMotifs(Array.from(next));
                        }}
                      />
                      {section.motif_label}
                    </label>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-col gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <label className="flex items-center gap-1">
                          <input
                            type="radio"
                            name={`mode-${index}`}
                            value="melody"
                            checked={mode === "melody"}
                            onChange={() =>
                              setRegenerateModes((prev) => ({ ...prev, [index]: "melody" }))
                            }
                          />
                          {t("form.regenerateMelodyOnly")}
                        </label>
                        <label className="flex items-center gap-1">
                          <input
                            type="radio"
                            name={`mode-${index}`}
                            value="melody-harmony"
                            checked={mode === "melody-harmony"}
                            onChange={() =>
                              setRegenerateModes((prev) => ({ ...prev, [index]: "melody-harmony" }))
                            }
                          />
                          {t("form.regenerateMelodyHarmony")}
                        </label>
                      </div>
                      <button
                        type="button"
                        className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 transition hover:border-slate-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
                        disabled={regenerating}
                        onClick={() => onRegenerateSection(index, mode)}
                      >
                        {t("form.regenerate")}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">{t("form.keyboardHelp")}</p>
    </section>
  );
};

export default FormTable;
