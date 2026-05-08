# LLM API Key 接入规划

这份文档说明 AI Signal Radar 应该如何接入 API key，用轻量模型提升项目筛选、每日推送、深挖任务和 Markdown 归档质量。

核心原则：API key 不是用来否定现有规则，而是作为规则之后的“增强判断层”。现有的 stars、language、license、RSS 关键词、文档模板和任务流仍然是系统的稳定底座；LLM 负责补足语义判断、总结表达、研究路径和文档质量建议。

## 1. 接入定位

当前系统已经具备这些能力：

- GitHub / RSS / HN 等信号采集
- 基于 stars、star delta、language、license、活跃度、RSS 关键词的规则评分
- 飞书每日推送
- 高能量项目持续追踪，直到深挖和归档完成
- Markdown 模板生成
- Markdown 归档质量检查
- 适合 deep project dossier 的 skill 化总结工作流

API key 接入后，应该增强这些能力，而不是替换它们。

不应该替换：

- GitHub delta 评分
- RSS 关键词评分
- license / language / activity 判断
- pushed / documented / ignored / archived 等任务状态逻辑
- Markdown 模板
- 人的最终判断和归档动作

推荐的数据流：

```text
原始信号
  -> 规则评分
  -> LLM 轻量增强
  -> 飞书推荐理由
  -> 人工选择深挖
  -> skill 生成结构化总结
  -> 规则 + LLM 质量检查
  -> 归档
```

## 2. API Key 最应该提升什么

### 2.1 项目相关性判断

规则能判断“热不热”，但不一定能判断“值不值得你今天看”。

LLM 应该补充判断：

- 这个项目是否真的和 AI 有关？
- 它属于 coding agent、RAG、模型服务、推理优化、评测、工作流自动化、AI UI 还是开发者工具？
- 它是实用产品、底层框架、论文实现、资源列表、玩具项目，还是营销页？
- 它适合今天深挖，还是只适合观察？

建议输出结构：

```json
{
  "ai_category": "coding-agent",
  "project_type": "tool",
  "relevance": "high",
  "priority": "must_read",
  "reason": "项目和 coding agent 工作流直接相关，近期增长明显，适合用于观察 agent 工具链趋势。",
  "risk": "可能更偏资源整理，需要确认是否有原创实现。"
}
```

### 2.2 相似项目聚类

现在 GitHub 热门项目容易重复出现，规则可以降权，但不能很好理解“这些项目其实属于同一类趋势”。

LLM 可以把候选项目聚类成：

- Agent workflow 平台
- 本地模型运行和 UI
- RAG / 知识库工具
- Eval / benchmark / observability
- Prompt / agent 资源库
- 模型推理和部署

这样飞书推送就不只是 Top 10，而是“今天 AI 技术雷达里出现了哪些趋势”。

### 2.3 “为什么推给你”

目前规则可以生成理由，例如：

```text
理由：7 天新增 6071 stars，最近仍活跃，TypeScript 项目，可用于 agent 工具链观察。
```

LLM 可以把规则理由变得更像人的判断：

```text
理由：这个项目不是单纯涨星，而是同时命中 agent workflow、开发者工具和近期高活跃三个信号，适合今天进入深挖队列。
```

但注意：LLM 的理由必须基于已有字段，不允许凭空补事实。

## 3. 轻量 API Key 的现实策略

你现在没有特别强的 Gemini / ChatGPT 大模型 key，所以不能把系统设计成“全靠模型理解一切”。

正确方式是：让规则先把问题缩小，再让轻量模型做小而清晰的判断。

### 3.1 只让模型做小任务

不要问：

```text
请分析今天所有 AI 项目，告诉我最值得关注的 10 个。
```

应该问：

```text
根据以下结构化信息，判断这个项目是否值得深挖，并返回 JSON。
```

输入只给必要字段：

- title
- url
- description
- language
- license
- stars
- stars_delta_24h
- stars_delta_7d
- pushed_at
- source
- rule_score
- rule_reasons

轻量模型更适合在清晰边界内做分类、摘要和风险提示。

### 3.2 规则先过滤，模型只分析少量候选

建议每天：

- 规则先筛出 30-50 条候选
- 模型只分析前 10-20 条
- 飞书最终仍推 10 条
- 已归档、已跳过、低相关项目不消耗模型调用

这样低成本也能有比较好的效果。

### 3.3 固定标签体系

轻模型最怕开放式发挥。应该给它固定选项：

```json
{
  "ai_category": [
    "coding-agent",
    "rag",
    "model-serving",
    "evaluation",
    "workflow-automation",
    "developer-tool",
    "ai-ui",
    "research",
    "other"
  ],
  "priority": ["must_read", "track", "skip"],
  "project_type": ["product", "framework", "library", "resource-list", "paper-implementation", "benchmark", "toy", "unknown"]
}
```

模型只能从固定标签里选，系统再校验 JSON。这样即使模型不强，也能把稳定性拉起来。

### 3.4 输出必须可验证

LLM 输出只作为增强，不直接覆盖规则。

可以采用加权方式：

```text
final_score = rule_score * 0.75 + llm_score * 0.25
```

如果 LLM 输出解析失败、超时、字段缺失，就直接回退到 rule_score。

## 4. 推荐架构

建议新增模块：

```text
apps/api/app/llm/
  __init__.py
  client.py
  prompts.py
  schemas.py
  enrichment.py
```

职责划分：

- `client.py`：统一处理 API base url、model、timeout、retry
- `prompts.py`：保存短 prompt，不把 prompt 散落在业务代码里
- `schemas.py`：定义返回 JSON schema 和校验逻辑
- `enrichment.py`：把 signal 转成 LLM 输入，解析输出并写入数据库

建议环境变量：

```env
AI_SIGNAL_RADAR_LLM_ENABLED=false
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
AI_SIGNAL_RADAR_LLM_TIMEOUT_SECONDS=20
AI_SIGNAL_RADAR_LLM_DAILY_LIMIT=20
AI_SIGNAL_RADAR_LLM_MAX_OUTPUT_TOKENS=500
AI_SIGNAL_RADAR_LLM_TEMPERATURE=0.2
```

这里用 OpenAI-compatible 接口设计，不绑定某一家供应商。以后你有更强 key，可以只换 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

## 5. 数据库存储

建议新增 `signal_enrichment` 表：

```sql
CREATE TABLE signal_enrichment (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  ai_category TEXT,
  project_type TEXT,
  relevance TEXT,
  priority TEXT,
  llm_score REAL,
  reason TEXT,
  risk TEXT,
  suggested_action TEXT,
  raw_json TEXT,
  created_at TEXT NOT NULL
);
```

关键点：

- 用 `input_hash` 缓存，避免重复花钱
- 保留 `raw_json`，方便后续排查模型质量
- 不直接改写原始 signal，避免污染规则数据

## 6. 对每日飞书推送的增强

飞书推送应该继续分块：

- 新出现 GitHub
- 持续升温 GitHub
- 官方 / RSS 动态
- 待深挖追踪
- 待归档追踪
- 补充候选

LLM 接入后，每条可以多一段更自然的理由：

```text
1. openai/codex
   规则：7 天新增 6071 stars，最近仍活跃，TypeScript 项目。
   AI 判断：coding-agent / developer-tool / must_read。
   理由：它和 agent 编程工作流直接相关，增长不是孤立热度，适合进入深挖队列。
```

注意：飞书不要变长。LLM 的价值不是写更多，而是写得更准。

## 7. 对高能量项目追踪的增强

你之前的方向是对的：

高能量项目不应该被简单冷却掉，而应该被追踪到完成；完成后安静，除非真的出现新变化。

LLM 可以帮助判断“新变化是否足够重要”：

- README 是否显著变化
- release 是否引入关键能力
- stars_delta 是否异常升高
- issue / discussion 是否出现重要方向
- 是否从资源列表变成实际产品

归档后再次推送的条件可以是：

```text
规则触发：7 天 star delta 超过阈值 / 最近 push 很活跃 / release 更新
LLM 判断：变化和原归档结论相比有新增价值
```

这样既不骚扰，也不错过真正变强的项目。

## 8. 对 skill 总结文档的增强

现在项目已有 Markdown 模板和 deep project dossier 思路。API key 不应该替代 skill，而应该帮 skill 准备更好的输入。

推荐工作流：

```text
选择项目深挖
  -> LLM 生成 research plan
  -> skill 按模板写 deep dossier
  -> 规则检查 Markdown 完整性
  -> LLM 做质量审阅
  -> 人工补充判断
  -> 归档
```

LLM 可以先生成研究计划：

```json
{
  "research_questions": [
    "这个项目解决的核心问题是什么？",
    "它和已有 agent framework 的差异在哪里？",
    "它的真实使用场景是什么？",
    "它的风险是维护性、商业化，还是技术路线？"
  ],
  "sections_to_emphasize": [
    "Use Cases",
    "Technical Architecture",
    "Adoption Signals",
    "Opportunity Notes"
  ],
  "missing_context": [
    "需要查看 README 和 release notes",
    "需要确认 license 是否允许商业使用"
  ]
}
```

这样 skill 输出的总结文档会更聚焦，而不是只把模板填满。

## 9. 文档质量审阅

已有规则质量检查适合发现结构问题，例如：

- 标题缺失
- 章节缺失
- 字数太少
- 没有 opportunity
- 没有 risk

LLM 更适合补充语义质量检查：

- 结论是否具体？
- 是否只是复述 README？
- 是否写出了你为什么要关注它？
- 是否区分了事实、推断和机会？
- 是否有可执行的下一步？

建议输出：

```json
{
  "quality_score": 82,
  "summary": "文档结构完整，但机会判断还不够具体。",
  "strengths": [
    "清楚说明了项目用途",
    "列出了技术栈和适用场景"
  ],
  "fixes": [
    "补充和同类项目的差异",
    "把商业机会从泛泛描述改成具体可验证假设",
    "补充 license 风险"
  ]
}
```

## 10. 如何接近强模型 70-80% 的效果

在轻量 key 条件下，想接近强模型 70-80% 的效果，关键不是换更复杂 prompt，而是把系统设计成“规则 + 结构化输入 + 小任务 + 缓存 + 人审”。

推荐策略：

- 规则负责召回，避免漏掉明显强信号
- LLM 负责精排，避免把无关热榜推给你
- 固定标签，减少模型自由发挥
- JSON 输出，减少幻觉和格式问题
- 每天只分析少量高分候选
- 低置信度时回退规则
- 对已归档项目只分析“变化摘要”，不重新全量分析
- 保留人工反馈，后续可用于调整规则权重

轻量模型最适合做：

- 分类
- 简短理由
- 风险提示
- 文档改进建议
- 去营销化摘要
- 把规则信号翻译成人能快速判断的语言

轻量模型不适合做：

- 无上下文地判断项目真实价值
- 长篇深度研究
- 代替你做最终投资 / 产品判断
- 在没有 README / release / issue 数据时凭空分析

## 11. 成本和稳定性控制

默认限制建议：

```env
AI_SIGNAL_RADAR_LLM_DAILY_LIMIT=20
AI_SIGNAL_RADAR_LLM_TIMEOUT_SECONDS=20
AI_SIGNAL_RADAR_LLM_MAX_OUTPUT_TOKENS=500
AI_SIGNAL_RADAR_LLM_TEMPERATURE=0.2
```

工程策略：

- API key 默认关闭，显式开启
- 所有 LLM 调用可失败、可跳过
- 失败不影响每日推送
- 结果缓存，避免重复调用
- prompt 保持短
- 只传结构化字段，不传大量无关文本
- 后续可对 README 摘要单独做二级增强

## 12. 最小实现路线

### Phase 1：信号增强

- 新增 LLM client
- 新增 enrichment schema
- 新增 `signal_enrichment` 表
- 新增 `scripts/enrich_signals.py`
- 只增强每日规则 Top 20
- 飞书中展示 AI 分类、优先级和一句理由

### Phase 2：深挖计划

- 新增 `POST /tasks/{task_id}/research-plan`
- 为待深挖项目生成研究问题
- Web 工作台展示 research plan
- deep dossier 使用 research plan 作为输入

### Phase 3：文档审阅

- 新增 `POST /tasks/{task_id}/llm-quality-review`
- 在规则质量检查之后运行
- 输出质量分、优点和修改建议
- Web 工作台展示审阅结果

### Phase 4：学习记忆

- 记录最近 7 / 30 天已深挖主题
- 减少重复类别
- 推荐本周欠缺的方向
- 生成周度 AI 学习地图

## 13. 成功标准

接入 API key 后，应该达到这些效果：

- 飞书每日 10 条更像“精选”，不是热榜搬运
- 重复但未完成的高能量项目会继续追踪
- 已归档项目保持安静，除非有明显新变化
- RSS 官方动态能区分重要发布和普通营销
- 每条推荐都有清晰的“为什么推给你”
- 深挖 Markdown 更像研究文档，而不是信息堆叠
- 没有 API key 时系统仍然能完整运行

## 14. 最重要的原则

规则提供稳定性。

模板提供结构。

Skill 提供研究工作流。

LLM 提供语义判断和表达质量。

人提供最终判断。

这个项目最好的状态不是“全自动替你决定”，而是每天把值得你判断的东西更准确、更有条理地送到你面前。
