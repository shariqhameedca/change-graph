import { useLocation } from "react-router-dom";
import { Breadcrumbs, type Crumb } from "./Breadcrumbs";
import { usePageMetaContext } from "../contexts/PageMetaContext";
import { Search } from "./icons";

function buildCrumbs(pathname: string, dynamicLabel: string | null): Crumb[] {
  const parts = pathname.split("/").filter(Boolean);

  if (parts.length === 0) return [{ label: "Overview" }];

  const [root, ...rest] = parts;

  const rootLabels: Record<string, string> = {
    regulations: "Regulations",
    rules: "Rules",
    decisions: "Decisions",
    "impact-analysis": "Impact Analysis",
    graph: "Knowledge Graph",
    simulator: "Scenario Simulator",
    evaluation: "Evaluation",
  };

  const rootLabel = rootLabels[root] ?? root;
  const rootTo = `/${root}`;

  if (rest.length === 0) {
    return [{ label: rootLabel }];
  }

  const crumbs: Crumb[] = [{ label: rootLabel, to: rootTo }];

  if (rest[0] === "new") {
    crumbs.push({ label: root === "regulations" ? "New Regulation" : "New" });
    return crumbs;
  }

  if (rest.length === 1) {
    crumbs.push({ label: dynamicLabel ?? "Detail" });
    return crumbs;
  }

  if (rest[1] === "compare") {
    crumbs.push({ label: dynamicLabel ?? "Detail", to: `${rootTo}/${rest[0]}` });
    crumbs.push({ label: "Compare Versions" });
    return crumbs;
  }

  crumbs.push({ label: dynamicLabel ?? "Detail" });
  return crumbs;
}

export function TopBar() {
  const location = useLocation();
  const meta = usePageMetaContext();
  const crumbs = buildCrumbs(location.pathname, meta?.crumbLabel ?? null);

  return (
    <div className="topbar">
      <Breadcrumbs items={crumbs} />
      <div className="topbar-right">
        <div className="topbar-search">
          <Search size={13} />
          <span>Search</span>
          <kbd>&#8984;K</kbd>
        </div>
        <span className="demo-pill">Demo environment</span>
      </div>
    </div>
  );
}
