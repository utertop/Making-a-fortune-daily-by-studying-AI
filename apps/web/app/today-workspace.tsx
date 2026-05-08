"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

export type TaskStatus =
  | "pending"
  | "pushed"
  | "selected"
  | "draft_created"
  | "review_pending"
  | "documented"
  | "archived"
  | "ignored";

export type TodayTask = {
  id: number;
  signal_id: number | null;
  title: string;
  task_type: string;
  status: TaskStatus;
  priority: string;
  source_url: string | null;
  target_doc_path: string | null;
  generated_prompt: string | null;
  draft_created_at: string | null;
  draft_initial_hash: string | null;
  last_detected_hash: string | null;
  last_detected_at: string | null;
  review_pending_at: string | null;
  ignored_reason: string | null;
  detection_status: string | null;
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

export type TodaySummary = {
  total: number;
  pending: number;
  pushed: number;
  selected: number;
  draft_created: number;
  review_pending: number;
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
  docs_url?: string;
  docs?: string;
  documentation_url?: string;
  homepage?: string;
  website?: string;
  changelog_url?: string;
  release_url?: string;
  blog_url?: string;
  extra_links?: string[];
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

type PromptDraft = {
  repoUrl: string;
  docsUrl: string;
  extraUrl: string;
  targetFile: string;
};

const DOCS_NOT_FOUND = "未发现文档链接，请先从 README 或仓库主页确认";
const EXTRA_LINKS_NOT_FOUND = "暂无补充链接";

const statusLabels: Record<TaskStatus, string> = {
  pending: "待处理",
  pushed: "已推送",
  selected: "已选择",
  draft_created: "草稿已生成",
  review_pending: "待审核",
  documented: "已归档",
  archived: "已收起",
  ignored: "已跳过",
};

const ignoreReasonOptions = ["相关性不足", "重复主题", "暂不值得深挖", "资料不足", "今天先跳过"];

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

function formatDateTime(value: string | null) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Shanghai",
  }).format(date);
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
    draft_created: 0,
    review_pending: 0,
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

async function parseApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    // Keep the fallback below.
  }
  return `API 返回 ${response.status}`;
}

function firstNonEmpty(values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function buildPromptDraft(task: TodayTask): PromptDraft {
  const details = parseDetails(task.raw_content);
  return {
    repoUrl: task.source_url?.trim() || "<repo_url>",
    docsUrl:
      firstNonEmpty([details.docs_url, details.documentation_url, details.docs, details.homepage, details.website]) ??
      DOCS_NOT_FOUND,
    extraUrl:
      firstNonEmpty([details.release_url, details.changelog_url, details.blog_url, details.extra_links?.[0]]) ??
      EXTRA_LINKS_NOT_FOUND,
    targetFile: task.target_doc_path ?? task.document_path ?? `<knowledge-base path for task ${task.id}>`,
  };
}

function buildDeepResearchPrompt(task: TodayTask, promptDraft?: PromptDraft) {
  const draft = promptDraft ?? buildPromptDraft(task);
  const details = parseDetails(task.raw_content);
  const reasons = details.reasons?.length ? details.reasons.map((reason) => `- ${reason}`).join("\n") : "- 暂无评分原因";
  const risks = details.risks?.length ? details.risks.map((risk) => `- ${risk}`).join("\n") : "- 暂无明显风险";

  return [
    "请使用 $deep-project-dossier 技能，为下面项目写一份深度项目知识档案。",
    "",
    `GitHub Repo: ${draft.repoUrl}`,
    `Docs: ${draft.docsUrl}`,
    `Extra Links: ${draft.extraUrl}`,
    `Target File: ${draft.targetFile}`,
    "",
    `项目名称: ${task.title}`,
    `一句话摘要: ${task.summary ?? "请根据资料补全"}`,
    "",
    "当前评分原因:",
    reasons,
    "",
    "已知风险:",
    risks,
    "",
    "写作要求:",
    "1. 先核对 README、docs、examples、releases/changelog 和许可证。",
    "2. 区分事实、推断和待确认信息，不要把营销描述当成事实。",
    "3. 输出结构化 Markdown，覆盖解决的问题、核心机制、适用场景、限制风险和学习建议。",
    "4. 保留来源链接，必要时补充 Mermaid 图，但不要为了装饰而加图。",
  ].join("\n");
}

function buildHeroContent(summary: TodaySummary, completionPercent: number) {
  if (summary.is_complete && summary.actionable_count > 0) {
    return {
      eyebrow: "TODAY COMPLETE",
      title: "今天的知识雷达已经收工",
      summary: "候选信号已经处理完。现在可以复盘文档质量，或者把精力留给明天的新信号。",
      chips: [`已处理 ${summary.done_count}/${summary.actionable_count}`, "可归档", `完成度 ${completionPercent}%`],
    };
  }

  if (summary.review_pending > 0) {
    return {
      eyebrow: "FOCUS: REVIEW",
      title: `${summary.review_pending} 篇草稿等待确认`,
      summary: "优先检查已经写完的 Markdown，把有价值的内容确认入库，今天的闭环就会轻很多。",
      chips: [`待审核 ${summary.review_pending}`, `已有草稿 ${summary.draft_created}`, `完成度 ${completionPercent}%`],
    };
  }

  if (summary.draft_created > 0) {
    return {
      eyebrow: "FOCUS: DRAFTS",
      title: `${summary.draft_created} 个项目已有 Markdown 草稿`,
      summary: "从草稿开始深挖会更快。打开 Prompt，补齐资料来源，再把文件写到知识库。",
      chips: [`草稿 ${summary.draft_created}`, `待审核 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
    };
  }

  if (summary.selected > 0) {
    return {
      eyebrow: "FOCUS: FOLLOW UP",
      title: `${summary.selected} 个信号已经被选中`,
      summary: "下一步是生成 Markdown 草稿，或复制深挖 Prompt 交给 Codex / Antigravity 继续研究。",
      chips: [`已选择 ${summary.selected}`, `待审核 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
    };
  }

  return {
    eyebrow: "V0.1 LOCAL WORKSPACE",
    title: "AI Signal Radar",
    summary: "从 GitHub 与 RSS 中筛选值得学习的 AI 信号，选择少量项目深挖，并沉淀为本地 Markdown 知识库。",
    chips: [`待处理 ${summary.pending + summary.pushed}`, `待审核 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
  };
}

function nextStepLabel(task: TodayTask) {
  if (task.status === "pending") {
    return "先推送或选择";
  }
  if (task.status === "pushed") {
    return "选择是否深挖";
  }
  if (task.status === "selected") {
    return "生成草稿";
  }
  if (task.status === "draft_created") {
    return "编辑 Markdown";
  }
  if (task.status === "review_pending") {
    return "确认归档";
  }
  if (task.status === "documented") {
    return "已完成";
  }
  if (task.status === "ignored") {
    return "已跳过";
  }
  return "已归档";
}

function buildDefaultDocumentDraft(task: TodayTask, archivePath: string): DocumentDraft {
  const details = parseDetails(task.raw_content);
  const path = task.target_doc_path ?? task.document_path ?? `${archivePath}${slugify(task.title)}-${task.id}.md`;
  const tags = ["ai", task.source_type ?? "signal", details.language?.toLowerCase()].filter(Boolean).join(", ");

  return {
    title: task.document_title ?? `${task.title} 深度项目知识档案`,
    path,
    summary: task.document_summary ?? task.summary ?? "",
    tags,
    confidence: "medium",
    created_by_agent: "codex",
  };
}

export default function TodayWorkspace({
  apiBaseUrl,
  initialAllowedStatuses,
  initialError,
  initialSummary,
  initialTasks,
}: TodayWorkspaceProps) {
  const [tasks, setTasks] = useState(initialTasks);
  const [allowedStatuses, setAllowedStatuses] = useState(initialAllowedStatuses);
  const [error, setError] = useState(initialError ?? "");
  const [notice, setNotice] = useState("");
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);
  const [documentTaskId, setDocumentTaskId] = useState<number | null>(null);
  const [promptPreviewTaskId, setPromptPreviewTaskId] = useState<number | null>(null);
  const [promptDrafts, setPromptDrafts] = useState<Record<number, PromptDraft>>({});
  const [documentDrafts, setDocumentDrafts] = useState<Record<number, DocumentDraft>>({});
  const [ignoreReasons, setIgnoreReasons] = useState<Record<number, string>>({});
  const [currentTime, setCurrentTime] = useState(new Date());
  const [runtimeApiBaseUrl] = useState(apiBaseUrl);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const liveSummary = useMemo(() => buildSummary(tasks), [tasks]);
  const summary = initialSummary && tasks.length === initialTasks.length ? liveSummary : liveSummary;
  const completionPercent = summary.actionable_count ? Math.round((summary.done_count / summary.actionable_count) * 100) : 0;
  const allowedStatusSet = useMemo(() => new Set(allowedStatuses), [allowedStatuses]);
  const hero = buildHeroContent(summary, completionPercent);
  const today = new Intl.DateTimeFormat("zh-CN", { dateStyle: "full", timeZone: "Asia/Shanghai" }).format(currentTime);
  const clockText = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Shanghai",
  }).format(currentTime);
  const archiveDate = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Shanghai",
    year: "numeric",
  }).format(currentTime);
  const [archiveYear, archiveMonth] = archiveDate.split("-");
  const archivePath = `knowledge-base/daily/${archiveYear}/${archiveMonth}/${archiveDate}/`;

  const applyTaskUpdate = useCallback((updatedTask: TodayTask) => {
    setTasks((currentTasks) => currentTasks.map((task) => (task.id === updatedTask.id ? updatedTask : task)));
  }, []);

  const refreshTodayTasks = useCallback(
    async (silent = false) => {
      if (!silent) {
        setIsRefreshing(true);
        setError("");
      }

      try {
        const response = await fetch(`${runtimeApiBaseUrl}/tasks/today?limit=10`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }

        const payload = (await response.json()) as TodayTasksPayload;
        setTasks(payload.tasks);
        setAllowedStatuses(payload.allowed_statuses);
        if (!silent) {
          setNotice("今日任务已刷新。");
        }
      } catch (refreshError) {
        if (!silent) {
          setError(refreshError instanceof Error ? refreshError.message : "刷新今日任务失败。");
          setNotice("");
        }
      } finally {
        if (!silent) {
          setIsRefreshing(false);
        }
      }
    },
    [runtimeApiBaseUrl],
  );

  const runBulkDetection = useCallback(
    async (silent = false) => {
      const detectableCount = tasks.filter(
        (task) => ["selected", "draft_created", "review_pending"].includes(task.status) && task.target_doc_path,
      ).length;
      if (detectableCount === 0) {
        return;
      }

      try {
        const response = await fetch(`${runtimeApiBaseUrl}/tasks/detect-documents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ limit: 50 }),
        });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }

        const payload = (await response.json()) as { checked: number; changed: number; tasks: TodayTask[] };
        if (payload.tasks.length > 0) {
          setTasks((currentTasks) => currentTasks.map((task) => payload.tasks.find((item) => item.id === task.id) ?? task));
        }
        if (!silent && payload.changed > 0) {
          setNotice(`发现 ${payload.changed} 个已更新的 Markdown，等待确认。`);
        }
      } catch (detectError) {
        if (!silent) {
          setError(detectError instanceof Error ? detectError.message : "检测 Markdown 失败。");
        }
      }
    },
    [runtimeApiBaseUrl, tasks],
  );

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => void refreshTodayTasks(true), 60000);
    return () => window.clearInterval(timer);
  }, [refreshTodayTasks]);

  useEffect(() => {
    const timer = window.setInterval(() => void runBulkDetection(true), 45000);
    return () => window.clearInterval(timer);
  }, [runBulkDetection]);

  async function copyText(value: string, successMessage: string) {
    try {
      await navigator.clipboard.writeText(value);
      setNotice(successMessage);
      setError("");
    } catch {
      setError("复制失败，请手动选择文本。");
    }
  }

  async function updateTaskStatus(task: TodayTask, status: TaskStatus, extra?: { ignored_reason?: string }) {
    setBusyTaskId(task.id);
    setError("");
    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          target_doc_path: task.target_doc_path,
          ignored_reason: extra?.ignored_reason,
        }),
      });
      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask };
      applyTaskUpdate(payload.task);
      setNotice(`${task.title} 已更新为「${statusLabels[status]}」。`);
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "更新任务状态失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function generateDraft(task: TodayTask) {
    setBusyTaskId(task.id);
    setError("");
    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite: false }),
      });
      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { draft: { path: string }; task: TodayTask };
      applyTaskUpdate(payload.task);
      setNotice(`Markdown 草稿已生成：${payload.draft.path}`);
    } catch (draftError) {
      setError(draftError instanceof Error ? draftError.message : "生成 Markdown 草稿失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function detectTaskDocument(task: TodayTask) {
    setBusyTaskId(task.id);
    setError("");
    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/detect-document`, { method: "POST" });
      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask; changed: boolean; reason: string };
      applyTaskUpdate(payload.task);
      setNotice(payload.changed ? "检测到 Markdown 已更新，等待确认归档。" : "还没有发现新的 Markdown 更新。");
    } catch (detectError) {
      setError(detectError instanceof Error ? detectError.message : "检测 Markdown 失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  function updateDocumentDraft(taskId: number, patch: Partial<DocumentDraft>) {
    setDocumentDrafts((currentDrafts) => ({
      ...currentDrafts,
      [taskId]: { ...currentDrafts[taskId], ...patch },
    }));
  }

  function updatePromptDraft(task: TodayTask, patch: Partial<PromptDraft>) {
    setPromptDrafts((currentDrafts) => ({
      ...currentDrafts,
      [task.id]: { ...(currentDrafts[task.id] ?? buildPromptDraft(task)), ...patch },
    }));
  }

  async function submitDocument(task: TodayTask) {
    const draft = documentDrafts[task.id] ?? buildDefaultDocumentDraft(task, archivePath);
    setBusyTaskId(task.id);
    setError("");
    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: draft.title,
          path: draft.path,
          summary: draft.summary,
          tags: draft.tags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
          confidence: draft.confidence,
          created_by_agent: draft.created_by_agent,
        }),
      });
      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask };
      applyTaskUpdate(payload.task);
      setDocumentTaskId(null);
      setNotice(`${task.title} 已确认归档。`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "确认归档失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function copyDeepResearchPrompt(task: TodayTask) {
    const promptDraft = promptDrafts[task.id] ?? buildPromptDraft(task);
    await copyText(buildDeepResearchPrompt(task, promptDraft), "深挖 Prompt 已复制。");
  }

  return (
    <main className="page-shell">
      <header className="workspace-header">
        <div className="workspace-hero">
          <div className="workspace-hero-copy">
            <p className="eyebrow">{hero.eyebrow}</p>
            <h1 className="brand-title">{hero.title}</h1>
            <p className="summary">{hero.summary}</p>
          </div>
          <div className="workspace-hero-stats">
            <div className="hero-stat-card hero-stat-card-strong">
              <span>{completionPercent}%</span>
              <strong>今日完成度</strong>
              <p>{hero.chips.join(" / ")}</p>
              <div className="hero-progress">
                <div className="hero-progress-track">
                  <div className="hero-progress-fill" style={{ width: `${completionPercent}%` }} />
                </div>
                <div className="hero-progress-caption">
                  <span>{summary.done_count} 已处理</span>
                  <strong>{summary.actionable_count} 个有效任务</strong>
                </div>
              </div>
            </div>
            <div className="hero-stat-card">
              <span>{summary.review_pending}</span>
              <strong>待审核文档</strong>
              <p>优先确认这些内容，闭环最快。</p>
            </div>
          </div>
        </div>
      </header>

      <section className="attention-strip" aria-label="今日重点">
        <div className="attention-card highlight">
          <strong>今天</strong>
          <p>{today}</p>
        </div>
        <div className="attention-card">
          <strong>知识库路径</strong>
          <p className="break-text">{archivePath}</p>
        </div>
        <div className="attention-card action-card">
          <strong>当前时间</strong>
          <p>{clockText}</p>
          <button disabled={isRefreshing} onClick={() => void refreshTodayTasks()} type="button">
            {isRefreshing ? "刷新中..." : "刷新任务"}
          </button>
        </div>
      </section>

      {notice ? <div className="notice-banner">{notice}</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="workflow-strip" aria-label="工作流">
        <div>
          <strong>
            <span className="step-dot done" />
            发现信号
          </strong>
          <p>采集 GitHub / RSS，形成候选列表。</p>
        </div>
        <div>
          <strong>
            <span className="step-dot current" />
            选择深挖
          </strong>
          <p>从高分信号里挑 1 到 3 个项目。</p>
        </div>
        <div>
          <strong>
            <span className="step-dot" />
            写成 Markdown
          </strong>
          <p>生成草稿，复制 Prompt，补齐事实来源。</p>
        </div>
        <div>
          <strong>
            <span className="step-dot" />
            确认归档
          </strong>
          <p>审核后写入本地知识库。</p>
        </div>
      </section>

      <section className="signals-section">
        <div className="section-heading">
          <div>
            <p className="panel-label">Top Signals</p>
            <h2>今日候选信号</h2>
          </div>
          {initialError ? <p className="load-error">{initialError}</p> : null}
        </div>

        <div className="task-summary-grid" aria-label="任务统计">
          <div className="summary-card-hot">
            <span>{summary.total}</span>
            <p>全部</p>
          </div>
          <div>
            <span>{summary.pending + summary.pushed}</span>
            <p>待选择</p>
          </div>
          <div>
            <span>{summary.selected}</span>
            <p>已选择</p>
          </div>
          <div>
            <span>{summary.draft_created}</span>
            <p>已有草稿</p>
          </div>
          <div>
            <span>{summary.review_pending}</span>
            <p>待审核</p>
          </div>
          <div>
            <span>{summary.documented}</span>
            <p>已归档</p>
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="empty-state">
            <h2>还没有今日任务</h2>
            <p>先运行 daily flow 或刷新任务。API 可用后，这里会显示今日 Top Signals。</p>
          </div>
        ) : (
          <div className="signal-list">
            {tasks.map((task, index) => {
              const details = parseDetails(task.raw_content);
              const reasons = details.reasons ?? [];
              const risks = details.risks ?? [];
              const promptDraft = promptDrafts[task.id] ?? buildPromptDraft(task);
              const deepPromptText = buildDeepResearchPrompt(task, promptDraft);
              const draft = documentDrafts[task.id] ?? buildDefaultDocumentDraft(task, archivePath);
              const isBusy = busyTaskId === task.id;
              const isPromptPreviewOpen = promptPreviewTaskId === task.id;
              const canPush = allowedStatusSet.has("pushed") && task.status === "pending";
              const canSelect = allowedStatusSet.has("selected") && (task.status === "pending" || task.status === "pushed");
              const canCreateDraft =
                task.status === "selected" || task.status === "draft_created" || task.status === "review_pending";
              const canDetect =
                Boolean(task.target_doc_path) && !["documented", "archived", "ignored"].includes(task.status);
              const canConfirmDocument =
                Boolean(task.target_doc_path) && !["documented", "archived", "ignored"].includes(task.status);
              const canPreviewPrompt =
                Boolean(task.target_doc_path) &&
                (task.status === "selected" || task.status === "draft_created" || task.status === "review_pending");
              const canIgnore =
                allowedStatusSet.has("ignored") && !["documented", "archived", "ignored"].includes(task.status);
              const canArchive = allowedStatusSet.has("archived") && (task.status === "documented" || task.status === "ignored");
              const ignoreReason = ignoreReasons[task.id] ?? "相关性不足";
              const isWorkspaceOpen = isPromptPreviewOpen || documentTaskId === task.id;
              const isTerminalCard = task.status === "documented" || task.status === "archived" || task.status === "ignored";
              const progressHint = task.last_detected_at ? `最近检测：${formatDateTime(task.last_detected_at)}` : "";

              return (
                <article
                  className={`signal-card ${isWorkspaceOpen ? "signal-card-expanded" : "signal-card-collapsed"} ${
                    isTerminalCard ? "signal-card-terminal" : "signal-card-active"
                  }`}
                  key={task.id}
                >
                  <div className="signal-rank">{index + 1}</div>
                  <div className="signal-content">
                    <div className="signal-title-row">
                      <div className="signal-title-group">
                        <h3>
                          <a href={task.source_url ?? "#"} target="_blank" rel="noreferrer">
                            {task.title}
                          </a>
                        </h3>
                        <p className="signal-summary">{task.summary ?? "暂无摘要"}</p>
                      </div>
                      <div className="signal-status-stack">
                        <span className={`status-badge status-${task.status}`}>{statusLabels[task.status] ?? task.status}</span>
                        <div className="next-step-chip">{nextStepLabel(task)}</div>
                      </div>
                    </div>

                    <dl className="metric-grid">
                      <div className="metric-card metric-card-score">
                        <dt>Score</dt>
                        <dd>{task.signal_score ?? 0}</dd>
                      </div>
                      <div>
                        <dt>Stars</dt>
                        <dd>{formatNumber(details.latest_stars)}</dd>
                      </div>
                      <div className="metric-card metric-card-delta">
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
                      <ul className="reason-list" aria-label={`${task.title} 评分原因`}>
                        {reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : null}

                    <div className="signal-insight-strip">
                      {risks.length > 0 ? (
                        <p className="risk-text">风险：{risks.join(" / ")}</p>
                      ) : (
                        <p className="risk-text muted">暂未发现明显风险。</p>
                      )}

                      {progressHint ? <div className="task-hint">{progressHint}</div> : null}

                      {task.document_path ?? task.target_doc_path ? (
                        <div className="doc-path-row">
                          <p className="doc-path">
                            Markdown：{task.document_title ? `${task.document_title} - ` : ""}
                            {task.document_path ?? task.target_doc_path}
                          </p>
                          <button
                            onClick={() => void copyText(task.document_path ?? task.target_doc_path ?? "", "Markdown 路径已复制。")}
                            type="button"
                          >
                            复制路径
                          </button>
                        </div>
                      ) : null}
                    </div>

                    <div className={`signal-workspace-shell ${isWorkspaceOpen ? "is-open" : "is-closed"}`}>
                      <div className="signal-workspace-summary">
                        <div>
                          <span className="signal-workspace-kicker">Workspace</span>
                          <strong>{isWorkspaceOpen ? "正在处理这个信号" : "打开 Prompt 或归档表单后继续处理"}</strong>
                        </div>
                        <span className="signal-workspace-state">{isWorkspaceOpen ? "展开" : "待操作"}</span>
                      </div>

                      {isWorkspaceOpen ? (
                        <div className="signal-workspace">
                          {isPromptPreviewOpen ? (
                            <div className="prompt-preview-panel">
                              <div className="panel-kicker">Deep Prompt</div>
                              <div className="prompt-preview-header">
                                <div>
                                  <strong>深挖 Prompt 预览</strong>
                                  <p>复制后交给 Codex / Antigravity，用于生成或完善项目知识档案。</p>
                                </div>
                                <div className="prompt-preview-actions">
                                  <button onClick={() => void copyDeepResearchPrompt(task)} type="button">
                                    复制 Prompt
                                  </button>
                                  <button onClick={() => void copyText(promptDraft.targetFile, "目标路径已复制。")} type="button">
                                    复制路径
                                  </button>
                                  <button onClick={() => setPromptPreviewTaskId(null)} type="button">
                                    收起
                                  </button>
                                </div>
                              </div>
                              <div className="prompt-source-grid">
                                <div className="prompt-source-card">
                                  <span>Repo</span>
                                  <strong>{promptDraft.repoUrl}</strong>
                                </div>
                                <div className="prompt-source-card">
                                  <span>Docs</span>
                                  <strong>{promptDraft.docsUrl}</strong>
                                </div>
                                <div className="prompt-source-card">
                                  <span>Extra Links</span>
                                  <strong>{promptDraft.extraUrl}</strong>
                                </div>
                                <div className="prompt-source-card">
                                  <span>Target File</span>
                                  <strong>{promptDraft.targetFile}</strong>
                                </div>
                              </div>
                              <div className="prompt-edit-grid">
                                <label>
                                  <span>Docs</span>
                                  <input
                                    onChange={(event) => updatePromptDraft(task, { docsUrl: event.target.value })}
                                    type="text"
                                    value={promptDraft.docsUrl}
                                  />
                                </label>
                                <label>
                                  <span>Extra Links</span>
                                  <input
                                    onChange={(event) => updatePromptDraft(task, { extraUrl: event.target.value })}
                                    type="text"
                                    value={promptDraft.extraUrl}
                                  />
                                </label>
                              </div>
                              <div className="prompt-console">
                                <div className="prompt-console-bar">
                                  <span>Research Prompt</span>
                                  <small>可直接复制</small>
                                </div>
                                <pre>{deepPromptText}</pre>
                              </div>
                            </div>
                          ) : null}

                          {documentTaskId === task.id ? (
                            <div className="document-form" aria-label={`${task.title} document form`}>
                              <div className="panel-kicker">Submit Record</div>
                              <label>
                                <span>文档标题</span>
                                <input
                                  onChange={(event) => updateDocumentDraft(task.id, { title: event.target.value })}
                                  type="text"
                                  value={draft.title}
                                />
                              </label>
                              <label>
                                <span>Markdown 路径</span>
                                <input
                                  onChange={(event) => updateDocumentDraft(task.id, { path: event.target.value })}
                                  placeholder="knowledge-base/daily/2026/04/2026-04-23/example.md"
                                  type="text"
                                  value={draft.path}
                                />
                              </label>
                              <label>
                                <span>摘要</span>
                                <textarea
                                  onChange={(event) => updateDocumentDraft(task.id, { summary: event.target.value })}
                                  rows={3}
                                  value={draft.summary}
                                />
                              </label>
                              <div className="document-form-grid">
                                <label>
                                  <span>Tags</span>
                                  <input
                                    onChange={(event) => updateDocumentDraft(task.id, { tags: event.target.value })}
                                    type="text"
                                    value={draft.tags}
                                  />
                                </label>
                                <label>
                                  <span>Confidence</span>
                                  <select
                                    onChange={(event) => updateDocumentDraft(task.id, { confidence: event.target.value })}
                                    value={draft.confidence}
                                  >
                                    <option value="high">high</option>
                                    <option value="medium">medium</option>
                                    <option value="low">low</option>
                                  </select>
                                </label>
                              </div>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>

                    {canIgnore ? (
                      <div className="inline-select-row">
                        <label className="inline-select">
                          <span>跳过原因</span>
                          <select
                            onChange={(event) =>
                              setIgnoreReasons((currentReasons) => ({ ...currentReasons, [task.id]: event.target.value }))
                            }
                            value={ignoreReason}
                          >
                            {ignoreReasonOptions.map((reason) => (
                              <option key={reason} value={reason}>
                                {reason}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    ) : null}

                    <div className="task-actions" aria-label={`${task.title} task actions`}>
                      {canPush ? (
                        <button className="button-secondary" disabled={isBusy} onClick={() => void updateTaskStatus(task, "pushed")} type="button">
                          标记已推送
                        </button>
                      ) : null}
                      {canSelect ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void updateTaskStatus(task, "selected")} type="button">
                          选择深挖
                        </button>
                      ) : null}
                      {canCreateDraft ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void generateDraft(task)} type="button">
                          生成 Markdown 草稿
                        </button>
                      ) : null}
                      {canPreviewPrompt ? (
                        <button
                          className="button-primary"
                          disabled={isBusy}
                          onClick={() => {
                            setPromptDrafts((currentDrafts) => ({
                              ...currentDrafts,
                              [task.id]: currentDrafts[task.id] ?? buildPromptDraft(task),
                            }));
                            setPromptPreviewTaskId(isPromptPreviewOpen ? null : task.id);
                          }}
                          type="button"
                        >
                          深挖 Prompt
                        </button>
                      ) : null}
                      {canDetect ? (
                        <button className="button-secondary" disabled={isBusy} onClick={() => void detectTaskDocument(task)} type="button">
                          检测 Markdown
                        </button>
                      ) : null}
                      {canConfirmDocument ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void submitDocument(task)} type="button">
                          确认归档
                        </button>
                      ) : null}
                      {canConfirmDocument ? (
                        <button
                          className="button-secondary"
                          disabled={isBusy}
                          onClick={() => setDocumentTaskId(documentTaskId === task.id ? null : task.id)}
                          type="button"
                        >
                          {documentTaskId === task.id ? "收起归档表单" : "编辑归档信息"}
                        </button>
                      ) : null}
                      {documentTaskId === task.id ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void submitDocument(task)} type="button">
                          提交文档记录
                        </button>
                      ) : null}
                      {canIgnore ? (
                        <button
                          className="button-subtle"
                          disabled={isBusy}
                          onClick={() => void updateTaskStatus(task, "ignored", { ignored_reason: ignoreReason })}
                          type="button"
                        >
                          跳过
                        </button>
                      ) : null}
                      {canArchive ? (
                        <button className="button-subtle" disabled={isBusy} onClick={() => void updateTaskStatus(task, "archived")} type="button">
                          收起
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
