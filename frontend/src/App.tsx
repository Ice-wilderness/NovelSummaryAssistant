import { ListTree } from "lucide-react";
import { useEffect, useMemo, useState, type ComponentType } from "react";
import { AppLayout } from "./components/layout/AppLayout";
import { useBootstrapData } from "./hooks/useBootstrapData";
import { AppStateProvider, useAppState, type ViewKey } from "./state/AppState";
import { ArticleSummaryPage } from "./views/ArticleSummaryPage";
import { ApiConfigPage } from "./views/ApiConfigPage";
import { CustomSummaryPage } from "./views/CustomSummaryPage";
import { NovelSummaryPage } from "./views/NovelSummaryPage";
import { PromptEditorPage } from "./views/PromptEditorPage";
import { SplitterPage } from "./views/SplitterPage";
import { TriggerScanPage } from "./views/TriggerScanPage";

const viewOrder: ViewKey[] = [
  "novel",
  "article",
  "custom",
  "splitter",
  "trigger_scan",
  "prompts",
  "apis"
];

const viewComponents: Record<ViewKey, ComponentType> = {
  novel: NovelSummaryPage,
  article: ArticleSummaryPage,
  custom: CustomSummaryPage,
  splitter: SplitterPage,
  trigger_scan: TriggerScanPage,
  prompts: PromptEditorPage,
  apis: ApiConfigPage
};

function WorkbenchSurface() {
  const { state } = useAppState();
  const [visitedViews, setVisitedViews] = useState<Set<ViewKey>>(
    () => new Set([state.activeView])
  );
  useBootstrapData();

  useEffect(() => {
    setVisitedViews((current) => {
      if (current.has(state.activeView)) {
        return current;
      }
      const next = new Set(current);
      next.add(state.activeView);
      return next;
    });
  }, [state.activeView]);

  const mountedViews = useMemo(
    () => viewOrder.filter((view) => visitedViews.has(view)),
    [visitedViews]
  );

  return (
    <AppLayout>
      {mountedViews.length > 0 ? (
        mountedViews.map((view) => {
          const ViewComponent = viewComponents[view];
          const isActive = state.activeView === view;
          return (
            <section
              aria-hidden={isActive ? undefined : true}
              className="workspace-view-frame"
              data-view={view}
              hidden={!isActive}
              key={view}
            >
              <ViewComponent />
            </section>
          );
        })
      ) : (
        <section className="workspace-surface">
          <div className="workspace-title">
            <ListTree size={22} />
            <h2>工作台</h2>
          </div>
          <div className="surface-grid">
            <div className="surface-panel">
              <h3>任务参数</h3>
              <span className="empty-state">等待页面接入</span>
            </div>
            <div className="surface-panel">
              <h3>运行结果</h3>
              <span className="empty-state">暂无结果</span>
            </div>
          </div>
        </section>
      )}
    </AppLayout>
  );
}

export function App() {
  return (
    <AppStateProvider>
      <WorkbenchSurface />
    </AppStateProvider>
  );
}
