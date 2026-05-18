import { AppStateProvider } from "./state/AppState";

export function App() {
  return (
    <AppStateProvider>
      <main className="app-shell">
        <h1>NovelSummaryAssistant WebUI</h1>
        <p>WebUI 工作台基础已就绪。</p>
      </main>
    </AppStateProvider>
  );
}
