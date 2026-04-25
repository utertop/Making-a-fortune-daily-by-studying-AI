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

const DOCS_NOT_FOUND = "未自动识别到官方文档链接";
const EXTRA_LINKS_NOT_FOUND = "暂无，可留空";

const statusLabels: Record<TaskStatus, string> = {
  pending: "待处理",
  pushed: "已推送",
  selected: "已选择跟进",
  draft_created: "草稿已创建",
  review_pending: "待确认提交",
  documented: "已确认提交",
  archived: "已归档",
  ignored: "已忽略",
};

const ignoreReasonOptions = ["与方向不相关", "质量不足", "已了解", "暂时不重要", "重复信号"];

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
    // ignore JSON parse failure
  }
  return `API returned ${response.status}`;
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
      firstNonEmpty([
        details.docs_url,
        details.documentation_url,
        details.docs,
        details.homepage,
        details.website,
      ]) ?? DOCS_NOT_FOUND,
    extraUrl:
      firstNonEmpty([
        details.release_url,
        details.changelog_url,
        details.blog_url,
        details.extra_links?.[0],
      ]) ?? EXTRA_LINKS_NOT_FOUND,
    targetFile:
      task.target_doc_path ?? task.document_path ?? `<knowledge-base path for task ${task.id}>`,
  };
}

function buildDeepResearchPrompt(task: TodayTask, promptDraft?: PromptDraft) {
  const draft = promptDraft ?? buildPromptDraft(task);
  const repoUrl = draft.repoUrl;
  const docsUrl =
    draft.docsUrl === DOCS_NOT_FOUND
      ? "未自动识别到官方文档链接，请优先从 README、仓库导航、官方主页中确认"
      : draft.docsUrl;
  const extraUrl = draft.extraUrl === EXTRA_LINKS_NOT_FOUND ? "暂无" : draft.extraUrl;
  const targetFile = draft.targetFile;

  return [
    "使用 $deep-project-dossier，读取以下来源并补全现有深度知识库草稿，输出最终深度知识库文档。",
    "",
    `GitHub Repo: ${repoUrl}`,
    `Docs: ${docsUrl}`,
    `Extra Links: ${extraUrl}`,
    "",
    "目标文件：",
    targetFile,
    "",
    "要求：",
    "1. 默认输出中文。",
    "2. 优先使用 README、官方 docs、examples、releases、changelog、关键配置文件、关键源码入口等主信源。",
    "3. 保持本项目 deep-project-dossier 模板结构，不要退化成普通摘要。",
    "4. 默认覆盖：项目定位、核心概念、用户工作流、架构总览、关键模块、配置与扩展、实战路径、风险与对比。",
    "5. 当代码仓库真实存在且代码是关键强信源时，补充源码级模块、调用链、目录与配置分析。",
    "6. 当代码不足、代码不关键或代码不公开时，不强行展开源码分析，而要明确说明原因。",
    "7. 区分 Fact、Inference 和 TODO；不要把推断写成确定事实。",
    "8. 代码导览要解释“为什么这些文件重要”，不要变成目录清单。",
    "9. Mermaid 图只在确实能帮助理解系统结构时添加，并配套文字解释。",
    "10. 在 Links 一节列出实际使用过的主信源链接，并在“信源与置信度说明”中说明源码级分析是否适用。",
  ].join("\n");
}

function buildHeroContent(summary: TodaySummary, completionPercent: number) {
  if (summary.is_complete && summary.actionable_count > 0) {
    return {
      eyebrow: "TODAY COMPLETE",
      title: "今天的深度研究主流程已闭环",
      summary: "今天的可处理任务已经完成确认或归档。现在更适合回看重点项目，整理收获，准备下一轮信号学习。",
      chips: [`已完成 ${summary.done_count}/${summary.actionable_count}`, "主流程已闭环", `完成度 ${completionPercent}%`],
    };
  }

  if (summary.review_pending > 0) {
    return {
      eyebrow: "FOCUS: REVIEW",
      title: `先处理 ${summary.review_pending} 条待确认文档`,
      summary: "当前最值钱的动作是回到已补全的知识库文档，快速审核内容，然后在这里确认提交并继续归档。",
      chips: [`待确认 ${summary.review_pending}`, `草稿待补全 ${summary.draft_created}`, `完成度 ${completionPercent}%`],
    };
  }

  if (summary.draft_created > 0) {
    return {
      eyebrow: "FOCUS: DRAFTS",
      title: `还有 ${summary.draft_created} 份草稿待补全`,
      summary: "草稿已经准备好了，下一步更适合用深度研究 Prompt 去补全文档，再回到这里做确认提交。",
      chips: [`草稿待补全 ${summary.draft_created}`, `待确认 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
    };
  }

  if (summary.selected > 0) {
    return {
      eyebrow: "FOCUS: FOLLOW UP",
      title: `已选择 ${summary.selected} 个项目进入深度跟进`,
      summary: "今天已经有项目进入主流程。继续为这些任务创建深度草稿，然后生成 Prompt 去完善知识库文档。",
      chips: [`已选择跟进 ${summary.selected}`, `待确认 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
    };
  }

  return {
    eyebrow: "V0.1 LOCAL WORKSPACE",
    title: "AI Signal Radar",
    summary: "这是今天的深度研究工作台。我们只保留一条主流程：选择跟进项目，生成深度草稿，补全文档，然后回到这里确认提交与归档。",
    chips: [`待处理 ${summary.pending + summary.pushed}`, `待确认 ${summary.review_pending}`, `完成度 ${completionPercent}%`],
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
  const [runtimeApiBaseUrl, setRuntimeApiBaseUrl] = useState(apiBaseUrl);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const liveSummary = useMemo(() => buildSummary(tasks), [tasks]);
  const completionPercent = liveSummary.actionable_count
    ? Math.round((liveSummary.done_count / liveSummary.actionable_count) * 100)
    : 0;
  const allowedStatusSet = useMemo(() => new Set(allowedStatuses), [allowedStatuses]);
  const today = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "full",
    timeZone: "Asia/Shanghai",
  }).format(new Date());
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
        const response = await fetch(`${runtimeApiBaseUrl}/tasks/today?limit=10`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }

        const payload = (await response.json()) as TodayTasksPayload;
        setTasks(payload.tasks);
        setAllowedStatuses(payload.allowed_statuses);
        if (!silent) {
          setNotice("已刷新今日任务状态。");
        }
      } catch (refreshError) {
        if (!silent) {
          setError(refreshError instanceof Error ? refreshError.message : "刷新任务状态失败。");
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
      const detectableCount = tasks.filter((task) =>
        ["selected", "draft_created", "review_pending"].includes(task.status) && task.target_doc_path,
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

        const payload = (await response.json()) as {
          checked: number;
          changed: number;
          tasks: TodayTask[];
        };
        if (payload.tasks.length > 0) {
          setTasks((currentTasks) =>
            currentTasks.map((task) => payload.tasks.find((item) => item.id === task.id) ?? task),
          );
        }
        if (!silent && payload.changed > 0) {
          setNotice(`已检测到 ${payload.changed} 个待确认知识库文档。`);
          setError("");
        }
      } catch (detectError) {
        if (!silent) {
          setError(detectError instanceof Error ? detectError.message : "刷新文档检测状态失败。");
          setNotice("");
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
    const isLocalApi = apiBaseUrl.includes("127.0.0.1") || apiBaseUrl.includes("localhost");
    const isLocalPage = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";
    if (isLocalApi && !isLocalPage) {
      setRuntimeApiBaseUrl(`http://${window.location.hostname}:8000`);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    void runBulkDetection(true);
  }, [runBulkDetection]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void runBulkDetection(true);
      }
    }, 90_000);

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        void refreshTodayTasks(true);
        void runBulkDetection(true);
      }
    };

    const handleFocus = () => {
      void refreshTodayTasks(true);
      void runBulkDetection(true);
    };

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleFocus);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleFocus);
    };
  }, [refreshTodayTasks, runBulkDetection]);

  function showNotice(message: string) {
    setNotice(message);
    setError("");
  }

  function showError(message: string) {
    setError(message);
    setNotice("");
  }

  function taskLabel(task: TodayTask) {
    return task.title.length > 42 ? `${task.title.slice(0, 42)}...` : task.title;
  }

  function statusSuccessMessage(status: TaskStatus, task: TodayTask) {
    const label = taskLabel(task);
    const messages: Record<TaskStatus, string> = {
      pending: `已将 ${label} 调整为待处理。`,
      pushed: `已将 ${label} 标记为已推送。`,
      selected: `已选择跟进 ${label}。`,
      draft_created: `已为 ${label} 创建知识库草稿。`,
      review_pending: `已检测到 ${label} 的待确认知识库文档。`,
      documented: `已确认提交 ${label} 的知识库文档。`,
      archived: `已归档 ${label}。`,
      ignored: `已忽略 ${label}。`,
    };
    return messages[status];
  }

  async function updateTaskStatus(task: TodayTask, status: TaskStatus, extra?: { ignored_reason?: string }) {
    setBusyTaskId(task.id);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          ignored_reason: extra?.ignored_reason ?? null,
        }),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask };
      applyTaskUpdate(payload.task);
      showNotice(statusSuccessMessage(status, payload.task));
    } catch (updateError) {
      showError(updateError instanceof Error ? updateError.message : "更新任务状态失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

function getDocumentDraft(task: TodayTask): DocumentDraft {
    const fallbackTitle = `${task.title} 深度项目知识档案`;
    const normalizedTitle =
      task.document_title && !/[?？�]/.test(task.document_title) ? task.document_title : fallbackTitle;

    return (
      documentDrafts[task.id] ?? {
        title: normalizedTitle,
        path: task.document_path ?? task.target_doc_path ?? `${archivePath}${slugify(task.title)}-${task.id}.md`,
        summary: task.document_summary ?? task.summary ?? "",
        tags: "ai,github,deep-dossier",
        confidence: "medium",
        created_by_agent: "manual",
      }
    );
  }

  function updateDocumentDraft(taskId: number, patch: Partial<DocumentDraft>) {
    const task = tasks.find((item) => item.id === taskId);
    if (!task) {
      return;
    }

    setDocumentDrafts((currentDrafts) => ({
      ...currentDrafts,
      [taskId]: {
        ...(currentDrafts[taskId] ?? getDocumentDraft(task)),
        ...patch,
      },
    }));
  }

  function getPromptDraft(task: TodayTask): PromptDraft {
    return promptDrafts[task.id] ?? buildPromptDraft(task);
  }

  function updatePromptDraft(task: TodayTask, patch: Partial<PromptDraft>) {
    setPromptDrafts((currentDrafts) => ({
      ...currentDrafts,
      [task.id]: {
        ...(currentDrafts[task.id] ?? buildPromptDraft(task)),
        ...patch,
      },
    }));
  }

  async function submitDocument(task: TodayTask) {
    const draft = getDocumentDraft(task);
    if (!draft.title.trim() || !draft.path.trim()) {
      showError("文档标题和路径不能为空。");
      return;
    }

    setBusyTaskId(task.id);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/document`, {
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
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask };
      applyTaskUpdate(payload.task);
      setDocumentTaskId(null);
      showNotice(`已确认提交文档：${payload.task.document_path ?? draft.path}`);
    } catch (submitError) {
      showError(submitError instanceof Error ? submitError.message : "确认提交文档失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function generateDraft(task: TodayTask) {
    setBusyTaskId(task.id);
    setError("");
    setNotice("");

    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite: false }),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as { task: TodayTask; draft: { path: string } };
      applyTaskUpdate(payload.task);
      setDocumentDrafts((currentDrafts) => ({
        ...currentDrafts,
        [task.id]: {
          ...getDocumentDraft(payload.task),
          path: payload.draft.path,
        },
      }));
      setDocumentTaskId(task.id);
      setPromptPreviewTaskId(task.id);
      showNotice(`知识库草稿已创建：${payload.draft.path}。接下来进入深度研究主流程，预览并复制深度研究 Prompt。`);
    } catch (draftError) {
      showError(draftError instanceof Error ? draftError.message : "创建知识库草稿失败。");
    } finally {
      setBusyTaskId(null);
    }
  }

  async function detectTaskDocument(task: TodayTask, silent = false) {
    if (!silent) {
      setBusyTaskId(task.id);
      setError("");
      setNotice("");
    }

    try {
      const response = await fetch(`${runtimeApiBaseUrl}/tasks/${task.id}/detect-document`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const payload = (await response.json()) as {
        task: TodayTask;
        changed: boolean;
        reason: string;
      };
      applyTaskUpdate(payload.task);
      if (!silent) {
        if (payload.reason === "review_pending") {
          showNotice(`检测到待确认知识库文档：${payload.task.target_doc_path ?? ""}`);
        } else if (payload.reason === "waiting_for_update") {
          showNotice("已刷新检测状态，当前还没有发现补全文档。");
        } else if (payload.reason === "missing_file") {
          showNotice("草稿路径已记录，但目录里暂时还没有检测到文件。");
        } else {
          showNotice("已刷新文档检测状态。");
        }
      }
    } catch (detectError) {
      if (!silent) {
        showError(detectError instanceof Error ? detectError.message : "刷新文档检测状态失败。");
      }
    } finally {
      if (!silent) {
        setBusyTaskId(null);
      }
    }
  }

  async function copyText(value: string, label: string) {
    setError("");
    setNotice("");

    try {
      await navigator.clipboard.writeText(value);
      showNotice(`已复制${label}。`);
    } catch {
      showError("复制失败，请手动复制。");
    }
  }

  async function copyDeepResearchPrompt(task: TodayTask) {
    const prompt = buildDeepResearchPrompt(task, getPromptDraft(task));
    await copyText(prompt, "深度研究 Prompt");
  }

  function taskProgressHint(task: TodayTask) {
    if (task.status === "review_pending") {
      return `检测到待确认知识库文档，上次检测时间：${formatDateTime(task.last_detected_at) || "刚刚"}`;
    }
    if (task.status === "draft_created") {
      return "已生成草稿，暂未检测到补全文档。";
    }
    if (task.status === "selected") {
      return "已选择跟进，下一步建议创建知识库草稿。";
    }
    if (task.status === "documented") {
      return `已提交文档：${formatDateTime(task.doc_submitted_at) || "刚刚"}`;
    }
    if (task.status === "ignored" && task.ignored_reason) {
      return `已忽略，原因：${task.ignored_reason}`;
    }
    return "";
  }

  function nextStepLabel(task: TodayTask) {
    if (task.status === "pending" || task.status === "pushed") {
      return "下一步：选择跟进";
    }
    if (task.status === "selected") {
      return "下一步：创建知识库草稿";
    }
    if (task.status === "draft_created") {
      return "下一步：生成深度 Prompt 并补全文档";
    }
    if (task.status === "review_pending") {
      return "下一步：确认提交文档";
    }
    if (task.status === "documented") {
      return "下一步：归档";
    }
    if (task.status === "archived") {
      return "当前状态：已归档完成";
    }
    if (task.status === "ignored") {
      return "当前状态：已忽略";
    }
    return "下一步：继续处理";
  }

  return (
    <main className="page-shell">
      <section className="workspace-header workspace-hero">
        <div className="workspace-hero-copy">
          <p className="eyebrow">v0.1 Local Workspace</p>
          <h1 className="brand-title">AI Signal Radar</h1>
          <p className="summary">
            这是今天的深度研究工作台。我们只保留一条主流程：选择跟进项目，生成深度草稿，补全文档，然后回到这里确认提交与归档。
          </p>
        </div>
        <div className="workspace-hero-stats">
          <div className="hero-stat-card hero-stat-card-strong">
            <span>{liveSummary.review_pending}</span>
            <strong>待确认提交</strong>
            <p>{liveSummary.review_pending > 0 ? "优先清掉这些待确认文档" : "当前没有待确认文档"}</p>
          </div>
          <div className="hero-stat-card">
            <span>{liveSummary.draft_created}</span>
            <strong>草稿待补全</strong>
            <p>{liveSummary.draft_created > 0 ? "还有草稿等待补全" : "草稿流程很干净"}</p>
          </div>
          <div className="hero-stat-card">
            <span>{liveSummary.done_count}/{liveSummary.actionable_count}</span>
            <strong>今日完成度</strong>
            <p>{liveSummary.is_complete ? "今天已经闭环" : "还有任务待处理"}</p>
            <div className="hero-progress">
              <div className="hero-progress-track">
                <div className="hero-progress-fill" style={{ width: `${completionPercent}%` }} />
              </div>
              <div className="hero-progress-caption">
                <span>完成进度</span>
                <strong>{completionPercent}%</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="operation-bar" aria-live="polite">
        <div>
          <strong>当前时间</strong>
          <p>{clockText}</p>
        </div>
        <div>
          <strong>今日归档目录</strong>
          <p className="break-text">{archivePath}</p>
        </div>
        <button onClick={() => void copyText(archivePath, "知识库目录")} type="button">
          复制目录
        </button>
      </section>

      {notice ? <div className="notice-banner">{notice}</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="attention-strip" aria-label="Today reminders">
        <div className={liveSummary.review_pending > 0 ? "attention-card highlight" : "attention-card"}>
          <strong>待你确认</strong>
          <p>
            {liveSummary.review_pending > 0
              ? `检测到 ${liveSummary.review_pending} 个知识库文档待确认。`
              : "还没有检测到待确认知识库文档。"}
          </p>
        </div>
        <div className={liveSummary.draft_created > 0 ? "attention-card highlight" : "attention-card"}>
          <strong>待补全文档</strong>
          <p>
            {liveSummary.draft_created > 0
              ? `还有 ${liveSummary.draft_created} 个草稿等待你用 Codex / Antigravity 补全。`
              : "当前没有草稿卡在补全阶段。"}
          </p>
        </div>
        <div className="attention-card action-card">
          <strong>状态检查</strong>
          <p>{isRefreshing ? "正在刷新今日任务..." : "页面会在可见状态下每 90 秒自动检查一次文档更新。"}</p>
          <button onClick={() => void refreshTodayTasks(false)} type="button">
            刷新任务
          </button>
        </div>
      </section>

      <section className="today-grid" aria-label="Today workspace status">
        <div className="status-panel status-panel-lead">
          <p className="panel-label">Today</p>
          <h2>今日 AI 学习任务</h2>
          <p className="panel-copy">{today}</p>
        </div>
        <div className="status-panel">
          <p className="panel-label">Progress</p>
          <h2>
            {liveSummary.done_count}/{liveSummary.actionable_count}
          </h2>
          <p className="panel-copy">
            {liveSummary.is_complete ? "今日任务已经闭环。" : "还有任务需要处理或确认。"}
          </p>
        </div>
        <div className="status-panel">
          <p className="panel-label">API</p>
          <h2>Local</h2>
          <p className="panel-copy break-text">{runtimeApiBaseUrl}</p>
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
          <span className={liveSummary.selected > 0 || liveSummary.draft_created > 0 ? "step-dot done" : "step-dot"} />
          <strong>知识库跟进</strong>
          <p>{liveSummary.selected > 0 || liveSummary.draft_created > 0 ? "已选择项目并开始处理" : "等待选择跟进项目"}</p>
        </div>
        <div>
          <span className={liveSummary.documented > 0 ? "step-dot done" : "step-dot current"} />
          <strong>提交确认</strong>
          <p>{liveSummary.documented > 0 ? "已确认提交文档" : "检测待确认文档并完成提交"}</p>
        </div>
      </section>

      <section className="task-summary-grid" aria-label="Task counts">
        <div className="summary-card summary-card-hot">
          <span>{liveSummary.review_pending}</span>
          <p>待确认提交</p>
        </div>
        <div className="summary-card summary-card-hot">
          <span>{liveSummary.draft_created}</span>
          <p>草稿已创建</p>
        </div>
        <div className="summary-card">
          <span>{liveSummary.documented}</span>
          <p>已确认提交</p>
        </div>
        <div className="summary-card">
          <span>{liveSummary.selected}</span>
          <p>已选择跟进</p>
        </div>
        <div className="summary-card">
          <span>{liveSummary.pending}</span>
          <p>待处理</p>
        </div>
        <div className="summary-card">
          <span>{liveSummary.total}</span>
          <p>候选总数</p>
        </div>
      </section>

      <section className="signals-section" aria-label="Today learning tasks">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Today Tasks</p>
            <h2>本地任务状态</h2>
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="empty-state">
            <h3>还没有今日任务</h3>
            <p>
              先在项目根目录运行 <code>scripts\daily_flow.cmd</code>，然后刷新页面。如果只是想验证界面，可以使用
              <code> --skip-rss --skip-github --skip-push --limit 3</code>。
            </p>
          </div>
        ) : (
          <div className="signal-list">
            {tasks.map((task, index) => {
              const details = parseDetails(task.raw_content);
              const reasons = details.reasons?.slice(0, 3) ?? [];
              const risks = details.risks?.slice(0, 2) ?? [];
              const isBusy = busyTaskId === task.id;
              const draft = getDocumentDraft(task);
              const promptDraft = getPromptDraft(task);
              const progressHint = taskProgressHint(task);
              const deepPromptText = buildDeepResearchPrompt(task, promptDraft);
              const isPromptPreviewOpen = promptPreviewTaskId === task.id;
              const canPush = allowedStatusSet.has("pushed") && task.status === "pending";
              const canSelect =
                allowedStatusSet.has("selected") && (task.status === "pending" || task.status === "pushed");
              const canCreateDraft =
                task.status === "selected" || task.status === "draft_created" || task.status === "review_pending";
              const canDetect =
                Boolean(task.target_doc_path) &&
                task.status !== "documented" &&
                task.status !== "archived" &&
                task.status !== "ignored";
              const canConfirmDocument =
                Boolean(task.target_doc_path) &&
                task.status !== "documented" &&
                task.status !== "archived" &&
                task.status !== "ignored";
              const canPreviewPrompt =
                Boolean(task.target_doc_path) &&
                (task.status === "selected" || task.status === "draft_created" || task.status === "review_pending");
              const canIgnore =
                allowedStatusSet.has("ignored") &&
                task.status !== "documented" &&
                task.status !== "archived" &&
                task.status !== "ignored";
              const canArchive =
                allowedStatusSet.has("archived") && (task.status === "documented" || task.status === "ignored");
              const ignoreReason = ignoreReasons[task.id] ?? "暂时不重要";
              const nextStep = nextStepLabel(task);

              const isWorkspaceOpen = isPromptPreviewOpen || documentTaskId === task.id;
              const isTerminalCard =
                task.status === "documented" || task.status === "archived" || task.status === "ignored";

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
                        <div className="next-step-chip">{nextStep}</div>
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
                      <ul className="reason-list" aria-label={`${task.title} scoring reasons`}>
                        {reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : null}

                    <div className="signal-insight-strip">
                      {risks.length > 0 ? (
                        <p className="risk-text">风险：{risks.join("；")}</p>
                      ) : (
                        <p className="risk-text muted">暂无明显风险信号</p>
                      )}

                      {progressHint ? <div className="task-hint">{progressHint}</div> : null}

                      {task.document_path ?? task.target_doc_path ? (
                        <div className="doc-path-row">
                          <p className="doc-path">
                            Markdown：{task.document_title ? `${task.document_title} - ` : ""}
                            {task.document_path ?? task.target_doc_path}
                          </p>
                          <button
                            onClick={() => void copyText(task.document_path ?? task.target_doc_path ?? "", "知识库路径")}
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
                          <span className="signal-workspace-kicker">工作区</span>
                          <strong>{isWorkspaceOpen ? "已展开当前任务工作区" : "默认收起，展开后继续处理当前任务"}</strong>
                        </div>
                        <span className="signal-workspace-state">{isWorkspaceOpen ? "展开中" : "已折叠"}</span>
                      </div>

                    {isWorkspaceOpen ? (
                      <div className="signal-workspace">
                        {isPromptPreviewOpen ? (
                          <div className="prompt-preview-panel">
                            <div className="panel-kicker">Deep Prompt</div>
                          <div className="prompt-preview-header">
                              <div>
                                <strong>深度研究 Prompt 预览</strong>
                                <p>确认来源和目标文件后再复制给 Codex / Antigravity。这一步只负责生成研究指令，不改变任务状态。</p>
                              </div>
                              <div className="prompt-preview-actions">
                                <button onClick={() => void copyDeepResearchPrompt(task)} type="button">
                                  复制深度 Prompt
                                </button>
                                <button onClick={() => void copyText(promptDraft.targetFile, "目标文件路径")} type="button">
                                  复制目标文件路径
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
                                <span>目标文件</span>
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
                                <small>只读预览</small>
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
                          <span>忽略原因</span>
                          <select
                            onChange={(event) =>
                              setIgnoreReasons((currentReasons) => ({
                                ...currentReasons,
                                [task.id]: event.target.value,
                              }))
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
                          选择跟进
                        </button>
                      ) : null}
                      {canCreateDraft ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void generateDraft(task)} type="button">
                          创建知识库草稿
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
                          生成深度研究 Prompt
                        </button>
                      ) : null}
                      {canDetect ? (
                        <button className="button-secondary" disabled={isBusy} onClick={() => void detectTaskDocument(task)} type="button">
                          刷新检测状态
                        </button>
                      ) : null}
{canConfirmDocument ? (
                        <button
                          className="button-primary"
                          disabled={isBusy}
                          onClick={() => void submitDocument(task)}
                          type="button"
                        >
                          确认提交文档
                        </button>
                      ) : null}
                      {canConfirmDocument ? (
                        <button
                          className="button-secondary"
                          disabled={isBusy}
                          onClick={() => setDocumentTaskId(documentTaskId === task.id ? null : task.id)}
                          type="button"
                        >
                          {documentTaskId === task.id ? "收起提交信息" : "编辑提交信息"}
                        </button>
                      ) : null}
                      {documentTaskId === task.id ? (
                        <button className="button-primary" disabled={isBusy} onClick={() => void submitDocument(task)} type="button">
                          保存并确认提交
                        </button>
                      ) : null}
                      {canIgnore ? (
                        <button
                          className="button-subtle"
                          disabled={isBusy}
                          onClick={() => void updateTaskStatus(task, "ignored", { ignored_reason: ignoreReason })}
                          type="button"
                        >
                          忽略
                        </button>
                      ) : null}
                      {canArchive ? (
                        <button className="button-subtle" disabled={isBusy} onClick={() => void updateTaskStatus(task, "archived")} type="button">
                          归档
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
