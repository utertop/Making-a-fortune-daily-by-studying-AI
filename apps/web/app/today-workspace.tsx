"use client";

import { useMemo, useState } from "react";

export type TodayTask = {
  id: number;
  signal_id: number | null;
  title: string;
  task_type: string;
  status: TaskStatus;
  priority: string;
  source_url: string | null;
  target_doc_path: string | null;
  selected_at: string | null;
  started_at: string | null;
  doc_submitted_at: string | null;
  reviewed_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  document_id: number | null;
  document_title: string | null;
  document_path: string | null;
  document_summary: string | null;
  summary: string | null;
  signal_score: number | null;
  source_type: string | null;
  raw_content: string | null;
};

export type TaskStatus = "pending" | "pushed" | "selected" | "documented" | "archived" | "ignored";

export type TodaySummary = {
  total: number;
  pending: number;
  pushed: number;
  selected: number;
  documented: number;
  archived: number;
  ignored: number;
  done_count: number;
  actionable_count: number;
  is_complete: boolean;
};

export type TodayTasksPayload = {
  tasks: TodayTask[];
  summary: TodaySummary | null;
  allowed_statuses: string[];
};

type SignalDetails = {
  language?: string;
  license?: string;
  latest_stars?: number;
  latest_forks?: number;
  latest_open_issues?: number;
  stars_delta?: number;
  reasons?: string[];
  risks?: string[];
};

type TodayWorkspaceProps = {
  apiBaseUrl: string;
  initialAllowedStatuses: string[];
  initialError?: string;
  initialSummary: TodaySummary | null;
  initialTasks: TodayTask[];
};

type DocumentDraft = {
  title: string;
  path: string;
  summary: string;
  tags: string;
  confidence: string;
  created_by_agent: string;
};

const statusLabels: Record<TaskStatus, string> = {
  pending: "\u5f85\u5904\u7406",
  pushed: "\u5df2\u63a8\u9001",
  selected: "\u5df2\u9009\u62e9\u8ddf\u8fdb",
  documented: "\u5df2\u63d0\u4ea4\u6587\u6863",
  archived: "\u5df2\u5f52\u6863",
  ignored: "\u5df2\u5ffd\u7565",
};

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

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "knowledge-doc";
}

function buildSummary(tasks: TodayTask[]): TodaySummary {
  const summary: TodaySummary = {
    total: tasks.length,
    pending: 0,
    pushed: 0,
    selected: 0,
    documented: 0,
    archived: 0,
    ignored: 0,
    done_count: 0,
    actionable_count: 0,
    is_complete: false,
  };

  tasks.forEach((task) => {
    summary[task.status] += 1;
  });

  summary.done_count = summary.documented + summary.archived + summary.ignored;
  summary.actionable_count = Math.max(0, summary.total - summary.ignored);
  summary.is_complete = summary.actionable_count > 0 && summary.done_count >= summary.actionable_count;
  return summary;
}

export default function TodayWorkspace({
  apiBaseUrl,
  initialAllowedStatuses,
  initialError,
  initialSummary,
  initialTasks,
}: TodayWorkspaceProps) {
  const [tasks, setTasks] = useState(initialTasks);
  const [error, setError] = useState(initialError ?? "");
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);
  const [documentTaskId, setDocumentTaskId] = useState<number | null>(null);
  const [documentDrafts, setDocumentDrafts] = useState<Record<number, DocumentDraft>>({});
  const allowedStatuses = initialAllowedStatuses.length > 0 ? initialAllowedStatuses : Object.keys(statusLabels);
  const liveSummary = useMemo(() => buildSummary(tasks), [tasks]);
  const today = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "full",
    timeZone: "Asia/Shanghai",
  }).format(new Date());

  async function updateTaskStatus(taskId: number, status: TaskStatus) {
    setBusyTaskId(taskId);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/tasks/${taskId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const payload = (await response.json()) as { task: TodayTask };
      setTasks((currentTasks) =>
        currentTasks.map((task) => (task.id === payload.task.id ? payload.task : task)),
      );
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Unable to update task status");
    } finally {
      setBusyTaskId(null);
    }
  }

  function getDocumentDraft(task: TodayTask): DocumentDraft {
    return (
      documentDrafts[task.id] ?? {
        title: task.document_title ?? `${task.title} \u6280\u672f\u7b14\u8bb0`,
        path: task.document_path ?? task.target_doc_path ?? `knowledge-base/projects/${slugify(task.title)}-${task.id}.md`,
        summary: task.document_summary ?? task.summary ?? "",
        tags: "ai,github,signal",
        confidence: "medium",
        created_by_agent: "manual",
      }
    );
  }

  function updateDocumentDraft(taskId: number, patch: Partial<DocumentDraft>) {
    setDocumentDrafts((currentDrafts) => ({
      ...currentDrafts,
      [taskId]: {
        ...(
          currentDrafts[taskId] ?? {
            title: "",
            path: "",
            summary: "",
            tags: "",
            confidence: "medium",
            created_by_agent: "manual",
          }
        ),
        ...patch,
      },
    }));
  }

  async function submitDocument(task: TodayTask) {
    const draft = getDocumentDraft(task);
    if (!draft.title.trim() || !draft.path.trim()) {
      setError("\u6587\u6863\u6807\u9898\u548c\u8def\u5f84\u5fc5\u586b");
      return;
    }

    setBusyTaskId(task.id);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/tasks/${task.id}/document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: draft.title.trim(),
          path: draft.path.trim(),
          summary: draft.summary.trim() || null,
          tags: draft.tags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
          confidence: draft.confidence.trim() || null,
          created_by_agent: draft.created_by_agent.trim() || "manual",
        }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const payload = (await response.json()) as { task: TodayTask };
      setTasks((currentTasks) =>
        currentTasks.map((currentTask) => (currentTask.id === payload.task.id ? payload.task : currentTask)),
      );
      setDocumentTaskId(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit document");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function generateDraft(task: TodayTask) {
    setBusyTaskId(task.id);
    setError("");

    try {
      const response = await fetch(`${apiBaseUrl}/tasks/${task.id}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite: false }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const payload = (await response.json()) as { task: TodayTask; draft: { path: string } };
      setTasks((currentTasks) =>
        currentTasks.map((currentTask) => (currentTask.id === payload.task.id ? payload.task : currentTask)),
      );
      setDocumentDrafts((currentDrafts) => ({
        ...currentDrafts,
        [task.id]: {
          ...getDocumentDraft(payload.task),
          path: payload.draft.path,
        },
      }));
      setDocumentTaskId(task.id);
    } catch (draftError) {
      setError(draftError instanceof Error ? draftError.message : "Unable to generate draft");
    } finally {
      setBusyTaskId(null);
    }
  }

  return (
    <main className="page-shell">
      <section className="workspace-header">
        <p className="eyebrow">v0.1 Local Workspace</p>
        <h1>AI Signal Radar</h1>
        <p className="summary">
          {"\u4eca\u65e5\u5de5\u4f5c\u53f0\u5df2\u63a5\u5165\u672c\u5730\u4efb\u52a1\u72b6\u6001\u548c Markdown \u8349\u7a3f\u751f\u6210\uff1a\u5148\u751f\u6210\u6807\u51c6\u77e5\u8bc6\u5e93\u6a21\u677f\uff0c\u518d\u4ea4\u7ed9 Codex / Antigravity \u8865\u5168\u5185\u5bb9\u3002"}
        </p>
      </section>

      <section className="today-grid" aria-label="Today workspace status">
        <div className="status-panel">
          <p className="panel-label">Today</p>
          <h2>{"\u4eca\u65e5 AI \u5b66\u4e60\u4efb\u52a1"}</h2>
          <p className="panel-copy">{today}</p>
        </div>
        <div className="status-panel">
          <p className="panel-label">Progress</p>
          <h2>
            {liveSummary.done_count}/{liveSummary.actionable_count}
          </h2>
          <p className="panel-copy">
            {liveSummary.is_complete
              ? "\u4eca\u65e5\u4efb\u52a1\u5df2\u5b8c\u6210"
              : "\u8fd8\u6709\u4efb\u52a1\u9700\u8981\u8ddf\u8fdb"}
          </p>
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
          <strong>{"\u91c7\u96c6"}</strong>
          <p>RSS / GitHub {"\u5df2\u8fdb\u5165\u672c\u5730\u5e93"}</p>
        </div>
        <div>
          <span className="step-dot done" />
          <strong>{"\u8bc4\u5206"}</strong>
          <p>{"\u6309\u70ed\u5ea6\u3001\u53ef\u4fe1\u5ea6\u3001\u76f8\u5173\u6027\u6392\u5e8f"}</p>
        </div>
        <div>
          <span className={liveSummary.pushed > 0 ? "step-dot done" : "step-dot current"} />
          <strong>{"\u98de\u4e66\u63a8\u9001"}</strong>
          <p>{liveSummary.pushed > 0 ? "\u5df2\u8bb0\u5f55\u63a8\u9001" : "\u7b49\u5f85\u63a8\u9001\u786e\u8ba4"}</p>
        </div>
        <div>
          <span className={liveSummary.documented > 0 ? "step-dot done" : "step-dot"} />
          <strong>{"\u77e5\u8bc6\u5e93\u8ddf\u8fdb"}</strong>
          <p>{liveSummary.documented > 0 ? "\u5df2\u63d0\u4ea4\u6587\u6863" : "\u9009\u62e9\u9879\u76ee\u5e76\u751f\u6210\u6587\u6863"}</p>
        </div>
      </section>

      <section className="task-summary-grid" aria-label="Task counts">
        <div>
          <span>{liveSummary.total}</span>
          <p>{"\u5019\u9009"}</p>
        </div>
        <div>
          <span>{liveSummary.pending}</span>
          <p>{"\u5f85\u5904\u7406"}</p>
        </div>
        <div>
          <span>{liveSummary.selected}</span>
          <p>{"\u8ddf\u8fdb\u4e2d"}</p>
        </div>
        <div>
          <span>{liveSummary.documented}</span>
          <p>{"\u5df2\u6587\u6863\u5316"}</p>
        </div>
      </section>

      <section className="signals-section" aria-label="Today learning tasks">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Today Tasks</p>
            <h2>{"\u672c\u5730\u4efb\u52a1\u72b6\u6001"}</h2>
          </div>
          {error ? <p className="load-error">{"\u540e\u7aef\u9519\u8bef\uff1a"}{error}</p> : null}
        </div>

        {tasks.length === 0 ? (
          <div className="empty-state">
            <h3>{"\u8fd8\u6ca1\u6709\u4eca\u65e5\u4efb\u52a1"}</h3>
            <p>{"\u5148\u8fd0\u884c\u91c7\u96c6\u548c\u8bc4\u5206\u811a\u672c\uff0c\u518d\u5237\u65b0\u9875\u9762\u3002"}</p>
          </div>
        ) : (
          <div className="signal-list">
            {tasks.map((task, index) => {
              const details = parseDetails(task.raw_content);
              const reasons = details.reasons?.slice(0, 3) ?? [];
              const risks = details.risks?.slice(0, 2) ?? [];
              const isBusy = busyTaskId === task.id;
              const allowed = new Set(allowedStatuses);

              return (
                <article className="signal-card" key={task.id}>
                  <div className="signal-rank">#{index + 1}</div>
                  <div className="signal-content">
                    <div className="signal-title-row">
                      <h3>
                        <a href={task.source_url ?? "#"} target="_blank" rel="noreferrer">
                          {task.title}
                        </a>
                      </h3>
                      <span className={`status-badge status-${task.status}`}>
                        {statusLabels[task.status] ?? task.status}
                      </span>
                    </div>

                    <p className="signal-summary">{task.summary ?? "\u6682\u65e0\u6458\u8981"}</p>

                    <dl className="metric-grid">
                      <div>
                        <dt>Score</dt>
                        <dd>{task.signal_score ?? 0}</dd>
                      </div>
                      <div>
                        <dt>Stars</dt>
                        <dd>{formatNumber(details.latest_stars)}</dd>
                      </div>
                      <div>
                        <dt>Delta</dt>
                        <dd>{formatDelta(details.stars_delta)}</dd>
                      </div>
                      <div>
                        <dt>Forks</dt>
                        <dd>{formatNumber(details.latest_forks)}</dd>
                      </div>
                      <div>
                        <dt>Language</dt>
                        <dd>{details.language ?? "-"}</dd>
                      </div>
                      <div>
                        <dt>License</dt>
                        <dd>{details.license ?? "-"}</dd>
                      </div>
                    </dl>

                    {reasons.length > 0 ? (
                      <ul className="reason-list" aria-label={`${task.title} scoring reasons`}>
                        {reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : null}

                    {risks.length > 0 ? (
                      <p className="risk-text">{"\u98ce\u9669\uff1a"}{risks.join("; ")}</p>
                    ) : (
                      <p className="risk-text muted">{"\u6682\u65e0\u660e\u663e\u98ce\u9669\u4fe1\u53f7"}</p>
                    )}

                    {task.document_path ?? task.target_doc_path ? (
                      <p className="doc-path">
                        Markdown: {task.document_title ? `${task.document_title} - ` : ""}
                        {task.document_path ?? task.target_doc_path}
                      </p>
                    ) : null}

                    {documentTaskId === task.id ? (
                      <div className="document-form" aria-label={`${task.title} document form`}>
                        <label>
                          <span>{"\u6587\u6863\u6807\u9898"}</span>
                          <input
                            onChange={(event) => updateDocumentDraft(task.id, { title: event.target.value })}
                            type="text"
                            value={getDocumentDraft(task).title}
                          />
                        </label>
                        <label>
                          <span>{"Markdown \u8def\u5f84"}</span>
                          <input
                            onChange={(event) => updateDocumentDraft(task.id, { path: event.target.value })}
                            placeholder="knowledge/projects/example.md"
                            type="text"
                            value={getDocumentDraft(task).path}
                          />
                        </label>
                        <label>
                          <span>{"\u6458\u8981"}</span>
                          <textarea
                            onChange={(event) => updateDocumentDraft(task.id, { summary: event.target.value })}
                            rows={3}
                            value={getDocumentDraft(task).summary}
                          />
                        </label>
                        <div className="document-form-grid">
                          <label>
                            <span>Tags</span>
                            <input
                              onChange={(event) => updateDocumentDraft(task.id, { tags: event.target.value })}
                              type="text"
                              value={getDocumentDraft(task).tags}
                            />
                          </label>
                          <label>
                            <span>Confidence</span>
                            <select
                              onChange={(event) => updateDocumentDraft(task.id, { confidence: event.target.value })}
                              value={getDocumentDraft(task).confidence}
                            >
                              <option value="high">high</option>
                              <option value="medium">medium</option>
                              <option value="low">low</option>
                            </select>
                          </label>
                        </div>
                      </div>
                    ) : null}

                    <div className="task-actions" aria-label={`${task.title} task actions`}>
                      {allowed.has("pushed") ? (
                        <button
                          disabled={isBusy || task.status === "pushed"}
                          onClick={() => updateTaskStatus(task.id, "pushed")}
                          type="button"
                        >
                          {"\u6807\u8bb0\u5df2\u63a8\u9001"}
                        </button>
                      ) : null}
                      {allowed.has("selected") ? (
                        <button
                          disabled={isBusy || task.status === "selected"}
                          onClick={() => updateTaskStatus(task.id, "selected")}
                          type="button"
                        >
                          {"\u9009\u62e9\u8ddf\u8fdb"}
                        </button>
                      ) : null}
                      {allowed.has("documented") ? (
                        <button
                          disabled={isBusy}
                          onClick={() => generateDraft(task)}
                          type="button"
                        >
                          {"\u751f\u6210 Markdown \u8349\u7a3f"}
                        </button>
                      ) : null}
                      {allowed.has("documented") ? (
                        <button
                          disabled={isBusy}
                          onClick={() => setDocumentTaskId(documentTaskId === task.id ? null : task.id)}
                          type="button"
                        >
                          {"\u63d0\u4ea4\u6587\u6863"}
                        </button>
                      ) : null}
                      {documentTaskId === task.id ? (
                        <button
                          disabled={isBusy}
                          onClick={() => submitDocument(task)}
                          type="button"
                        >
                          {"\u4fdd\u5b58\u6587\u6863\u8bb0\u5f55"}
                        </button>
                      ) : null}
                      {allowed.has("ignored") ? (
                        <button
                          disabled={isBusy || task.status === "ignored"}
                          onClick={() => updateTaskStatus(task.id, "ignored")}
                          type="button"
                        >
                          {"\u5ffd\u7565"}
                        </button>
                      ) : null}
                      {allowed.has("archived") ? (
                        <button
                          disabled={isBusy || task.status === "archived"}
                          onClick={() => updateTaskStatus(task.id, "archived")}
                          type="button"
                        >
                          {"\u5f52\u6863"}
                        </button>
                      ) : null}
                    </div>
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
