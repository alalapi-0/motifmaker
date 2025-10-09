import React, { useMemo, useState } from "react";

interface JsonPreviewPanelProps {
  data: unknown | null;
  title?: string;
  downloadFileName?: string;
}

type JsonPath = Array<string | number>;

type CollapsedMap = Record<string, boolean>;

const pathKey = (path: JsonPath) => path.join(".");

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isCollapsible = (value: unknown) => isRecord(value) || Array.isArray(value);

const stringifyValue = (value: unknown) => {
  if (typeof value === "string") return `"${value}"`;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value === null) return "null";
  return JSON.stringify(value);
};

const highlight = (text: string, term: string) => {
  if (!term) return text;
  const lower = text.toLowerCase();
  const lowerTerm = term.toLowerCase();
  const parts: Array<string | React.ReactNode> = [];
  let index = 0;
  while (index < text.length) {
    const matchIndex = lower.indexOf(lowerTerm, index);
    if (matchIndex === -1) {
      parts.push(text.slice(index));
      break;
    }
    if (matchIndex > index) {
      parts.push(text.slice(index, matchIndex));
    }
    parts.push(
      <mark key={`${matchIndex}-${term}`} className="rounded bg-bloodred/30 px-0.5 text-white">
        {text.slice(matchIndex, matchIndex + term.length)}
      </mark>
    );
    index = matchIndex + term.length;
  }
  return <>{parts}</>;
};

const nodeContainsTerm = (value: unknown, term: string): boolean => {
  if (!term) return true;
  const normalized = term.toLowerCase();
  if (typeof value === "string") {
    return value.toLowerCase().includes(normalized);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value).toLowerCase().includes(normalized);
  }
  if (value === null || value === undefined) {
    return false;
  }
  if (Array.isArray(value)) {
    return value.some((item) => nodeContainsTerm(item, term));
  }
  if (isRecord(value)) {
    return Object.entries(value).some(
      ([key, item]) => key.toLowerCase().includes(normalized) || nodeContainsTerm(item, term)
    );
  }
  return false;
};

const collectPaths = (value: unknown, base: JsonPath = []): string[] => {
  if (!isCollapsible(value)) {
    return [];
  }
  const currentKey = pathKey(base);
  const nested: string[] = [];
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      nested.push(...collectPaths(item, [...base, index]));
    });
  } else {
    Object.entries(value).forEach(([key, item]) => {
      nested.push(...collectPaths(item, [...base, key]));
    });
  }
  return currentKey ? [currentKey, ...nested] : nested;
};

const JsonPreviewPanel: React.FC<JsonPreviewPanelProps> = ({ data, title = "ProjectSpec JSON", downloadFileName }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [collapsed, setCollapsed] = useState<CollapsedMap>({});

  const jsonString = useMemo(() => (data ? JSON.stringify(data, null, 2) : ""), [data]);
  const allPaths = useMemo(() => collectPaths(data ?? null), [data]);
  const normalizedSearch = searchTerm.trim().toLowerCase();

  const handleCopy = async () => {
    if (!jsonString) return;
    await navigator.clipboard.writeText(jsonString);
  };

  const handleExport = () => {
    if (!jsonString) return;
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = downloadFileName ?? "project-spec.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const togglePath = (key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const collapseAll = () => {
    const next: CollapsedMap = {};
    allPaths.forEach((key) => {
      if (key) next[key] = true;
    });
    setCollapsed(next);
  };

  const expandAll = () => {
    setCollapsed({});
  };

  const renderNode = (value: unknown, path: JsonPath = [], name?: string): React.ReactNode => {
    const key = pathKey(path);
    const collapsible = isCollapsible(value);
    const matchesTerm = normalizedSearch ? nodeContainsTerm(value, normalizedSearch) : true;
    const keyMatches = normalizedSearch ? name?.toLowerCase().includes(normalizedSearch) ?? false : true;
    if (!matchesTerm && !keyMatches) {
      return null;
    }

    const isCollapsed = collapsed[key];
    const shouldForceExpand = Boolean(normalizedSearch && matchesTerm);
    const showChildren = collapsible && (!isCollapsed || shouldForceExpand);

    const header = (
      <div className="flex items-center gap-2 py-1 text-xs text-gray-200">
        {collapsible ? (
          <button
            type="button"
            className="flex h-5 w-5 items-center justify-center rounded border border-bloodred/40 bg-black/60 text-[11px] text-gray-200 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/70 focus-visible:ring-offset-2 focus-visible:ring-offset-black"
            onClick={() => togglePath(key)}
            aria-expanded={!isCollapsed}
            aria-label={`${isCollapsed ? "Expand" : "Collapse"} ${name ?? "node"}`}
          >
            {isCollapsed ? "+" : "−"}
          </button>
        ) : (
          <span className="h-5 w-5" aria-hidden="true" />
        )}
        {name && <span className="font-semibold text-gray-100">{highlight(name, searchTerm)}</span>}
        {collapsible ? (
          <span className="text-gray-400">
            {Array.isArray(value)
              ? `Array(${value.length})`
              : `Object(${Object.keys(value as Record<string, unknown>).length})`}
          </span>
        ) : (
          <span className="text-gray-200">{highlight(stringifyValue(value), searchTerm)}</span>
        )}
      </div>
    );

    if (!collapsible) {
      return (
        <li key={key || name} className="pl-4">
          {header}
        </li>
      );
    }

    const childItems = Array.isArray(value)
      ? value.map((item, index) => renderNode(item, [...path, index], `[${index}]`))
      : Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) =>
          renderNode(childValue, [...path, childKey], childKey)
        );

    return (
      <li key={key || name} className="pl-4">
        {header}
        {showChildren && (
          <ul className="ml-4 border-l border-gray-700/40 pl-4">
            {childItems.filter(Boolean).length ? childItems : (
              <li className="py-1 text-xs text-gray-500">(empty)</li>
            )}
          </ul>
        )}
      </li>
    );
  };

  return (
    <section className="metal-panel rounded-xl p-6 text-sm text-gray-200">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-bloodred">{title}</p>
          <h2 className="text-xl font-semibold text-white">Live ProjectSpec</h2>
        </div>
        <button
          type="button"
          className="metal-button rounded-md px-4 py-2 text-xs"
          onClick={() => setIsOpen((value) => !value)}
        >
          {isOpen ? "Collapse" : "Expand"} preview
        </button>
      </header>

      {isOpen ? (
        data ? (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div className="flex items-center gap-2">
                <label htmlFor="json-search" className="text-gray-300">
                  Search
                </label>
                <input
                  id="json-search"
                  type="search"
                  className="w-56 rounded border border-gray-600 bg-black/50 px-3 py-2 text-xs text-gray-100 focus-visible:border-bloodred focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/60"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Filter keys or values"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" className="metal-button rounded px-3 py-2 text-xs" onClick={handleCopy} disabled={!jsonString}>
                  Copy JSON
                </button>
                <button type="button" className="metal-button rounded px-3 py-2 text-xs" onClick={handleExport} disabled={!jsonString}>
                  Export .json
                </button>
                <button type="button" className="metal-button rounded px-3 py-2 text-xs" onClick={collapseAll}>
                  Collapse all
                </button>
                <button type="button" className="metal-button rounded px-3 py-2 text-xs" onClick={expandAll}>
                  Expand all
                </button>
              </div>
            </div>
            <div className="max-h-[420px] overflow-auto rounded border border-gray-700/40 bg-black/50 p-4">
              <ul className="space-y-1 text-xs">
                {renderNode(data, [])}
              </ul>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-xs text-gray-400">Generate a motif to preview the ProjectSpec JSON.</p>
        )
      ) : (
        <p className="mt-4 text-xs text-gray-400">Preview collapsed. Expand to inspect the JSON tree.</p>
      )}
    </section>
  );
};

export default JsonPreviewPanel;
