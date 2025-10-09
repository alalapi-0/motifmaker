import React, { useState } from "react";
import clsx from "clsx";

export interface FriendlyErrorState {
  summary: string;
  details?: string | null;
  tone?: "neutral" | "negative";
}

export interface FriendlyErrorProps extends FriendlyErrorState {}

const FriendlyError: React.FC<FriendlyErrorProps> = ({ summary, details, tone = "negative" }) => {
  const [showDetails, setShowDetails] = useState(false);
  const hasDetails = Boolean(details && details.trim());

  return (
    <div
      className={clsx(
        "rounded-lg border px-4 py-3 text-sm shadow-metal",
        tone === "negative"
          ? "border-bloodred/40 bg-black/60 text-gray-100"
          : "border-gray-600/40 bg-black/40 text-gray-200"
      )}
      role="alert"
    >
      <p className="font-semibold text-white">{summary}</p>
      {hasDetails && (
        <div className="mt-2 text-xs text-gray-300">
          <button
            type="button"
            className="inline-flex items-center gap-1 text-bloodred transition hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/70 focus-visible:ring-offset-2 focus-visible:ring-offset-black"
            onClick={() => setShowDetails((value) => !value)}
            aria-expanded={showDetails}
          >
            {showDetails ? "Hide technical details" : "Show technical details"}
            <span aria-hidden="true">{showDetails ? "↑" : "↓"}</span>
          </button>
          {showDetails && (
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-black/70 p-3 text-[11px] text-gray-200">
              {details}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export default FriendlyError;
