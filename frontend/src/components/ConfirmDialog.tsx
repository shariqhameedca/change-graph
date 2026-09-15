import { useEffect } from "react";
import type { ReactNode } from "react";
import { AlertTriangle } from "./icons";

/** A centered confirmation modal for destructive actions -- distinct from
 * SidePanel (which slides in from the right for browsing/detail content).
 * Closes on Escape or backdrop click, never on accidental outside clicks
 * during a pending mutation. */
export function ConfirmDialog({
  title,
  children,
  confirmLabel = "Delete",
  danger = true,
  pending = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !pending) onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel, pending]);

  return (
    <div
      className="modal-overlay"
      onClick={() => {
        if (!pending) onCancel();
      }}
    >
      <div className="modal" role="alertdialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-icon">
            <AlertTriangle size={18} />
          </div>
          <h3 style={{ fontSize: 15.5, marginTop: 6 }}>{title}</h3>
        </div>
        <div className="modal-body">{children}</div>
        <div className="modal-footer">
          <button className="btn btn-secondary" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
          <button className={`btn ${danger ? "btn-danger-solid" : "btn-primary"}`} disabled={pending} onClick={onConfirm}>
            {pending ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
