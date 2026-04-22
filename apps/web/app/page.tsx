const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type Signal = {
  id: number;
  title: string;
  url: string;
  source_type: string;
  summary: string | null;
  published_at: string | null;
  signal_score: number | null;
  status: string;
  raw_content: string | null;
};

type SignalDetails = {
  language?: string;
  license?: string;
  latest_stars?: number;
  latest_forks?: number;
  latest_open_issues?: number;
  stars_delta?: number;
  forks_delta?: number;
  reasons?: string[];
  risks?: string[];
};

type TopSignalsResponse = {
  signals: Signal[];
};

async function getTopSignals(): Promise<{ signals: Signal[]; error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/signals/top?limit=10`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return { signals: [], error: `API returned ${response.status}` };
    }

    const payload = (await response.json()) as TopSignalsResponse;
    return { signals: payload.signals ?? [] };
  } catch (error) {
    return {
      signals: [],
      error: error instanceof Error ? error.message : "Unable to load top signals",
    };
  }
}

function parseDetails(rawContent: string | null): SignalDetails {
  if (!rawContent) {
    return {};
  }

  try {
    return JSON.parse(rawContent) as SignalDetails;
  } catch {
    return {};
  }
}

function formatNumber(value?: number) {
  if (typeof value !== "number") {
    return "-";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

function formatDelta(value?: number) {
  if (typeof value !== "number") {
    return "+0";
  }

  return value > 0 ? `+${value}` : `${value}`;
}

export default async function HomePage() {
  const { signals, error } = await getTopSignals();
  const today = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "full",
    timeZone: "Asia/Shanghai",
  }).format(new Date());

  return (
    <main className="page-shell">
      <section className="workspace-header">
        <p className="eyebrow">v0.1 Local Workspace</p>
        <h1>AI Signal Radar</h1>
        <p className="summary">
          今日工作台用于查看 Top Signals、完成飞书推送确认，并提醒你把高价值项目整理成
          Markdown 知识库文档。
        </p>
      </section>

      <section className="today-grid" aria-label="Today workspace status">
        <div className="status-panel">
          <p className="panel-label">Today</p>
          <h2>今日 AI 学习任务</h2>
          <p className="panel-copy">{today}</p>
        </div>
        <div className="status-panel">
          <p className="panel-label">Top Signals</p>
          <h2>{signals.length} 条候选</h2>
          <p className="panel-copy">优先处理评分高、风险少、文档和代码完整的项目。</p>
        </div>
        <div className="status-panel">
          <p className="panel-label">API</p>
          <h2>Local</h2>
          <p className="panel-copy break-text">{apiBaseUrl}</p>
        </div>
      </section>

      <section className="workflow-strip" aria-label="Today workflow">
        <div>
          <span className="step-dot done" />
          <strong>采集</strong>
          <p>RSS / GitHub 已进入本地库</p>
        </div>
        <div>
          <span className="step-dot done" />
          <strong>评分</strong>
          <p>按热度、可信度、相关性排序</p>
        </div>
        <div>
          <span className="step-dot current" />
          <strong>飞书推送</strong>
          <p>把今日候选推送到个人群</p>
        </div>
        <div>
          <span className="step-dot" />
          <strong>知识库跟进</strong>
          <p>选择项目并生成知识库文档</p>
        </div>
      </section>

      <section className="signals-section" aria-label="Top AI signals">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ranked Signals</p>
            <h2>Top Signals</h2>
          </div>
          {error ? <p className="load-error">后端未连接：{error}</p> : null}
        </div>

        {signals.length === 0 ? (
          <div className="empty-state">
            <h3>还没有可展示的信号</h3>
            <p>先运行采集和评分脚本，再刷新页面查看今日 Top Signals。</p>
          </div>
        ) : (
          <div className="signal-list">
            {signals.map((signal, index) => {
              const details = parseDetails(signal.raw_content);
              const reasons = details.reasons?.slice(0, 3) ?? [];
              const risks = details.risks?.slice(0, 2) ?? [];

              return (
                <article className="signal-card" key={signal.id}>
                  <div className="signal-rank">#{index + 1}</div>
                  <div className="signal-content">
                    <div className="signal-title-row">
                      <h3>
                        <a href={signal.url} target="_blank" rel="noreferrer">
                          {signal.title}
                        </a>
                      </h3>
                      <span className="score-badge">{signal.signal_score ?? 0}</span>
                    </div>
                    <p className="signal-summary">{signal.summary ?? "暂无摘要"}</p>

                    <dl className="metric-grid">
                      <div>
                        <dt>Stars</dt>
                        <dd>{formatNumber(details.latest_stars)}</dd>
                      </div>
                      <div>
                        <dt>24h/周期增长</dt>
                        <dd>{formatDelta(details.stars_delta)}</dd>
                      </div>
                      <div>
                        <dt>Forks</dt>
                        <dd>{formatNumber(details.latest_forks)}</dd>
                      </div>
                      <div>
                        <dt>语言</dt>
                        <dd>{details.language ?? "-"}</dd>
                      </div>
                      <div>
                        <dt>License</dt>
                        <dd>{details.license ?? "-"}</dd>
                      </div>
                      <div>
                        <dt>Open Issues</dt>
                        <dd>{formatNumber(details.latest_open_issues)}</dd>
                      </div>
                    </dl>

                    {reasons.length > 0 ? (
                      <ul className="reason-list" aria-label={`${signal.title} scoring reasons`}>
                        {reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : null}

                    {risks.length > 0 ? (
                      <p className="risk-text">风险：{risks.join("；")}</p>
                    ) : (
                      <p className="risk-text muted">暂无明显风险信号</p>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
