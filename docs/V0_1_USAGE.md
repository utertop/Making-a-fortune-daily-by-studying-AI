# v0.1 使用说明

本文档说明当前 v0.1 阶段已经可以怎么用、怎么验证、哪些能力仍然是半自动。

## 当前定位

v0.1 是一个本地优先的 AI 信号雷达和学习工作台。

它现在主要完成四件事：

1. 采集 GitHub / RSS 等公开信号。
2. 对 AI 相关项目做本地评分和排序。
3. 通过飞书推送今日候选信号。
4. 在 Web 工作台里跟进任务，并生成 Markdown 知识库草稿。

当前还不是全自动 Agent 系统。v0.1 的默认模式是半自动：系统负责采集、筛选、排序、推送和生成基础草稿；你再用 Codex / Antigravity 补全深度总结和知识库内容。

## 本地地址

启动后访问：

```text
http://127.0.0.1:3100
```

本地 API 地址：

```text
http://127.0.0.1:8000
```

这两个地址都只在本机服务运行时可用，不是公网部署地址。

如果需要同一局域网内的电脑或手机访问，可以用 LAN 模式启动：

```powershell
scripts\start_local.cmd --lan
```

脚本会尝试打印类似这样的地址：

```text
LAN Web: http://192.168.x.x:3100
LAN API: http://192.168.x.x:8000
```

注意：LAN 模式会让同一局域网设备访问你的本地服务，只建议在可信网络里使用。
从局域网地址打开页面时，Web 会自动把按钮请求切换到同一台主机的 `:8000` API。

## 第一次使用前检查

在项目根目录执行：

```powershell
scripts\doctor.cmd
```

理想结果：

```text
ok: true
ok_count: 12/12
```

如果 Web 依赖缺失，执行：

```powershell
scripts\install_web_deps.cmd
```

如果 API 或 Web 显示 unreachable，通常只是本地服务还没有启动。

## 启动 Web 工作台

在项目根目录执行：

```powershell
scripts\start_local.cmd
```

它会启动两个本地服务：

```text
API: http://127.0.0.1:8000
Web: http://127.0.0.1:3100
```

然后打开：

```text
http://127.0.0.1:3100
```

如果窗口一闪而过，或者页面打不开，重新执行：

```powershell
scripts\doctor.cmd
```

并查看 API / Web 两个窗口里的错误信息。

如果希望局域网访问，启动方式改为：

```powershell
scripts\start_local.cmd --lan
```

如果希望完全不手动启动，需要做 Windows 开机启动、计划任务、桌面应用壳或云端部署。这些都属于 v0.1 之后的增强项；当前项目内已经提供一键启动脚本，但不会主动修改你的系统启动项。

## 每日推荐流程

### 1. 运行今日雷达

只预览，不真实推送飞书：

```powershell
scripts\daily_flow.cmd
```

真实推送到飞书：

```powershell
scripts\daily_flow.cmd --send
```

常用参数：

```powershell
scripts\daily_flow.cmd --limit 5
scripts\daily_flow.cmd --skip-rss
scripts\daily_flow.cmd --skip-github
scripts\daily_flow.cmd --skip-push
```

### 2. 打开 Today Workspace

访问：

```text
http://127.0.0.1:3100
```

页面会展示今日候选 AI 信号、评分、star / fork / delta、语言、许可证、触发规则和风险提示。

### 3. 处理今日任务

推荐顺序：

1. 先看 Top Signals。
2. 对值得关注的项目点 `选择跟进`。
3. 对值得写知识库的项目点 `生成 Markdown 草稿`。
4. 用 Codex / Antigravity 阅读链接、仓库、文档后补全 Markdown。
5. 回到 Web 页面点 `提交文档`，填写路径、摘要、标签。
6. 点 `保存文档记录`。
7. 对不处理的项目点 `忽略`，对已结束跟进的项目点 `归档`。

## Web 按钮说明

| 按钮 | 当前作用 |
| --- | --- |
| `标记已推送` | 在本地数据库记录这条任务已经推送过；不会重新发送飞书消息。 |
| `选择跟进` | 把任务状态改成跟进中。 |
| `生成 Markdown 草稿` | 在 `knowledge-base/daily/YYYY/MM/YYYY-MM-DD/` 下生成一篇标准 Markdown 草稿，并把任务改为跟进中。 |
| `提交文档` | 展开文档提交表单。 |
| `保存文档记录` | 把文档路径、摘要、标签等写入本地数据库，并把任务标记为已文档化。 |
| `忽略` | 标记这条今天不处理。 |
| `归档` | 标记为已归档，算作今日已处理。 |

当前页面已经提供操作成功 / 失败提示。生成 Markdown 草稿后会显示文件路径，并提供复制路径按钮。

## 知识库文件在哪里

Markdown 草稿默认写入：

```text
knowledge-base/daily/YYYY/MM/YYYY-MM-DD/
```

模板位置：

```text
knowledge-base/templates/project-note.md
```

生成草稿后，你可以直接让 Codex / Antigravity 基于该文件继续补全：

```text
请阅读这个项目链接和当前 Markdown 草稿，补全背景、核心能力、技术架构、安装使用、适合学习的点、风险和后续跟进建议。
```

复杂概念后续可以在 Markdown 里用 Mermaid 表达。v0.1 默认先生成 Markdown 文本，后续阶段再支持 Mermaid 渲染成 SVG / PNG。

## 飞书推送说明

飞书 Webhook 配置参考：

```text
docs/FEISHU_WEBHOOK.md
```

v0.1 的推送逻辑：

1. `scripts\daily_flow.cmd` 默认只预览，不发送。
2. 加 `--send` 才会真实发送飞书。
3. Web 页面上的 `标记已推送` 只是状态记录，不会调用飞书 Webhook。

如果只想单独测试飞书：

```powershell
.venv\Scripts\python scripts\push_today.py --limit 5
```

真实发送：

```powershell
.venv\Scripts\python scripts\push_today.py --send --limit 5
```

## 当前验证方式

### 验证本地整体状态

```powershell
scripts\doctor.cmd
```

### 验证每日流程可跑

```powershell
scripts\daily_flow.cmd --skip-rss --skip-github --skip-push --limit 3
```

### 验证 Web 页面可打开

1. 执行 `scripts\start_local.cmd`。
2. 打开 `http://127.0.0.1:3100`。
3. 页面能看到 Top Signals 和本地任务状态。

### 验证 Markdown 草稿生成

1. 在 Web 页面点击某个任务的 `生成 Markdown 草稿`。
2. 检查目录：

```text
knowledge-base/daily/YYYY/MM/YYYY-MM-DD/
```

3. 应该出现对应 `.md` 文件。

## 当前已完成能力

- 本地 SQLite 数据库初始化。
- GitHub 搜索源采集。
- RSS 源采集。
- GitHub repo snapshot 保存。
- AI 信号评分和排序。
- 今日任务生成。
- 飞书 Webhook 推送。
- Today Workspace 页面。
- 本地任务状态系统。
- Markdown 知识库提交记录。
- Markdown 草稿生成入口。
- 一键本地启动脚本。
- LAN 模式本地启动。
- 一键本地体检脚本。
- Web 操作成功 / 失败提示。
- Markdown 路径展示和复制。
- 今日时间和归档目录提示。

## 当前限制

- 暂时没有接入 LLM API Key 自动总结。
- 暂时不会自动阅读完整 GitHub 仓库、论文或长文档。
- 飞书推送只支持文本消息。
- 任务状态保存在本地 SQLite，不是云端同步。
- GitHub 热度增长目前依赖本地 snapshot，数据越持续跑越有价值。
- 完全免手动启动需要 Windows 计划任务、桌面应用壳或云端部署，v0.1 暂不主动修改系统启动项。

## 不要提交的内容

不要提交：

```text
.env
data/local.db
.venv/
apps/web/node_modules/
apps/web/.next/
真实 Webhook URL
API key
token
本地缓存
```

安全规则详见：

```text
docs/SECURITY_RULES.md
```

## 下一步建议

v0.1 目前已经可以本地闭环使用。下一步建议进入：

```text
Phase 13: 自动化运行与部署形态
```

重点优化：

1. Windows 计划任务或托盘程序，减少手动启动。
2. 局域网访问权限和防火墙提示。
3. Vercel / Supabase 云端形态。
4. API key 接入后的全自动总结。
5. 知识库文档渲染、搜索和同步到笔记工具。
