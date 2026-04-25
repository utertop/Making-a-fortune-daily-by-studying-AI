PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    platform TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    enabled INTEGER NOT NULL DEFAULT 1,
    official INTEGER NOT NULL DEFAULT 0,
    tags TEXT,
    poll_interval_minutes INTEGER NOT NULL DEFAULT 1440,
    allowlist_domain TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, url)
);

CREATE TABLE IF NOT EXISTS signal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source_id INTEGER,
    source_type TEXT,
    raw_content TEXT,
    summary TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    signal_score REAL NOT NULL DEFAULT 0,
    freshness_score REAL NOT NULL DEFAULT 0,
    velocity_score REAL NOT NULL DEFAULT 0,
    authority_score REAL NOT NULL DEFAULT 0,
    resonance_score REAL NOT NULL DEFAULT 0,
    relevance_score REAL NOT NULL DEFAULT 0,
    actionability_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'discovered',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES source(id),
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    canonical_url TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(type, name)
);

CREATE TABLE IF NOT EXISTS github_repo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    topics TEXT,
    license TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS github_repo_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL,
    stars INTEGER NOT NULL DEFAULT 0,
    forks INTEGER NOT NULL DEFAULT 0,
    open_issues INTEGER NOT NULL DEFAULT 0,
    pushed_at TEXT,
    latest_release_at TEXT,
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(repo_id) REFERENCES github_repo(id)
);

CREATE TABLE IF NOT EXISTS learning_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    title TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    priority TEXT NOT NULL DEFAULT 'medium',
    source_url TEXT,
    target_doc_path TEXT,
    generated_prompt TEXT,
    draft_created_at TEXT,
    draft_initial_hash TEXT,
    last_detected_hash TEXT,
    last_detected_at TEXT,
    review_pending_at TEXT,
    ignored_reason TEXT,
    detection_status TEXT,
    selected_at TEXT,
    started_at TEXT,
    doc_submitted_at TEXT,
    reviewed_at TEXT,
    archived_at TEXT,
    snoozed_until TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(signal_id) REFERENCES signal(id)
);

CREATE TABLE IF NOT EXISTS knowledge_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    source_url TEXT,
    content TEXT,
    summary TEXT,
    tags TEXT,
    confidence TEXT,
    created_by_agent TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collector_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    collector_type TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    fetched_count INTEGER NOT NULL DEFAULT 0,
    created_signal_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    duration_ms INTEGER,
    FOREIGN KEY(source_id) REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS reminder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    reminder_type TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    sent_at TEXT,
    channel TEXT NOT NULL DEFAULT 'feishu',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES learning_task(id)
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    feedback_type TEXT NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(signal_id) REFERENCES signal(id)
);

CREATE TABLE IF NOT EXISTS task_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES learning_task(id)
);

CREATE INDEX IF NOT EXISTS idx_signal_score ON signal(signal_score DESC);
CREATE INDEX IF NOT EXISTS idx_signal_status ON signal(status);
CREATE INDEX IF NOT EXISTS idx_github_repo_snapshot_repo_time ON github_repo_snapshot(repo_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_task_status ON learning_task(status);
CREATE INDEX IF NOT EXISTS idx_task_event_task_time ON task_event(task_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_collector_run_status ON collector_run(status);
