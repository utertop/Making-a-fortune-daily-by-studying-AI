import TodayWorkspace, { type TodayTasksPayload } from "./today-workspace";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const archiveDatePattern = /^\d{4}-\d{2}-\d{2}$/;

type WorkspaceView = "today" | "todayArchive" | "historyArchive";
type SearchParams = Record<string, string | string[] | undefined>;

function firstSearchParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

async function getTasks(path: string, fallbackError: string): Promise<TodayTasksPayload & { error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        tasks: [],
        summary: null,
        allowed_statuses: [],
        error: `API returned ${response.status}`,
      };
    }

    return (await response.json()) as TodayTasksPayload;
  } catch (error) {
    return {
      tasks: [],
      summary: null,
      allowed_statuses: [],
        error: error instanceof Error ? error.message : fallbackError,
      };
  }
}

async function getInitialWorkspace(searchParams: SearchParams): Promise<
  TodayTasksPayload & { error?: string; selectedArchiveDate: string | null; view: WorkspaceView }
> {
  const view = firstSearchParam(searchParams.view);
  const date = firstSearchParam(searchParams.date);

  if (view === "archive" && date && archiveDatePattern.test(date)) {
    const payload = await getTasks(`/tasks/archive?date=${encodeURIComponent(date)}&limit=50`, "Unable to load archive tasks");
    return {
      ...payload,
      selectedArchiveDate: date,
      view: "historyArchive",
    };
  }

  const payload = await getTasks("/tasks/today?limit=10", "Unable to load today's tasks");
  return {
    ...payload,
    selectedArchiveDate: null,
    view: "today",
  };
}

export default async function HomePage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const payload = await getInitialWorkspace(resolvedSearchParams);

  return (
    <TodayWorkspace
      apiBaseUrl={apiBaseUrl}
      initialAllowedStatuses={payload.allowed_statuses}
      initialError={payload.error}
      initialSelectedArchiveDate={payload.selectedArchiveDate}
      initialSummary={payload.summary}
      initialTasks={payload.tasks}
      initialView={payload.view}
    />
  );
}
