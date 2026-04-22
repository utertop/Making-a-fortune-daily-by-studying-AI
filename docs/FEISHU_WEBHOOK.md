# 飞书 Webhook 配置说明

本项目 v0.1 使用飞书自定义机器人 Webhook 来推送“今日 AI 学习任务”。

## 1. 创建飞书群

1. 打开飞书。
2. 创建一个新的群聊。
3. 这个群可以只有你自己，用作个人 AI 学习提醒群。
4. 建议群名：

```text
AI Signal Radar
```

## 2. 添加自定义机器人

1. 进入刚创建的飞书群。
2. 打开群设置。
3. 找到“机器人”或“群机器人”。
4. 添加“自定义机器人”。
5. 机器人名称可以填写：

```text
AI Signal Radar Bot
```

6. 创建后复制 Webhook 地址。

Webhook 通常长这样：

```text
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## 3. 配置本地 `.env`

先从 `.env.example` 复制一份本地配置文件：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，填入你的飞书 Webhook：

```text
PUSH_CHANNEL=feishu
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
FEISHU_WEBHOOK_SECRET=
```

注意：

- 不要把真实 `.env` 提交到 Git。
- 不要把真实 Webhook 写入 Markdown 文档。
- `.gitignore` 已经排除了 `.env`。

## 4. 先预览，不发送

建议先 dry-run 预览消息内容：

```powershell
.venv\Scripts\python scripts\push_today.py --limit 5
```

这个命令只会在终端打印消息，不会发送到飞书。

## 5. 真实发送测试消息

确认 `.env` 配好后，执行：

```powershell
.venv\Scripts\python scripts\push_today.py --send --limit 5
```

预期结果：

- 飞书群收到一条“今日 AI 学习任务”。
- 消息里包含 Top Signals。
- 消息里包含 Today Workspace 入口。

## 6. 安全设置

飞书自定义机器人可能支持额外安全设置，比如：

- 关键词校验
- 签名校验
- IP 白名单

v0.1 最简单的方式是只配置 Webhook。

如果后续开启签名校验，可以把密钥放到：

```text
FEISHU_WEBHOOK_SECRET=
```

不要把密钥写入文档，也不要提交到 Git。

## 7. 常见问题

### 没收到飞书消息

检查：

- 项目根目录是否存在 `.env`。
- `FEISHU_WEBHOOK_URL` 是否为空。
- Webhook 是否以 `https://open.feishu.cn/open-apis/bot/v2/hook/` 开头。
- 是否执行了 `--send`，dry-run 不会发送。

### 飞书返回权限或安全错误

检查：

- 机器人是否开启了关键词校验。
- 消息内容是否包含飞书要求的关键词。
- 是否开启了签名校验，但没有配置 `FEISHU_WEBHOOK_SECRET`。
- 是否设置了 IP 白名单导致本机请求被拒绝。

### 网络错误

如果在沙箱环境里发送失败，可以在你的普通终端里执行同样命令。

## 8. 当前 v0.1 命令汇总

预览消息：

```powershell
.venv\Scripts\python scripts\push_today.py --limit 5
```

真实发送：

```powershell
.venv\Scripts\python scripts\push_today.py --send --limit 10
```
