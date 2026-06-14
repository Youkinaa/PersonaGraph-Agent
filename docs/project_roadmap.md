# PersonaGraph Career Agent 项目路线图

本文档是项目阶段规划的单一事实来源。后续每推进一个 Phase，都要同步更新对应阶段的“已完成、当前边界、后续优化、验收方式”，避免把已做内容、当前目标和未来优化混在一起。

## 0. 项目定位

PersonaGraph Career Agent 是一个面向求职场景的个人职业智能体平台。

它不是“上传 PDF 后问答”的普通 RAG demo，而是围绕求职全过程构建的工作流系统：

- 管理简历、JD、项目材料、公司资料、面试笔记和学习资料。
- 将文档解析成 parent section 和 child chunk。
- 使用 Hybrid RAG 找到可追溯证据。
- 后续使用 Neo4j 构建职业知识图谱。
- 使用 LangGraph 编排 JD 匹配、简历改写、学习路线、岗位发现等 workflow。
- 使用 Celery 执行文档解析、索引构建、岗位扫描、主动提醒等异步任务。
- 后续使用 SKILL.md 动态加载职业场景技能。
- 后续使用长期记忆维护用户偏好、项目背景、职业目标和历史决策。

核心设计：

```text
能力池 + 意图路由 + 按需编排
```

当前主线只保留“求职助手”。旅行规划、通用 GitHub 仓库分析、通用研究报告作为独立场景废弃；其中有价值的能力迁移到项目经历分析、岗位要求分析、学习路线规划和主动岗位提醒中。

## 1. 技术栈

后端与页面：

- FastAPI
- Jinja2
- HTMX
- Pydantic Settings
- SQLAlchemy 2.x
- Alembic

任务与运行时：

- Redis
- Celery
- 后续 Celery Beat

数据与检索：

- PostgreSQL：主业务库和事实源。
- Elasticsearch：BM25 / 全文检索。
- Milvus：child chunk 向量检索。
- Neo4j：职业知识图谱和 GraphRAG。

Agent 与工作流：

- LangChain：LLM、loader、tool、retriever 组件。
- LangGraph：多步骤 workflow 编排。
- SKILL.md Runtime：动态技能系统。
- MCP / Tool Gateway：外部工具接入。

后续工程治理：

- Docker Compose
- SSE 流式输出
- 限流
- 重试
- 审计日志
- 结构化日志
- OpenTelemetry / Prometheus / Grafana

## 2. 当前评估方式

### 当前已经有的评估

当前还没有完整 Retrieval Eval，也没有自动生成评估集。

目前主要靠三类验证：

- 单元测试：验证 embedding fallback、RRF、rerank endpoint、rerank response parsing、index versioning 等纯逻辑。
- Smoke test：用 TestClient 或真实本地服务检查 `/health`、`/rag`、`/api/rag/indexes/status` 等接口是否正常。
- 人工观察：在 `/rag` 页面查看 evidence、retriever 数量、rerank 状态、fallback 错误。

当前测试覆盖的是“系统能不能跑、关键模块有没有明显坏掉”，不是“检索质量是否足够好”。

### 还没有做的评估

还没有：

- 固定 eval query 集。
- 人工标注 expected documents / expected chunks。
- hit@k、recall@k、MRR。
- rerank lift。
- parent coverage。
- 检索延迟统计。
- RAGAS answer-level 评估。

### 后续评估策略

Phase 4.3 会先做自定义 Retrieval Eval，不先上 RAGAS。

原因：

- 当前阶段主要产物是 Evidence Pack，而不是最终回答。
- RAGAS 更适合评估最终 answer 的 faithfulness、answer relevancy、context precision 等。
- 现在更需要可解释、可复现地判断“正确证据有没有召回”。

Phase 4.3 计划：

- 手工维护小型 eval seed 文件，不用脚本自动生成作为最终标准。
- 可以用脚本辅助生成候选 query，但必须人工确认 expected evidence。
- 输出 `reports/rag_eval.json` 和 `reports/rag_eval.md`。

后续 Phase 5 进入 JD 匹配报告生成后，再引入 RAGAS 做 answer-level 评估。

## 3. Phase 状态总览

| Phase | 名称 | 状态 | 当前结论 |
| --- | --- | --- | --- |
| Phase 0 | 工程基础 | 已完成 | FastAPI/Jinja2/HTMX 基础可运行 |
| Phase 1 | 数据库与异步任务基础 | 已完成 | PostgreSQL/Redis/Celery/TaskRun 基础可用 |
| Phase 2 | 求职领域数据模型 | 已完成 | 简历、岗位、投递、目标、通知等模型和页面可用 |
| Phase 3 | 文档摄取与简历生命周期 | 已完成 | 文档上传、解析、切分、Resume Profile/Version 关联可用 |
| Phase 4 | Hybrid RAG 初版 | 已完成 | ES/Milvus/PostgreSQL fallback/RRF/Evidence Pack 可运行 |
| Phase 4.1 | RAG 稳定化 | 已完成 | 索引健康、状态、删除清理、fallback 可观测 |
| Phase 4.2 | Rerank 层 | 已完成 | qwen3-rerank 已接入，失败回退 RRF |
| Phase 4.3a | Index Versioning 与 Re-index | 已完成 | parse/index version、re-index、OCR 预留已完成 |
| Phase 4.3b | Retrieval Eval 与切分优化 | 暂缓 | 后续回头做，不阻塞业务闭环 |
| Phase 5 | JD-简历匹配 Workflow | 下一步 | 第一个真实业务 Agent workflow |
| Phase 6 | Career GraphRAG | 待做 | 技能图谱、gap path、学习路线 |
| Phase 7 | 岗位发现与主动推送 | 待做 | 岗位订阅、去重、相关性评分、通知 |
| Phase 8 | Memory Lifecycle | 待做 | 长期记忆候选、审核、冲突、归档 |
| Phase 9 | Skills Runtime | 待做 | SKILL.md 动态技能加载 |
| Phase 10 | 求职规划与学习路线 Agent | 待做 | 规划型 Agent |
| Phase 11 | 投递管理与面试准备 | 待做 | 求职闭环 |
| Phase 12 | 工程治理与部署 | 待做 | Docker Compose、SSE、监控、压测等 |

## 4. Phase 0：工程基础

### 本阶段目标

搭建最小可运行的 FastAPI 应用和页面基础。

### 已完成

- FastAPI 应用入口。
- Jinja2 页面框架。
- HTMX 局部刷新基础。
- `.env` 配置加载。
- 基础日志和 request id。
- 统一异常处理。
- `/health` 健康检查。

### 当前边界

- 不做认证。
- 不做多用户租户隔离。
- 不做复杂权限系统。

### 后续优化

- 用户认证。
- session / token。
- 多用户数据隔离。

### 验收方式

- 应用可以启动。
- `/health` 返回正常。
- 首页可以打开。

## 5. Phase 1：数据库与异步任务基础

### 本阶段目标

建立主业务库、迁移、异步任务和任务状态跟踪。

### 已完成

- PostgreSQL 连接。
- SQLAlchemy models。
- Alembic migrations。
- Redis 连接检查。
- Celery worker。
- `task_runs` 任务状态表。
- `workflow_runs`、`messages` 等 workflow 基础表。
- `documents`、`document_sections`、`document_chunks` 基础表。

### 当前边界

- Celery 任务只有基础 ping、解析、索引、重建索引。
- 任务重试和审计还不完整。

### 后续优化

- Celery retry policy。
- dead letter / failed task audit。
- task event 页面。
- Celery Beat。

### 验收方式

- migration 可以执行。
- worker 可以连接 Redis。
- ping task 可以创建、运行、写回状态。

## 6. Phase 2：求职领域数据模型

### 本阶段目标

建立求职助手所需的业务模型和轻量页面。

### 已完成

- `resume_profiles`
- `resume_versions`
- `job_sources`
- `job_subscriptions`
- `job_fetch_runs`
- `job_postings`
- `job_scores`
- `applications`
- `career_goals`
- `learning_goals`
- `notifications`
- `proactive_events`

已完成页面：

- `/resumes`
- `/jobs`
- `/applications`
- `/goals`
- `/notifications`

### 当前边界

- 岗位订阅还没有真实定时抓取。
- 通知主要还是手动创建。
- career goal / learning goal 还没有 Agent 规划。

### 后续优化

- 岗位订阅 source adapter。
- 投递状态流转。
- 与 JD 匹配报告联动。
- 主动提醒。

### 验收方式

- 页面可创建和查看基础业务对象。
- 数据能写入 PostgreSQL。

## 7. Phase 3：文档摄取与简历生命周期

### 本阶段目标

让简历、JD、项目材料进入系统，变成可检索语料，并和求职业务对象关联。

### 已完成

- 简历 / JD / 项目材料上传或粘贴。
- 文件落盘。
- PDF / 文本文档解析。
- Parent Section 切分。
- Child Chunk 切分。
- Celery 文档解析任务。
- 上传 resume document 时自动创建或关联 `ResumeProfile` 和 `ResumeVersion`。
- 已有 resume document 可以重新 attach 到 Resume Version。
- 删除 Document 时清理本地文件、sections、chunks。
- 删除 Resume Profile / Resume Version 时保留原始 Document。

### 当前边界

- PDF 解析只是 text-only，不理解版面和表格。
- splitter 是最小手写实现。
- 图片 OCR 只是预留配置，未真正实现。
- 音频不考虑。

### 后续优化

- Parser adapter 化。
- 接入 LangChain / Docling / Unstructured。
- 表格和版面结构解析。
- 图片 OCR adapter。
- 重复上传检测。

### 验收方式

- 上传或粘贴文档后能生成 sections / chunks。
- resume 文档能创建或关联 Resume Profile / Version。
- 删除 Document 不误删 Resume Profile。

## 8. Phase 4：Hybrid RAG 初版

### 本阶段目标

跑通从 parsed chunks 到 evidence pack 的最小检索闭环。

### 已完成

- 全局 phase 配置。
- Elasticsearch chunk index adapter。
- Milvus chunk vector adapter。
- PostgreSQL `document_chunks` 本地关键词 fallback。
- RRF fusion。
- Parent section fetch。
- Evidence Pack 输出。
- `text-embedding-v4` embedding provider。
- deterministic hashing embedding fallback。
- `documents.index` Celery 任务。
- `/api/rag/search`。
- `/api/rag/documents/{document_id}/index`。
- `/rag` 检索验证页面。
- `/documents` 页面新增 Index 操作。

### 当前边界

- `/rag` 是开发验证台，不是最终产品页。
- local fallback 只是简单关键词计分，不是 PostgreSQL FTS / BM25。
- 还未接入业务 workflow。

### 后续优化

- Query rewrite。
- Graph expansion。
- 接入 JD Match workflow。
- PostgreSQL FTS fallback。

### 验收方式

- parsed 文档可以 index。
- `/rag` 可以返回 Evidence Pack。
- ES/Milvus 不可用时仍可用 PostgreSQL fallback。

## 9. Phase 4.1：Hybrid RAG 稳定化

### 本阶段目标

让 RAG 链路可观测、可诊断、可清理。

### 已完成

- Elasticsearch index mapping 检查。
- Milvus collection schema 检查。
- Milvus 默认 collection 使用 `persona_graph_chunks_v4`。
- 索引状态详情展示。
- 一键 index ready documents。
- 外部索引健康检查。
- Document 删除时清理 ES / Milvus。
- RAG 单元测试基础。

### 当前边界

- `Index Ready` 仍偏同步/轻量。
- 外部索引清理失败没有后台补偿。
- Neo4j 图节点清理尚未实现。

### 后续优化

- 批量索引全部走 Celery task。
- 外部索引清理失败补偿队列。
- 索引任务审计日志。

### 验收方式

- `/api/rag/indexes/health` 能显示 ES/Milvus 状态。
- `/api/rag/indexes/status` 能显示文档和 chunk 的索引状态。
- 删除 Document 后 ES/Milvus 按 `document_id` 清理。

## 10. Phase 4.2：Rerank 与检索质量层

### 本阶段目标

在 RRF 后加入 rerank，提高 evidence 排序质量。

### 已完成

- `qwen3-rerank` adapter。
- Rerank API key 和 base URL 默认复用 LLM 配置。
- DashScope rerank endpoint 规范化。
- RRF 后候选扩展。
- Rerank 后 Evidence Pack 输出。
- Rerank 失败回退 RRF。
- `/rag` 页面支持 rerank `auto / on / off`。
- API 返回 `reranker` metadata。
- rerank 单元测试。

当前 RAG 链路：

```text
BM25 / Vector / Local
-> RRF Fusion
-> Parent Fetch
-> qwen3-rerank
-> Evidence Pack
```

### 当前边界

- rerank 结果未持久化。
- rerank instruct 还没有按 JD Match / 学习路线等场景定制。
- 还没有 retrieval eval 来量化 rerank 提升。

### 后续优化

- rerank lift 指标。
- 不同 workflow 使用不同 rerank instruct。
- rerank 成本和延迟统计。

### 验收方式

- smoke test 可调用 `qwen3-rerank`。
- rerank 失败时 RAG 仍能返回 RRF evidence。
- `/rag` 能显示 reranker status。

## 11. Phase 4.3a：Index Versioning 与 Re-index 基础

### 本阶段目标

记录每份文档按哪套解析和索引策略生成，并提供 re-parse / re-index 入口。

### 已完成

- 解析策略版本指纹：
  - `parse_version`
  - `parse_strategy`
- 索引策略版本指纹：
  - `index_version`
  - `index_strategy`
- 文档 parse 后写入当前 parse strategy。
- 文档 index 后写入当前 index strategy。
- `DocumentChunk.metadata` 写入 parse / index version。
- `/api/rag/indexes/status` 返回当前 parse / index version 和 stale 文档数量。
- `/api/rag/documents/{document_id}/reindex`。
- `/api/rag/reindex-stale`。
- `/api/documents/{document_id}/parse` 用于 re-parse。
- `/documents` 页面新增 Re-parse / Re-index。
- `/rag` 页面新增 Re-index Stale。
- OCR / 图片文本识别预留配置：
  - `DOCUMENT_OCR_ENABLED`
  - `DOCUMENT_OCR_PROVIDER`
  - `DOCUMENT_MULTIMODAL_ENABLED`
  - `DOCUMENT_IMAGE_EXTENSIONS`
- 明确不支持音频。

### 当前边界

- 版本信息先放在 JSONB metadata 中，没有新增数据库列。
- OCR / 多模态只是预留策略字段，不实际调用 OCR，也不开放图片上传解析。
- 一键 re-parse stale documents 还没有做。

### 后续优化

- 一键 re-parse stale documents。
- 索引版本变更的后台补偿队列。
- OCR adapter。
- 图片文件解析与上传类型开放。
- 索引版本可视化详情页。

### 验收方式

- `/api/rag/indexes/status` 能返回 current parse/index version。
- legacy parsed 文档会被识别为 stale。
- `/documents` 能触发 Re-parse / Re-index。
- Celery worker 能加载 `documents.reindex`。

## 12. Phase 4.3b：Retrieval Eval 与切分优化

### 当前决策

本阶段暂缓，不在当前迭代继续做。

原因：

- 当前系统已经具备可运行的 RAG 闭环、rerank、index versioning 和 re-index 基础。
- 继续打磨 eval 和切分会提升质量，但会推迟第一个真实业务 workflow。
- 项目当前更需要尽快进入 Phase 5，做出 JD-简历匹配闭环。

后续回头做 Phase 4.3b 时，再补 Retrieval Eval 和切分优化。

### 本阶段目标

让 RAG 质量可以被稳定评估，而不是靠肉眼感觉。

### 当前要做

- 建立 `eval_sets/rag_retrieval.yaml`。
- 手工维护一批 query 和 expected evidence。
- 实现 `scripts/eval_rag.py`。
- 输出 `reports/rag_eval.json`。
- 输出 `reports/rag_eval.md`。
- 统计：
  - hit@k
  - recall@k
  - MRR
  - source coverage
  - parent coverage
  - rerank lift
  - latency
  - retriever errors
- 对比 rerank on/off。
- 为后续 chunk size / overlap 优化提供依据。

### 当前边界

- 不用脚本自动生成最终评估集。
- 可以用脚本辅助生成候选 query，但必须人工确认 expected evidence。
- 不在本阶段接 RAGAS 作为主评估。
- 不在本阶段做 answer-level 评估。

### 后续优化

- Phase 5 后引入 RAGAS。
- 针对 JD Match 报告评估 faithfulness、answer relevancy、context precision。
- 增加更多真实 JD 和简历样例。

### 验收方式

- 固定 eval query 能跑完。
- 报告能展示每条 query 的命中情况。
- rerank on/off 差异可见。
- 能发现至少一类切分或召回问题。

## 13. Phase 5：JD-简历匹配 Workflow

### 当前决策

下一阶段直接进入 Phase 5。

### 本阶段目标

做出第一个真正面向求职业务的 Agent workflow。

### 当前要做

- `resume_match` skill。
- JD 文档选择。
- Resume Version 选择。
- 调用 Hybrid RAG 召回：
  - resume evidence
  - project evidence
  - JD evidence
- 输出匹配报告：
  - 总体匹配分
  - matched skills
  - gap skills
  - evidence references
  - resume rewrite suggestions
  - interview prep points
- 保存 `job_scores`。

### 当前边界

- 先做单用户、本地页面流程。
- 先做结构化 JSON 报告，不做复杂 PDF 导出。
- 先用固定 skill，不做完整 Skills Runtime。

### 后续优化

- LangGraph 分支规划。
- 多 JD 批量比较。
- 报告导出。
- RAGAS answer-level 评估。

### 验收方式

- 选择一份 JD 和一版简历后生成匹配报告。
- 报告中每个关键判断都有 evidence。
- 结果写入 `job_scores`。

## 14. Phase 6：Career GraphRAG

### 本阶段目标

把 RAG 证据升级为职业知识图谱，支持技能差距和学习路线。

### 当前要做

- 技能 / 要求 / 项目实体抽取。
- 写入 Neo4j：
  - Candidate
  - Resume
  - Project
  - Skill
  - Technology
  - JobPosting
  - Requirement
  - LearningResource
- 建立关系：
  - Project DEMONSTRATES Skill
  - JobPosting REQUIRES Skill
  - Skill PREREQUISITE_OF Skill
- Graph expansion 检索。
- skill gap path。
- learning prerequisite path。

### 当前边界

- 先从 JD Match 场景抽图，不做通用知识图谱。
- 先做小规模图谱，不追求全自动完美抽取。

### 后续优化

- 图谱质量审核。
- 图谱增量更新。
- 图谱可视化。

### 验收方式

- 对某个 JD 可以展示“要求技能 -> 我的项目证据 -> 缺口技能”路径。
- 对某个目标岗位可以生成基于图谱的学习路线。

## 15. Phase 7：岗位发现与主动推送

### 本阶段目标

让系统从被动分析变成主动发现机会。

### 当前要做

- Company Career Page Adapter。
- SerpApi / public job source adapter。
- Manual JD import adapter 保留。
- Job deduplication。
- Job subscription scheduler。
- Job relevance scoring。
- Notification 生成。
- `proactive_events` 记录。
- Celery Beat 定时触发。

### 当前边界

- 不做 BOSS 直聘私有登录爬取。
- 不做反爬绕过。
- 不做自动给招聘者发消息。

### 后续优化

- 多源岗位归并。
- 个性化推送阈值。
- 推送反馈学习。

### 验收方式

- 可以配置目标岗位订阅。
- 定时任务能产生新增岗位。
- 系统能判断推送或跳过，并记录原因。

## 16. Phase 8：长期记忆 Memory Lifecycle

### 本阶段目标

让系统维护用户长期偏好和职业画像。

### 当前要做

- `memory_candidates`
- `memories`
- memory extractor
- verifier
- conflict checker
- consolidation worker
- retriever
- source ref
- memory audit 页面

### 当前边界

- 不把 chat history 直接当长期记忆。
- 先做求职相关记忆，不做通用生活记忆。

### 后续优化

- 自动归档策略。
- 记忆冲突解决。
- 记忆置信度评分。

### 验收方式

- 对话、文档、任务结果可以产生 memory candidate。
- 用户可以确认、拒绝、归档记忆。
- JD 匹配和学习路线能使用长期记忆。

## 17. Phase 9：动态 Skills Runtime

### 本阶段目标

让能力通过 SKILL.md 动态组合，而不是写死在一个 agent 文件里。

### 当前要做

- Skill Registry。
- Skill Metadata Parser。
- Skill Search。
- Skill Loader。
- Permission Checker。
- Skill Run Logger。
- `skill_runs` 表。

### 当前边界

- 先支持本地 skills。
- 先做求职相关 skills。

### 后续优化

- MCP tool permission。
- skill marketplace。
- skill eval。

### 验收方式

- 用户请求进入 Intent Router。
- Router 选择相关 skill。
- 系统加载 SKILL.md。
- LangGraph workflow 执行并保存 skill run。

## 18. Phase 10：求职规划与学习路线 Agent

### 本阶段目标

实现“我想 8 周内冲 AI Agent 实习”这类规划任务。

### 当前要做

- career planning workflow。
- learning roadmap workflow。
- 结合：
  - resume evidence
  - job market evidence
  - graph skill gaps
  - long-term memory
- 生成：
  - 当前能力评估
  - 技能缺口
  - 学习优先级
  - 每周 milestones
  - 项目实践任务
  - 验收标准

### 当前边界

- 先生成计划，不做自动执行学习任务。
- 先做本地页面，不做复杂日历同步。

### 后续优化

- 计划进度追踪。
- 主动提醒。
- 周报复盘。

### 验收方式

- 输入目标岗位和时间范围后生成可执行计划。
- 计划能引用真实 JD、项目证据和学习资源。

## 19. Phase 11：投递管理与面试准备

### 本阶段目标

把求职流程闭环到投递和面试。

### 当前要做

- application tracker 强化。
- 面试题生成。
- 面试准备 checklist。
- 投递复盘。
- 每周 career review。
- 状态看板。

### 当前边界

- 不做自动投递。
- 不做自动联系招聘者。

### 后续优化

- 面试记录分析。
- application pipeline dashboard。
- 简历版本和投递效果关联分析。

### 验收方式

- 每个 application 有状态、下一步行动、使用的 resume version 和复盘记录。
- 系统能根据 JD 和我的项目生成面试准备材料。

## 20. Phase 12：工程治理与部署

### 本阶段目标

让项目具备完整上线和展示能力。

### 当前要做

- Docker Compose 一键启动。
- 完整 README。
- seed data / demo script。
- SSE 流式输出。
- 限流。
- 重试策略。
- 审计日志。
- 更完整测试。
- OpenTelemetry / Prometheus / Grafana 可选接入。

### 当前边界

- 先保证本地可复现。
- 生产级安全和多租户可以后置。

### 后续优化

- CI。
- 压测。
- 部署脚本。
- 监控 dashboard。

### 验收方式

- 新机器可以按 README 启动核心服务。
- 有完整演示路径：
  - 上传简历
  - 上传 JD
  - 解析
  - 索引
  - 检索
  - 匹配
  - 生成规划
