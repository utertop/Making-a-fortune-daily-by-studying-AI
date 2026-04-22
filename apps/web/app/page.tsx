const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="workspace-header">
        <p className="eyebrow">v0.1 Local Workspace</p>
        <h1>AI Signal Radar</h1>
        <p className="summary">
          Today Workspace will track AI signals, Feishu pushes, and Markdown knowledge tasks.
        </p>
      </section>

      <section className="task-panel" aria-label="Today workspace placeholder">
        <div>
          <h2>今日 AI 学习任务</h2>
          <p>Phase 1 skeleton is ready. Next step: data models and collectors.</p>
        </div>
        <dl>
          <div>
            <dt>API</dt>
            <dd>{apiBaseUrl}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>Waiting for backend health check</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
