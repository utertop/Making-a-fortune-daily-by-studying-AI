# AI Signal Radar v0.1 任务清单

## 1. v0.1 目标

v0.1 只做最小可用闭环：

```text
发现热点
  -> 初步评分
  -> 飞书推送
  -> Today Workspace 待办
  -> Codex / Antigravity 半自动生成 Markdown
  -> 提交知识库
  -> 任务完成提醒
```

v0.1 不追求完整平台，不做全自动 LLM，不做云端同步，不做外部笔记自动同步。

## 2. 开工节奏原则

第一步不要直接做复杂前端大界面，先把 Phase 0 + Phase 1 跑起来。

优先顺序：

```text
目录结构
  -> .env.example
  -> config/sources.yaml
  -> knowledge-base/ 初始目录
  -> FastAPI 骨架
  -> Next.js 骨架
  -> SQLite 连接
  -> /health 检查
```

原因：

- 先确认本地运行方式和项目边界。
- 先固定配置、目录、数据库和启动方式。
- 后续采集、评分、推送、Today Workspace 都依赖这些基础设施。
- v0.1 前端只做可用工作台，不做复杂视觉和完整产品界面。

开工第一批任务：

1. 创建项目目录结构。
2. 创建 `.env.example`。
3. 创建 `config/sources.yaml`。
4. 创建 `knowledge-base/` 初始目录。
5. 初始化 FastAPI 项目。
6. 初始化 Next.js 项目。
7. 配置 SQLite。
8. 实现后端 `/health`。

## 3. 默认技术选型

```text
前端：Next.js
后端：FastAPI
数据库：SQLite
任务调度：APScheduler 或简单 cron
采集：feedparser + GitHub API
推送：飞书 webhook
知识库：本地 Markdown
配置：.env + config/sources.yaml
```

后续可迁移：

- SQLite -> PostgreSQL / Supabase
- 本地前端 -> Vercel
- 半自动总结 -> API key 全自动总结
- 本地 Markdown -> GitHub 私有仓库同步

## 4. 目录结构

建议 v0.1 按以下结构创建：

```text
apps/
  web/
  api/
config/
  sources.yaml
knowledge-base/
  daily/
  weekly/
  projects/
  concepts/
  people/
  companies/
  comparisons/
assets/
  mermaid/
  images/
data/
  local.db
scripts/
docs/
```

## 5. Phase 0：开工前确认

### 任务

- 确认飞书 webhook 获取方式。
- 确认是否使用 GitHub token。
- 确认本地端口和运行方式。
- 创建 `.env.example`。
- 创建 `config/sources.yaml` 初始信源。
- 创建 `knowledge-base/` 初始目录。

### 验收

- `.env.example` 存在，不包含真实密钥。
- `config/sources.yaml` 存在。
- `knowledge-base/` 目录存在。
- 飞书 webhook 可以在本地测试发送消息。

## 6. Phase 1：项目骨架

### 任务

- 初始化后端 FastAPI 项目。
- 初始化前端 Next.js 项目。
- 配置 SQLite 数据库。
- 配置基础环境变量读取。
- 增加本地启动命令。
- 增加基础 health check。

### 验收

- 后端可以启动并访问 `/health`。
- 前端可以启动并访问首页。
- 后端可以连接 SQLite。
- 本地启动步骤写入 README 或 docs。

## 7. Phase 2：数据模型

### 任务

实现或迁移以下表：

- source
- signal
- entity
- github_repo
- github_repo_snapshot
- learning_task
- knowledge_document
- collector_run
- reminder
- user_feedback

### 关键字段

`github_repo`：

```text
id
full_name
url
description
language
topics
license
created_at
updated_at
```

`github_repo_snapshot`：

```text
id
repo_id
stars
forks
open_issues
pushed_at
latest_release_at
captured_at
```

`collector_run`：

```text
id
source_id
collector_type
started_at
finished_at
status
fetched_count
created_signal_count
error_message
duration_ms
```

### 验收

- 数据库可以初始化。
- 能创建并查询基础表。
- 能保存 GitHub repo 和 snapshot。
- 能保存 collector run。

## 8. Phase 3：信源和采集器

### 任务

- 实现 `sources.yaml` 加载。
- 实现 RSS / 官方博客采集。
- 实现 GitHub repo 搜索采集。
- 实现 GitHub repo 快照保存。
- 实现基础去重。
- 实现 collector run 记录。

### v0.1 数据源

- GitHub AI 关键词搜索。
- 官方博客 RSS。
- Hacker News 可作为辅助。
- Hugging Face Papers 可作为辅助。

暂不接：

- X API。
- Reddit API。
- YouTube API。

### 注意

- GitHub Search v0.1 先保证链路跑通；query 初版可能偏宽，后续在评分与排序阶段收紧 AI 相关性。

### 验收

- 能从 sources.yaml 加载信源。
- 能采集至少一个 RSS 源。
- 能采集 GitHub repo。
- 同一个 repo 多次采集能产生多条 snapshot。
- 采集失败时有 collector run 错误记录。

## 9. Phase 4：评分与排序

### 任务

- 实现 Signal Score 初版。
- 实现 GitHub delta 计算。
- 实现 Top 10 候选信号生成。
- 实现风险降权。

### v0.1 评分规则

```text
stars_24h_delta > 1000: +25
stars_7d_delta > 3000: +20
forks_7d_delta > 200: +10
latest_commit within 14 days: +10
has_readme: +5
has_examples: +5
has_docs: +5
has_license: +5
mentioned_by_authority_source: +15
appears_in_multiple_sources: +10
no_license: -10
no_docs_or_examples: -10
stale_repo_over_180_days: -20
readme_marketing_only: -10
```

### 验收

- 能计算 repo 的 24h / 7d star delta。
- 能生成 Signal Score。
- 能按分数输出 Top 10。
- 能解释每条信号的加分和降权原因。

## 10. Phase 5：飞书推送

### 任务

- 实现飞书 webhook 推送。
- 实现今日候选任务消息。
- 实现任务完成提醒消息。
- 增加推送失败日志。

### 推送内容

- 今日发现数量。
- 今日 Top 10 候选信号。
- 建议深挖 1 到 3 条。
- Today Workspace 入口。
- 今日最低目标：提交 1 篇 Markdown。

### 验收

- 能向飞书群发送测试消息。
- 能推送今日 AI 学习任务。
- 推送失败时有错误记录。

## 11. Phase 6：Today Workspace

### 任务

- 实现今日任务页面。
- 展示今日候选信号。
- 展示任务状态和进度。
- 支持深挖、跳过、稍后提醒。
- 支持生成 Codex / Antigravity Prompt。

### 页面最小功能

```text
今日 AI 学习任务

[已完成] 今日热点已推送到飞书
[待处理] 从候选信号中选择 1 到 3 个深挖
[待处理] 为选中的信号生成知识库 Markdown
[待处理] 审核并归档今日文档
```

### 验收

- 页面能显示今日 Top 10。
- 能创建 deep_dive task。
- 能把任务状态改为 selected / in_progress / skipped / snoozed。
- 能复制 Prompt。

## 12. Phase 7：Markdown 提交

### 任务

- 支持粘贴 Markdown。
- 支持上传 `.md` 文件。
- 支持输入 `knowledge-base/` 路径并检测文件存在。
- 检测 frontmatter 的 `source_url`。
- 检测必要章节。
- 任务自动标记为 `doc_submitted`。
- 支持手动标记完成作为兜底。

### 必要章节

- 一句话总结
- 它解决什么问题
- 为什么值得关注
- 核心机制
- 适用场景
- 局限与风险
- 相关链接
- 学习建议

### 验收

- 粘贴 Markdown 可以保存到 `knowledge-base/`。
- 上传 `.md` 可以保存到 `knowledge-base/`。
- 指定存在路径可以完成检测。
- 缺少 source_url 或必要章节时提示补充。
- 提交后任务自动完成。

## 13. Phase 8：日报生成

### 任务

- 每天生成 `knowledge-base/daily/YYYY-MM-DD.md`。
- 包含今日 Top 10 信号。
- 包含已提交文档列表。
- 包含未完成任务。
- 包含明日建议。

### 验收

- 能生成当日 Markdown 日报。
- 日报包含来源链接。
- 日报包含任务状态。
- 日报可以被 Obsidian 直接打开。

## 14. Phase 9：验收测试

### 总体验收

- 能采集 GitHub repo。
- 能保存至少两次 GitHub repo 快照。
- 能计算 star / fork delta。
- 能采集 RSS / 官方博客。
- 能生成今日 Top 10 候选信号。
- 能推送飞书消息。
- 能创建 Learning Task。
- 能生成 Codex / Antigravity Prompt。
- 能提交 Markdown 文档。
- 能检测 `knowledge-base/` 中的目标文档。
- 能自动把任务标记为完成。
- 能生成每日 `knowledge-base/daily/YYYY-MM-DD.md`。

## 15. v0.1 不做清单

- X API。
- Notion / 语雀 / 有道云 / 飞书文档自动同步。
- 云端与本地双向同步。
- 自动 clone 和运行 GitHub 项目。
- 复杂 Agent 编排。
- 多用户权限。
- 复杂概念图谱。
- 全自动 LLM 总结。
- 生产级 API key 管理和计费控制。

## 16. 后续升级入口

v0.1 开发时需要保留这些接口边界：

- LLM provider adapter。
- Push provider adapter。
- Source collector adapter。
- Notebook / knowledge export adapter。
- Sync service adapter。
- Scoring rule registry。

这些不需要 v0.1 完整实现，但命名和模块边界要留好。

