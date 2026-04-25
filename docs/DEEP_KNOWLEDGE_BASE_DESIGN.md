# Deep Knowledge Base Design

这份文档用于定义下一阶段“深度知识库生成能力”的边界与升级方向。

它要回答的核心问题不是“怎么把 prompt 写得更长”，而是：

```text
如何让系统输出成熟、完整、可反复阅读、可继续补深的知识库文档？
```

---

## 1. 现状判断

当前的 `$knowledge-base-writer` 更接近：

```text
把已有草稿补成一篇结构完整、来源清晰、格式统一的项目笔记
```

它擅长：

1. 把 README / docs / release / changelog 整理成标准 Markdown
2. 避免编造安装命令、license、benchmark、架构细节
3. 保持本项目知识库格式一致
4. 支撑半自动流程稳定落地

但它不擅长：

1. 深入理解项目内部机制
2. 从 docs + code + config + examples 中提炼系统级认识
3. 生成适合长期学习和反复复盘的深度知识库
4. 输出更完整的架构、模块、工作流、优缺点、适用边界与实战路径

所以当前它更像：

```text
高质量结构化摘要 / 工程笔记
```

而不是：

```text
成熟知识库 / 项目理解手册 / 深度学习文档
```

---

## 2. 问题本质

问题不只是提示词不够长，而是任务定义太浅。

当前轻量 skill 默认做的是：

```text
source summarization
```

而你真正要的深度知识库需要的是：

```text
source understanding
+ project understanding
+ architecture extraction
+ workflow reconstruction
+ practical learning guidance
+ knowledge-base authoring
```

也就是说，深度知识库的任务本质是：

```text
研究 -> 理解 -> 拆解 -> 重组 -> 成文
```

---

## 3. 目标定义

最终输出应满足：

1. 从浅到深可阅读
   - 先解释它是什么
   - 再解释为什么重要
   - 再解释核心概念
   - 再解释架构、模块、工作流
   - 再解释如何使用、何时使用、不适合什么场景

2. 帮助真正理解项目
   - 不只是知道“它很火”
   - 而是知道“它为何这样组织、关键机制是什么、适合什么场景”

3. 能用于后续复习
   - 一周后再看仍能快速回忆
   - 一个月后再看还能继续补深

4. 能作为团队知识资产
   - 不只是个人随手笔记
   - 而是可沉淀、可索引、可继续扩写的知识文档

---

## 4. 总体设计结论

保留两层产品形态，但不拆成两个 deep skill：

### Layer A: Signal Note

用于：

```text
快速记录热点项目，适合当天跟进
```

对应：

```text
$knowledge-base-writer
```

### Layer B: Deep Project Dossier

用于：

```text
对重点项目做系统研究，输出成熟知识库文档
```

对应：

```text
$deep-project-dossier
```

注意：

```text
不再拆成 deep_dossier 和 deep_code_dossier 两个 skill。
源码级补深是 $deep-project-dossier 内部的条件增强层，而不是另一个独立 skill。
```

这样做的原因：

1. 知识库目标本来就是一体的，拆 skill 会把同一个项目割裂开。
2. 源码只是深度研究中的一种重要信源，不是另一类完全独立产品。
3. 拆 skill 容易让“代码更深”与“整体理解更完整”分离，反而削弱成熟度。

---

## 5. 一个 Deep Skill 的内部判断逻辑

`$deep-project-dossier` 保持为唯一的深度知识库 skill。

但它内部要具备“源码分析是否适用”的判断逻辑。

### 5.1 默认目标

无论项目类型如何，deep skill 都应尽量覆盖：

1. 项目定位
2. 核心概念
3. 用户工作流
4. 架构总览
5. 关键模块
6. 配置与扩展
7. 实战路径
8. 优势 / 局限 / 风险
9. 对比与学习建议

### 5.2 何时启用源码级补深

当满足以下条件时，应主动进入源码级增强分析：

1. repo 中存在真实实现代码，而不是只有 landing 内容
2. 仓库目录结构清晰，可识别关键模块或入口
3. 项目核心价值明显体现在代码组织、runtime、模块边界或调用链中
4. 仅靠 docs 不足以支撑完整理解

### 5.3 何时不强行做源码分析

当出现以下情况时，不应硬写源码层：

1. 项目主要是论文、文档、规范或方法论
2. repo 代码极少、核心实现未公开，或只是展示仓库
3. 代码不是该项目主要学习价值来源
4. 公开信息不足以支持可靠的模块级判断

### 5.4 对“不适合源码分析”的项目应该怎么写

不要把“没有代码可分析”直接等同于“项目不成熟”或“无法做深度文档”。

更好的做法是：

```text
明确说明：本项目本轮更适合从文档、方法、工作流、产品形态或研究思路层面做深度理解；
源码层暂无足够公开实现，或不作为本轮重点。
```

---

## 6. 深度研究所需的阅读层次

深度文档至少应覆盖以下阅读层：

### 6.1 基础层

必须读：

1. README
2. Docs 首页
3. 安装文档
4. Release / changelog

### 6.2 结构层

应读：

1. 顶层目录
2. 关键子目录
3. package / workspace / config 文件
4. 明显的 agent / skill / plugin / sdk 目录

### 6.3 机制层

应读：

1. 配置机制
2. 扩展机制
3. 权限机制
4. agent / workflow 定义

### 6.4 源码层（条件触发）

仅当代码是关键强信源时再读：

1. 入口文件
2. runtime 或 orchestration 模块
3. provider / tool / plugin / adapter 接线位置
4. 持久化、session、workspace、state 相关实现

### 6.5 实战层

应读：

1. Quick start
2. 使用示例
3. 多入口（CLI / Web / IDE / Desktop / SDK / Slack 等）
4. 已知限制与部署/权限/网络注意事项

---

## 7. 图形化要求

深度知识库不能只有文字，也不能只有装饰图。

建议图形化至少分三类：

### 7.1 总体架构图

回答：

```text
系统由哪些大块组成？
```

### 7.2 工作流图

回答：

```text
用户操作 -> agent -> tool -> model -> output 如何流动？
```

### 7.3 模块关系图

回答：

```text
目录 / 模块 / 服务之间如何协作？
```

当前阶段可继续用 Mermaid。  
后续可升级为：

```text
Mermaid -> SVG / PNG
```

---

## 8. 半自动阶段如何落地

当前不建议一口气做全自动深度研究。

推荐半自动流程：

```text
1. 页面生成草稿
2. 页面生成标准 Prompt
3. 你用 Codex / Antigravity 触发 $deep-project-dossier
4. Agent 输出 Deep Project Dossier
5. 页面检测到文档更新
6. 你审核后确认提交
```

也就是说，现阶段先实现：

```text
Prompt + 深度模板 + 深度 skill
```

后续再接：

```text
API key + 全自动多步研究流
```

---

## 9. 实现对象

### 9.1 继续保留 `$knowledge-base-writer`

用途：

```text
补已有草稿，生成标准项目笔记
```

### 9.2 建立 `$deep-project-dossier`

用途：

```text
对重点项目做系统研究，输出成熟知识库文档
```

内部规则：

```text
默认覆盖产品、工作流、架构、模块、配置、实战与风险；
当代码仓库真实存在且代码是关键强信源时，再补充源码级模块、调用链、目录与配置分析；
当代码不足、代码不关键或代码不公开时，不强行展开源码分析，而是明确说明原因。
```

### 9.3 页面后续支持两种 Prompt

建议页面支持：

1. `生成标准 Prompt`
2. `生成深度研究 Prompt`

这样你可以自己决定：

1. 今天只是快速记一篇
2. 还是这个项目值得做深度研究

---

## 10. 建议的下一个实现顺序

### Phase KB-1

完善深度模板 `deep-project-dossier.md`

### Phase KB-2

完善 `$deep-project-dossier` 规则与参考资料

### Phase KB-3

页面增加 `生成深度研究 Prompt`

### Phase KB-4

拿真实项目试跑并回调模板与 skill  
当前样本：

```text
anomalyco/opencode
```

### Phase KB-5

在适合的项目上继续做源码级补深验证

---

## 11. 审核结论

当前结论很明确：

```text
$knowledge-base-writer 适合作为标准知识笔记 skill；
$deep-project-dossier 适合作为重点项目的深度知识库生成能力；
源码级补深应作为 $deep-project-dossier 内部的条件增强层，而不是另一个独立 skill。
```

深度知识库生成的正确形态应是：

```text
多步 agent 研究工作流
```

而不是：

```text
单步长 prompt 摘要
```
