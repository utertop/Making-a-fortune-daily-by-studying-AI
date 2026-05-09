# NVIDIA API Key 最大收益接入方案

更新时间：2026-05-09

## 1. 结论

NVIDIA API key 值得接入，但不应该把它设计成“替代现有规则系统的万能大脑”。更成熟、可控的路线是：

1. 继续保留现有 GitHub / RSS / 规则评分 / 今日任务 / 归档目录作为稳定底座。
2. 用 NVIDIA OpenAI-compatible LLM 做三类增强：
   - 候选项目语义精排与过滤。
   - 自动生成研究计划、Markdown 草稿、质量检查意见。
   - 自动生成更有解释力的 Mermaid / C4 / sequence diagram 图形结构。
3. 对“最终入库”采用分阶段自动化：
   - 初期：LLM 自动写草稿，人确认入库。
   - 中期：高置信项目自动入库，低置信项目待确认。
   - 后期：形成模型质量评分与回归评测后，再扩大自动入库范围。

这能最大化利用免费 NVIDIA key，同时避免免费模型质量波动直接污染知识库。

## 2. 当前项目状态

当前已经具备的基础：

- `.env` 已配置 NVIDIA OpenAI-compatible 参数：
  - `AI_SIGNAL_RADAR_LLM_ENABLED=true`
  - `OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1`
  - `OPENAI_MODEL=openai/gpt-oss-20b`
  - `OPENAI_API_KEY` 已配置
- 后端已有 LLM client：
  - `apps/api/app/llm/client.py`
- 已有 LLM enrichment 流程：
  - `apps/api/app/llm/enrichment.py`
  - `scripts/enrich_signals.py`
  - `scripts/push_today.py --enrich`
- 已有 `signal_enrichment` 表和缓存逻辑。
- 飞书推送已能优先使用 `llm_reason`。

当前缺口：

- `signal_enrichment` 当前还没有实际数据。
- LLM 增强没有默认纳入 daily flow。
- 网页端没有显示 LLM 启用、调用结果、失败原因、置信度。
- 还没有“自动生成最终归档文档”的后端流水线。
- 还没有图形生成质量标准和自动检查。

## 3. 能力边界判断

### 3.1 NVIDIA key 能明确带来的收益

NVIDIA NIM / API Catalog 提供 OpenAI-compatible chat completions 接口。项目当前 client 使用 `/v1/chat/completions` 是正确方向。

适合交给 LLM 的任务：

- 语义判断：这个项目到底是不是 AI 相关，和 daily learning 是否有关。
- 精排：在规则打分相近的项目中判断哪个更值得深挖。
- 总结：把 README / docs / release / repo metadata 压缩成中文知识卡。
- 研究计划：告诉后续深挖应该看哪些文件、哪些问题要验证。
- 质量审查：检查 Markdown 是否缺来源、是否空泛、是否有幻觉风险。
- 图形结构设计：生成 Mermaid/C4/sequence diagram 的结构化草案。

### 3.2 NVIDIA key 不能直接保证的东西

不能假设：

- 免费模型稳定达到强模型文档质量。
- 模型自己能可靠浏览网页或读取仓库全部内容。
- 模型生成的图天然有深度。
- 一次调用就能生成最终可入库文档。

关键原则：

LLM 只负责“判断和写作”，事实必须来自系统抓取的 evidence pack。不要让模型凭记忆写项目事实。

## 4. 产品目标拆解

你的目标可以拆成三条线：

### 4.1 热点项目识别增强

目标：在现有规则基础上，提高“值得学习”的命中率，降低噪声。

保留规则层：

- stars、forks、delta、language、license、最近提交、AI keyword、RSS source。

新增 LLM 层：

- `ai_category`
- `project_type`
- `relevance`
- `priority`
- `llm_score`
- `reason`
- `risk`
- `suggested_action`

融合方式：

```text
final_score = rule_score * 0.75 + normalized_llm_score * 0.25
```

第一阶段不要让 LLM 覆盖规则分，只做增强排序和解释。等积累评测数据后，再调整权重。

### 4.2 自动生成最终归档文档

目标：从“把 prompt 发给 Codex/Antigravity”变成后端自动生成 Markdown，并可直接入库。

推荐流水线：

```text
候选任务
  -> evidence pack 抓取
  -> LLM 研究计划
  -> LLM 初稿生成
  -> LLM 自检与修订
  -> 规则质量检查
  -> 入库策略判断
  -> 自动入库或待确认
```

其中 evidence pack 是成败关键。

最低 evidence pack：

- GitHub repo metadata
- README
- docs 链接或 docs 主页摘要
- release / changelog
- license
- examples / quickstart
- 最近 commit 信息
- package metadata，如存在

不要让模型直接写“我觉得这个项目是什么”。要让模型基于 evidence pack 写“从这些来源能确认什么”。

### 4.3 图形生成增强

目标：不是生成更花哨的图，而是生成更能帮助理解的图。

成熟方案不是直接让 LLM 输出一张图，而是三步：

```text
文本证据
  -> diagram spec
  -> Mermaid / C4 / sequence diagram
  -> 自动校验与二次修订
```

图形类型按内容选择：

- 架构型项目：C4 container / component diagram。
- Agent 框架：workflow / sequence diagram。
- RAG / 数据管线：data flow diagram。
- SDK / library：API call sequence。
- 模型服务：request lifecycle / deployment topology。

图形质量标准：

- 至少 5 个真实组件。
- 节点必须来自 evidence pack。
- 边必须表达具体数据流、控制流或调用关系。
- 图后面必须有“图中每个节点的来源依据”。
- Mermaid 必须能通过语法检查。

NVIDIA key 可以提升“图的结构思考”，但不能保证一次生成好图。必须做 diagram critique 和 regenerate。

## 5. 推荐自动化等级

### L0：当前半自动

系统生成草稿和 Prompt，人把 Prompt 发给强模型或网页 AI，再手动写回本地。

优点：质量可控。
缺点：链路割裂，不是真自动。

### L1：LLM 辅助筛选

自动跑 `signal_enrichment`，只增强候选排序和推送理由。

入库仍然人工。

这是下一步最稳的落点。

### L2：LLM 自动生成草稿

点击“自动生成归档草稿”，后端调用 NVIDIA API 生成完整 Markdown。

状态进入：

```text
draft_created -> review_pending
```

仍需人工确认。

### L3：高置信自动入库

当满足以下条件时自动入库：

- evidence pack 完整度 >= 80
- LLM 质量分 >= 85
- 规则质量检查通过
- 没有 placeholder
- 来源链接 >= 3
- Mermaid 校验通过
- 项目不是安全/法律/医疗等高风险主题

否则进入待确认。

### L4：全自动归档

只建议在连续一段时间评测稳定后启用。比如连续 50 篇自动文档中，人工回退率低于 10%。

## 6. 技术架构方案

### 6.1 新增后端模块

```text
apps/api/app/llm/
  client.py                 # 已有
  enrichment.py             # 已有
  document_generator.py     # 新增：生成最终 Markdown
  evidence.py               # 新增：抓取和压缩证据包
  diagram.py                # 新增：图形 spec + Mermaid 生成
  quality_review.py         # 新增：LLM 质量审查
  budgets.py                # 新增：调用预算、限流、重试
```

### 6.2 新增数据表

建议新增：

```sql
document_generation_run (
  id,
  task_id,
  signal_id,
  provider,
  model,
  status,
  evidence_hash,
  quality_score,
  auto_archive_allowed,
  error,
  created_at,
  updated_at
)
```

```sql
evidence_snapshot (
  id,
  signal_id,
  source_url,
  source_type,
  content_hash,
  excerpt,
  metadata_json,
  created_at
)
```

```sql
llm_call_log (
  id,
  purpose,
  provider,
  model,
  input_hash,
  output_hash,
  prompt_tokens,
  completion_tokens,
  status,
  error,
  created_at
)
```

注意：不要存 API key，不要把完整敏感请求体写入 log。

### 6.3 新增 API

```text
GET  /llm/status
POST /signals/enrich
POST /tasks/{task_id}/auto-draft
POST /tasks/{task_id}/auto-document
POST /tasks/{task_id}/llm-quality-review
POST /tasks/{task_id}/diagram
```

`/llm/status` 只返回：

```json
{
  "enabled": true,
  "provider": "openai-compatible",
  "base_url_host": "integrate.api.nvidia.com",
  "model": "openai/gpt-oss-20b",
  "has_api_key": true
}
```

不能返回 key 内容。

## 7. 文档生成 Prompt 设计

不能只靠一个大 prompt。建议拆成四段。

### 7.1 研究计划 Prompt

输入：

- repo metadata
- README 摘要
- docs / changelog / examples 摘要
- 当前规则评分原因

输出 JSON：

```json
{
  "research_questions": [],
  "must_verify": [],
  "likely_architecture": "",
  "diagram_type": "",
  "missing_evidence": []
}
```

### 7.2 文档初稿 Prompt

输入：

- evidence pack
- research plan
- knowledge-base 模板

输出 Markdown。

硬性要求：

- 每个关键结论带来源。
- 不确定的信息必须写进“待确认”。
- 不能写 evidence pack 没有的事实。

### 7.3 图形生成 Prompt

先输出 diagram spec：

```json
{
  "diagram_type": "sequence",
  "nodes": [],
  "edges": [],
  "evidence_refs": []
}
```

再输出 Mermaid。

### 7.4 质量审查 Prompt

输出：

```json
{
  "status": "pass | pass_with_warnings | needs_work",
  "score": 0,
  "issues": [],
  "warnings": [],
  "auto_archive_allowed": false
}
```

## 8. 质量评估方法

你担心“能否达到强模型 70% ~ 80%”是合理的。这个不能靠感觉，需要做评测集。

建议建立 20 篇 gold docs：

- 10 篇你已经认可的手工/强模型文档。
- 5 篇复杂项目。
- 5 篇简单项目。

评测维度：

| 维度 | 权重 |
|---|---:|
| 事实准确 | 30 |
| 来源充分 | 20 |
| 结构完整 | 15 |
| 原理解释 | 15 |
| 图形帮助理解 | 10 |
| 可读性 | 10 |

达标线：

- 平均分 >= gold doc 的 75%，可以进入 L2。
- 自动入库文档人工返工率 < 20%，可以进入 L3 小范围。
- 自动入库文档人工返工率 < 10%，再考虑 L4。

## 9. 分阶段实施计划

### Phase 1：先把 key 用起来，但只用于筛选增强

目标：让 NVIDIA key 先产生可见收益，风险最低。

任务：

1. 增加 `/llm/status`。
2. 增加页面 LLM 状态提示。
3. 把 `scripts/enrich_signals.py` 接入 daily flow。
4. 在今日候选卡片显示：
   - LLM 分类
   - LLM 推荐优先级
   - LLM 简短理由
   - LLM 风险
5. 推送默认可配置是否 `--enrich`。

完成标志：

- 每天候选信号有 LLM reason。
- 推送文案优先使用更自然的 AI reason。
- `signal_enrichment` 有稳定数据。

### Phase 2：自动生成归档草稿

目标：替代“复制 Prompt 到外部 AI”的半自动链路。

任务：

1. 新增 evidence pack 抓取器。
2. 新增 `POST /tasks/{task_id}/auto-draft`。
3. 自动生成 Markdown 到目标路径。
4. 状态变成 `review_pending`。
5. 页面增加“自动生成归档草稿”按钮。

完成标志：

- 不离开网页即可得到完整草稿。
- 人只需要审阅和确认。

### Phase 3：图形生成增强

目标：让图真正帮助理解。

任务：

1. 新增 diagram spec schema。
2. 新增 Mermaid 生成和语法检查。
3. 新增 diagram critique 二次修订。
4. 文档中自动插入图与图解。

完成标志：

- 图中组件来自证据包。
- Mermaid 可渲染。
- 图后有来源说明。

### Phase 4：高置信自动入库

目标：实现有限范围的真正自动归档。

任务：

1. 新增 auto archive policy。
2. 高置信文档自动 `documented`。
3. 低置信文档继续进入 `review_pending`。
4. 页面显示“自动入库原因 / 阻止入库原因”。

完成标志：

- 简单项目可自动闭环。
- 复杂项目仍保留人工确认。

## 10. 风险与控制

### 10.1 幻觉风险

控制：

- 所有事实来自 evidence pack。
- 文档必须有来源链接。
- LLM 审查不能替代规则检查。

### 10.2 免费 key 配额与稳定性

控制：

- daily limit。
- 缓存 input_hash。
- 失败不阻断 daily flow。
- 每个 task 可重试，但不能无限重试。

### 10.3 模型质量波动

控制：

- 每次记录 model。
- 质量分与人工反馈绑定。
- 支持以后切换更强模型。

### 10.4 图形低质量

控制：

- 先生成 spec，再生成 Mermaid。
- 图形必须通过检查。
- 不达标就不插图，而不是插一张低质量图。

## 11. 推荐下一步

下一步不要直接做“全自动写最终文档”。跨度太大，风险也高。

建议先做：

```text
Phase 1：LLM 状态页 + enrich 默认接入今日候选
```

具体第一项：

1. 新增 `GET /llm/status`。
2. 今日页面显示 LLM 状态。
3. 增加“运行 LLM 增强”按钮。
4. 候选卡片展示 LLM reason / risk / priority。
5. `daily_flow` 增加 `--enrich` 参数。

这一步完成后，你能马上看到 NVIDIA key 对“热点项目识别”的收益，同时不会污染最终知识库。

## 12. 参考

- NVIDIA NIM LLM API 支持 OpenAI-compatible `/v1/chat/completions`、`/v1/models` 等接口：https://docs.nvidia.com/nim/large-language-models/2.0.3/reference/api-reference.html
- NVIDIA API Catalog 的 hosted endpoint 为 `https://integrate.api.nvidia.com/v1/chat/completions`，并声明兼容 OpenAI：https://docs.api.nvidia.com/nim/reference/create_chat_completion_v1_chat_completions_post
- NVIDIA LLM API overview：https://docs.api.nvidia.com/nim/reference/llm-apis
