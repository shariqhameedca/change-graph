import { NavLink, Outlet, useLocation } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { PageMetaProvider } from "../contexts/PageMetaContext";
import {
  DecisionsIcon,
  EvaluationIcon,
  GraphIcon,
  ImpactIcon,
  OverviewIcon,
  RegulationsIcon,
  RulesIcon,
  SimulatorIcon,
} from "../components/icons";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true, icon: OverviewIcon },
  { to: "/regulations", label: "Regulations", icon: RegulationsIcon },
  { to: "/rules", label: "Rules", icon: RulesIcon },
  { to: "/graph", label: "Knowledge Graph", icon: GraphIcon },
  { to: "/decisions", label: "Decisions", icon: DecisionsIcon },
  { to: "/impact-analysis", label: "Impact Analysis", icon: ImpactIcon },
  { to: "/simulator", label: "Scenario Simulator", icon: SimulatorIcon },
  { to: "/evaluation", label: "Evaluation", icon: EvaluationIcon },
];

export function AppLayout() {
  const location = useLocation();

  return (
    <PageMetaProvider>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <span className="sidebar-brand-mark">CG</span>
            <span>
              Change<span className="dot">Graph</span>
            </span>
          </div>
          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  <Icon className="sidebar-nav-icon" size={16} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
          <div className="sidebar-footer">
            <span>v1.0.0 &middot; synthetic data</span>
            <span className="sidebar-env-pill">
              <span className="badge-dot" />
              Live
            </span>
          </div>
        </aside>
        <div className="app-body">
          <TopBar />
          <main className="main">
            <div className="page-enter" key={location.pathname}>
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </PageMetaProvider>
  );
}
