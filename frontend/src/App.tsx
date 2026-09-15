import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { DecisionsPage } from "./pages/DecisionsPage";
import { DecisionTracePage } from "./pages/DecisionTracePage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { ImpactAnalysisDetailPage } from "./pages/ImpactAnalysisDetailPage";
import { ImpactAnalysisListPage } from "./pages/ImpactAnalysisListPage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { NewRegulationPage } from "./pages/NewRegulationPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RegulationDetailPage } from "./pages/RegulationDetailPage";
import { RegulationsPage } from "./pages/RegulationsPage";
import { RuleDetailPage } from "./pages/RuleDetailPage";
import { RulesPage } from "./pages/RulesPage";
import { SimulatorPage } from "./pages/SimulatorPage";
import { VersionComparePage } from "./pages/VersionComparePage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/regulations" element={<RegulationsPage />} />
          <Route path="/regulations/new" element={<NewRegulationPage />} />
          <Route path="/regulations/:id" element={<RegulationDetailPage />} />
          <Route path="/regulations/:id/compare" element={<VersionComparePage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/rules/:id" element={<RuleDetailPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="/decisions/:id" element={<DecisionTracePage />} />
          <Route path="/impact-analysis" element={<ImpactAnalysisListPage />} />
          <Route path="/impact-analysis/:id" element={<ImpactAnalysisDetailPage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
