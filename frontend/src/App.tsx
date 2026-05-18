import { ListTree } from "lucide-react";
import { AppLayout } from "./components/layout/AppLayout";
import { useBootstrapData } from "./hooks/useBootstrapData";
import { AppStateProvider } from "./state/AppState";
import { ArticleSummaryPage } from "./views/ArticleSummaryPage";
import { CustomSummaryPage } from "./views/CustomSummaryPage";
import { NovelSummaryPage } from "./views/NovelSummaryPage";
import { PromptEditorPage } from "./views/PromptEditorPage";
import { SplitterPage } from "./views/SplitterPage";
import { useAppState } from "./state/AppState";

function WorkbenchSurface() {
  const { state } = useAppState();
  useBootstrapData();

  if (state.activeView === "novel") {
    return (
      <AppLayout>
        <NovelSummaryPage />
      </AppLayout>
    );
  }

  if (state.activeView === "article") {
    return (
      <AppLayout>
        <ArticleSummaryPage />
      </AppLayout>
    );
  }

  if (state.activeView === "custom") {
    return (
      <AppLayout>
        <CustomSummaryPage />
      </AppLayout>
    );
  }

  if (state.activeView === "splitter") {
    return (
      <AppLayout>
        <SplitterPage />
      </AppLayout>
    );
  }

  if (state.activeView === "prompts") {
    return (
      <AppLayout>
        <PromptEditorPage />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
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
