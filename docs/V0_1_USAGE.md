# AI Signal Radar v0.1 使用指南

v0.1 是一个本地优先的 AI 信号雷达工作流。它负责从 GitHub / RSS 发现候选信号，给信号打分，把今日任务推送到飞书，并在 Web 工作台里帮助你把少量高价值项目沉淀成 Markdown 知识档案。

## 1. 启动前检查

在项目根目录运行：

```powershell
scripts\doctor.cmd
```

理想状态是大部分检查通过。`API health` 和 `Web workspace` 在服务未启动时显示 unreachable 是正常的。

如果 Web 依赖缺失，运行：

```powershell
scripts\install_web_deps.cmd
```

## 2. 启动本地工作台

启动 API 和 Web：

```powershell
scripts\start_local.cmd
```

默认地址：

```text
Web: http://127.0.0.1:3100
API: http://127.0.0.1:8000
```

如果需要局域网访问：

```powershell
scripts\start_local.cmd --lan
```

## 3. 每日流程

运行一次完整的本地采集和整理流程：

```powershell
scripts\daily_flow.cmd
```

同时发送飞书推送：

```powershell
scripts\daily_flow.cmd --send
```

常用调试参数：

```powershell
scripts\daily_flow.cmd --limit 5
scripts\daily_flow.cmd --skip-rss
scripts\daily_flow.cmd --skip-github
scripts\daily_flow.cmd --skip-push
```

## 4. Today Workspace 怎么用

打开：

```text
http://127.0.0.1:3100
```

推荐节奏：

1. 查看今日 Top Signals。
2. 从候选信号里选择 1 到 3 个值得深挖的项目。
3. 点击 `生成 Markdown 草稿`，让系统创建知识库文件。
4. 点击 `深挖 Prompt`，复制 Prompt 给 Codex / Antigravity 继续研究。
5. 编辑生成的 Markdown 文档。
6. 点击 `检测 Markdown`，让系统识别文件是否已更新。
7. 确认内容后点击 `确认归档`。
8. 不值得处理的信号可以选择跳过原因并点击 `跳过`。

## 5. Markdown 保存位置

默认每日知识档案路径：

```text
knowledge-base/daily/YYYY/MM/YYYY-MM-DD/
```

项目模板：

```text
knowledge-base/templates/project-note.md
```

建议每篇项目档案至少包含：

- 一句话总结
- 它解决什么问题
- 为什么值得关注
- 核心机制
- 适用场景
- 限制与风险
- 相关链接
- 学习建议

## 6. 飞书推送

飞书 webhook 配置见：

```text
docs/FEISHU_WEBHOOK.md
```

单独测试今日推送：

```powershell
.venv\Scripts\python scripts\push_today.py --limit 5
```

真正发送：

```powershell
.venv\Scripts\python scripts\push_today.py --send --limit 5
```

## 7. 常见问题

### API 或 Web unreachable

先确认是否已经运行：

```powershell
scripts\start_local.cmd
```

如果只是运行 `doctor` 时看到 unreachable，而你没有启动服务，这是正常状态。

### Web 依赖检查失败

运行：

```powershell
scripts\install_web_deps.cmd
```

### 没有今日任务

先跑一次：

```powershell
scripts\daily_flow.cmd
```

或者确认数据库里已有 signal 数据：

```powershell
.venv\Scripts\python scripts\top_signals.py --limit 5
```

### PowerShell 输出执行策略错误

如果每次命令前都出现 PowerShell profile 加载失败，通常是本机执行策略阻止了 `Microsoft.PowerShell_profile.ps1`。它不一定影响项目运行，但会污染命令输出。可以后续单独处理 PowerShell profile 或执行策略。

## 8. v0.1 边界

当前版本专注本地闭环，不追求完整平台化能力。

v0.1 已覆盖：

- SQLite 本地数据存储
- GitHub / RSS 信号采集
- GitHub repo snapshot
- 信号评分与 Top Signals
- 飞书 webhook 推送
- Today Workspace
- Markdown 草稿生成
- Markdown 文件检测
- 知识文档归档记录

暂不覆盖：

- 多用户权限
- 云端同步
- 外部笔记软件自动同步
- 全自动 LLM 总结
- 生产级 API key 管理
- 复杂 Agent 编排

## 9. 安全提醒

不要提交这些内容：

```text
.env
data/local.db
.venv/
apps/web/node_modules/
apps/web/.next/
Webhook URL
API key
token
本地私密笔记
```

安全规则见：

```text
docs/SECURITY_RULES.md
```
