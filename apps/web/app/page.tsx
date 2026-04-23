import TodayWorkspace, { type TodayTasksPayload } from "./today-workspace";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function getTodayTasks(): Promise<TodayTasksPayload & { error?: string }> {
  try {
    const response = await fetch(`${apiBaseUrl}/tasks/today?limit=10`, {
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
      error: error instanceof Error ? error.message : "Unable to load today's tasks",
    };
  }
}

export default async function HomePage() {
  const payload = await getTodayTasks();

  return (
    <TodayWorkspace
      apiBaseUrl={apiBaseUrl}
      initialAllowedStatuses={payload.allowed_statuses}
      initialError={payload.error}
      initialSummary={payload.summary}
      initialTasks={payload.tasks}
    />
  );
}
