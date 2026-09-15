import type { ReactNode } from "react";
import { useEffect } from "react";
import { X } from "./icons";

export function SidePanel({
  title,
  eyebrow,
  onClose,
  children,
}: {
  title: string;
  eyebrow?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="side-panel-overlay" onClick={onClose} />
      <div className="side-panel" role="dialog" aria-modal="true">
        <div className="side-panel-header">
          <div style={{ minWidth: 0 }}>
            {eyebrow && <div className="page-eyebrow" style={{ marginBottom: 4 }}>{eyebrow}</div>}
            <h3 style={{ fontSize: 16 }}>{title}</h3>
          </div>
          <button className="btn btn-ghost btn-icon-only" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div className="side-panel-body">{children}</div>
      </div>
    </>
  );
}
