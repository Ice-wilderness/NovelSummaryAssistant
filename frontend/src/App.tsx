import { ListTree } from "lucide-react";
import { AppLayout } from "./components/layout/AppLayout";
import { AppStateProvider } from "./state/AppState";

function WorkbenchSurface() {
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
