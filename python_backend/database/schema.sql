CREATE TABLE IF NOT EXISTS trending_topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  normalized_title TEXT NOT NULL,
  source TEXT,
  score REAL DEFAULT 0,
  used INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generated_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL,
  image_url TEXT,
  caption TEXT,
  description TEXT,
  hashtags TEXT,
  status TEXT DEFAULT 'draft',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (topic_id) REFERENCES trending_topics (id)
);

CREATE TABLE IF NOT EXISTS publication_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  status TEXT NOT NULL,
  response_json TEXT,
  error_message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id) REFERENCES generated_posts (id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  execution_mode TEXT,
  selected_steps_json TEXT NOT NULL DEFAULT '[]',
  completed_steps_json TEXT NOT NULL DEFAULT '[]',
  current_step TEXT,
  next_step TEXT,
  outputs_json TEXT NOT NULL DEFAULT '{}',
  errors_json TEXT NOT NULL DEFAULT '[]',
  evidence_json TEXT NOT NULL DEFAULT '{}',
  topic_id INTEGER,
  topic_title TEXT,
  post_id INTEGER,
  quality_score REAL
);

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_updated_at ON pipeline_runs (updated_at);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_status ON pipeline_runs (status);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_topic_id ON pipeline_runs (topic_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_topic_title ON pipeline_runs (topic_title);
CREATE INDEX IF NOT EXISTS ix_pipeline_runs_post_id ON pipeline_runs (post_id);
