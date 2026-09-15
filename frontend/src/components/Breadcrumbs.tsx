import { Link } from "react-router-dom";
import { ChevronRight } from "./icons";

export interface Crumb {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
            {i > 0 && <ChevronRight size={13} />}
            {item.to && !isLast ? (
              <Link to={item.to}>{item.label}</Link>
            ) : (
              <span className={isLast ? "crumb-current" : ""}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
