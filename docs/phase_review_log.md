# 阶段复盘记录

这个文档用于记录每个阶段暴露出来的设计问题、实现决策、修复内容、验证方式和后续延迟项。之后每完成一个阶段，或者对某个阶段做了比较重要的优化，都要继续更新这里。

## 如何维护这个文档

每次阶段复盘建议记录：

- 背景：当时在实现或测试什么。
- 问题：哪里让人困惑、缺失、有风险，或者数据模型不够准确。
- 决策：最后采用了什么设计取舍。
- 实现：具体改了哪些代码、表结构或页面交互。
- 验证：如何确认改动可用。
- 延迟项：哪些事情是有意留到后续阶段做的。

## 2026-06-05：Phase 3 文档摄取与简历生命周期优化

### 背景

Phase 3 引入了面向简历、JD 和求职材料的 Document Ingestion 能力。

最初版本已经支持：

- 文件上传。
- 文件落盘。
- 文本解析。
- Parent Section 切分。
- Child Chunk 切分。
- Celery 解析任务。
- 基础 `/documents` 页面。

在用真实简历 PDF 手动测试时，发现上传文档和求职业务对象之间的关系还不够完整，尤其是 `Document`、`ResumeProfile`、`ResumeVersion` 的边界和删除语义不够清楚。

### 问题 1：上传简历后没有自动生成 Resume Profile

问题：

- 上传 `doc_type=resume` 的文档时，只创建了 `Document`。
- `/resumes` 页面仍然为空，因为没有创建 `ResumeProfile` 和 `ResumeVersion`。
- `/documents` 页面只能选择已有 Resume Profile，第一次上传简历时下拉框只有 `None`。

决策：

- 上传简历不应该只是创建一个原始文档，还应该完成求职业务侧的关联。
- 如果用户上传简历时没有选择已有 Profile，系统应根据用户填写的 Profile 标题，或者根据文档标题，自动创建新的 `ResumeProfile`。
- 随后系统创建一个 `ResumeVersion`，并通过 `document_id` 关联到刚上传的 `Document`。

实现：

- 新增 `app/domains/documents/career_links.py`。
- 将 document-to-career 关联逻辑从页面层和 API 层抽到共享 helper。
- 文档上传和文本录入新增可选字段：
  - `resume_profile_title`
  - `resume_target_role`
  - `resume_version_label`

验证：

- `/documents` 页面可以看到新建 Profile 相关字段。
- `/resumes` 页面可以看到上传的简历 Profile，并且下面有一个 Version。
- `python -m pytest -q` 通过。

### 问题 2：Resume Profile、Resume Version 和 Document 的边界不清楚

问题：

- 容易误以为上传的 PDF 是“放在 Resume Profile 里面”的。
- 实际数据模型不是这样。

正确关系：

```text
ResumeProfile
`-- ResumeVersion
    `-- document_id
        `-- Document
```

决策：

- 原始材料和求职业务组织方式要分开。
- `Document` 表示原始材料和解析后的语料，例如 PDF、txt、JD、项目材料。
- `ResumeProfile` 表示求职侧的简历档案，例如“AI Agent 实习简历”。
- `ResumeVersion` 表示某个 Profile 下的一版具体简历。它可以关联一个 Document，也可以直接保存手写内容。

实现：

- `/resumes` 页面展示 Profile 下的 Version 列表。
- Version 行展示 `source_type`。
- 如果 Version 关联了 Document，也展示文档标题。

验证：

- 手动打开 `/resumes` 页面，确认 Profile、Version、Document 的展示关系清楚。

### 问题 3：删除语义需要明确区分

问题：

- `/documents` 页面里的 Delete 和 `/resumes` 页面里的 Delete Version 看起来都像“删除”，但实际含义不同。
- 删除 Resume Profile 或 Resume Version 不应该误删原始上传 PDF。

决策：

删除 `Document` 是对原始语料的破坏性删除：

```text
Delete Document
-> 删除 documents 表记录
-> 删除 document_sections
-> 删除 document_chunks
-> 删除 uploads/documents 下的本地上传文件
```

删除 `ResumeVersion` 只删除求职业务侧的一条版本记录。

删除 `ResumeProfile` 会删除该 Profile 和它下面的所有 Version，但保留原始 `Document`。

实现：

- 在 document service 中新增：
  - `delete_document`
  - `delete_stored_file`
- 新增 Document 的页面删除路由和 API 删除路由。
- 新增 Resume Profile 和 Resume Version 的删除路由。
- 页面增加 Delete 按钮和浏览器确认弹窗。
- `delete_stored_file` 只允许删除配置的上传目录下的文件，避免误删项目外部路径。

验证：

- 创建临时文档，解析后删除，确认：
  - document row 被删除。
  - sections 被删除。
  - chunks 被删除。
  - 本地文件被删除。
- `python -m pytest -q` 通过。

### 问题 4：删除 Version 后，已有 Document 无法重新关联

问题：

- 如果用户删除了 `ResumeVersion`，原始 `Document` 仍然会保留在 `/documents`。
- 但最初页面没有提供“把已有 Document 重新挂到某个 Resume Profile 下”的入口。

决策：

- 创建 Resume Version 时应该支持选择已有的 resume Document。
- 这样即使用户删除了 Version，只要原始 Document 还在，就可以重新关联。

实现：

- `/resumes` 的 Version 表单新增 `Source Document` 下拉框。
- `list_documents` 支持按 `doc_type` 过滤。
- `/resumes` 页面向模板传入已有 resume documents。
- 修复 API 中 `resume-versions` 创建逻辑，让 `document_id` 和 `source_type` 真正写入数据库。
- 在 service 层增加防呆逻辑：如果传了 `document_id`，但 `source_type` 还是 `manual`，则自动保存为 `document`。

验证：

- 创建临时 Profile。
- 将已有 resume Document 绑定为一个临时 Version。
- 确认新 Version 中的 `document_id` 正确，`source_type=document`。
- 删除临时 Profile 做清理。
- `python -m pytest -q` 通过。

### 问题 5：删除时应该使用 hash 还是 document_id

问题：

- 一开始不确定删除 chunks、文件或后续索引时，应该靠 content hash 还是靠 document id。

决策：

- 删除应该以 `document_id` 为主，而不是 content hash。
- hash 不是业务主键。同一份内容可能因为不同用途被上传多次，如果用 hash 删除，容易误删多个逻辑文档。
- hash 更适合用于：
  - 重复上传检测。
  - 缓存 key。
  - 内容是否变更的判断。
  - 外部索引一致性校验。

实现：

- PostgreSQL 删除以 `Document.id` 为入口。
- `document_sections` 和 `document_chunks` 都通过 `document_id` 关联，并依赖级联删除。
- 本地文件删除通过当前 `Document.file_path` 执行，并做上传目录安全检查。

延迟项：

- 后续 Milvus vectors、Elasticsearch documents、Neo4j graph nodes 都应该在 metadata/properties 中保存 `document_id`。
- 删除 Document 时，需要按 `document_id` 删除外部索引中的记录。

## 2026-06-14：Phase 4 Hybrid RAG 初版实现

### 背景

Phase 4 的目标是把 Phase 3 已经落库的 parent section / child chunk 接入检索链路，形成最小可运行的 Hybrid RAG 闭环。

同时，页面上仍有一些地方显示旧阶段标识，说明阶段标识散落在多个路由里，不利于后续维护。

### 问题 1：页面阶段标识硬编码

问题：

- `/resumes`、`/jobs`、`/documents`、`/health` 等位置各自写死 phase。
- 进入新阶段后，需要手动搜索并修改多个文件，容易漏。

决策：

- 在 `Settings` 中新增全局阶段配置。
- 页面显示使用 `APP_PHASE_LABEL`。
- API / 健康检查使用 `APP_PHASE`。

实现：

- `app.core.config.Settings` 新增：
  - `app_phase`
  - `app_phase_label`
- `.env.example` 新增：
  - `APP_PHASE=phase_4_hybrid_rag`
  - `APP_PHASE_LABEL=Phase 4`
- 页面路由统一使用 `settings.app_phase_label`。
- `/health` 使用 `settings.app_phase`。

验证：

- `/health` 测试更新为 `phase_4_hybrid_rag`。
- `python -m pytest -q` 通过。

### 问题 2：Phase 4 需要先做检索闭环，而不是直接追求检索质量

问题：

- 真正的 Hybrid RAG 涉及 ES、Milvus、embedding 模型、RRF、parent fetch、rerank。
- 如果一开始就追求完整质量，很容易卡在 embedding 服务、模型选择或外部索引细节上。

决策：

- Phase 4 先做可运行、可验证、可替换的检索闭环。
- ES 和 Milvus 作为可选外部索引，失败时不影响本地页面和测试。
- 本地 PostgreSQL 关键词检索作为兜底召回。

实现：

- 新增 `app/domains/rag`：
  - `embeddings.py`
  - `indexes.py`
  - `fusion.py`
  - `schemas.py`
  - `service.py`
  - `jobs.py`
- Elasticsearch adapter 负责 chunk BM25 / full-text 写入与查询。
- Milvus adapter 负责 child chunk vector 写入与查询。
- 默认 embedding provider 使用 `text-embedding-v4`。
- `reciprocal_rank_fusion` 负责融合 BM25、vector 和 local 结果。
- `build_evidence_pack` 回表获取 parent section 和 document 信息。
- 新增 Celery task：`documents.index`。
- 新增 API：
  - `POST /api/rag/documents/{document_id}/index`
  - `POST /api/rag/index-ready`
  - `POST /api/rag/search`
- 新增页面：
  - `/rag`
  - `/documents` 中每个 parsed document 的 `Index` 操作。

验证：

- `python -m compileall app` 通过。
- `python -m pytest -q` 通过。
- `/rag` 页面可以在外部索引不可用时展示 local fallback 的检索结果。

### 问题 3：Embedding provider 从占位切到 text-embedding-v4

问题：

- Phase 4 需要 Milvus 向量索引，不能长期依赖 hashing embedding。
- 文本 embedding 需要和当前 LLM 一样走 DashScope OpenAI-compatible API。

决策：

- 默认 embedding 模型使用 `text-embedding-v4`。
- `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL` 为空时，自动复用 `LLM_API_KEY` 和 `LLM_BASE_URL`。
- 保留 deterministic hashing embedding 作为测试和 fallback，避免外部 API 临时不可用时整个检索页面不可用。

实现：

- `app/domains/rag/embeddings.py` 新增 OpenAI-compatible embedding client。
- 新增配置：
  - `EMBEDDING_MODEL_ID=text-embedding-v4`
  - `EMBEDDING_API_KEY`
  - `EMBEDDING_BASE_URL`
  - `EMBEDDING_BATCH_SIZE=10`
  - `RAG_EMBEDDING_DIM=1024`
  - `RAG_EMBEDDING_FALLBACK_TO_HASH=true`

延迟项：

- 后续需要增加 embedding provider 的健康检查。
- 后续需要增加 retrieval eval，评估 `text-embedding-v4` 的实际召回质量。

## 2026-06-14：Phase 4.1 Hybrid RAG 稳定化

### 背景

Phase 4 已经把文档 chunk 接入 ES、Milvus 和本地 PostgreSQL fallback，但当外部索引不可用时，页面只能看到“检索失败”或局部结果，不容易判断问题发生在哪里。

同时，删除 Document 时如果只删 PostgreSQL 和本地文件，ES / Milvus 中可能残留旧 chunk，后续检索会出现已删除文档的证据。

### 问题 1：fallback 的落点需要明确

问题：

- “ES 或 Milvus 不可用时，本地 fallback 仍然可用”这句话不够清楚。
- 容易误解成系统还有另一个外部检索服务或备用向量库。

决策：

- Phase 4.1 的 fallback 明确指向 PostgreSQL。
- 具体落点是已经解析落库的 `document_chunks` 表。
- fallback 检索方式是本地关键词计分：query token 在 chunk content、document title、section path 中命中的次数越多，分数越高。
- 这个结果仍然会进入 RRF，并通过 parent fetch 生成 Evidence Pack。

实现：

- `local_keyword_search` 继续作为兜底 retriever。
- `/rag` 页面显示 `Fallback: PostgreSQL document_chunks`。
- `docs/project_roadmap.md` 中明确 fallback 不依赖 ES / Milvus，但召回质量低于 BM25 + Vector。

延迟项：

- 当前 fallback 只是最小可用检索，不等价于 PostgreSQL FTS / BM25。
- 后续可以用 PostgreSQL full-text search 或 trigram index 强化本地检索质量。

### 问题 2：外部索引状态需要可观测

问题：

- ES / Milvus 如果未启动、collection 维度不一致、index 不存在，页面层之前没有统一入口查看。
- Phase 4 后续要接 JD 匹配 Agent，如果底层 evidence 不稳定，上层 workflow 很难排错。

决策：

- RAG 页先作为开发验证台保留。
- 新增索引健康检查和状态汇总，让“外部服务状态”和“本地数据库状态”分开看。

实现：

- 新增 API：
  - `GET /api/rag/indexes/health`
  - `GET /api/rag/indexes/status`
- `/rag` 页面新增：
  - Index Health：ES / Milvus 是否可用，index / collection 是否存在，Milvus 维度。
  - Index Status：documents、embedding chunks、BM25 chunks 的状态分布。
  - Index Ready：一次索引最多 5 个 ready 文档。

延迟项：

- `Index Ready` 目前是同步调用，后续应改为 Celery 批任务并在页面轮询 task status。
- embedding provider 自身还没有独立健康检查。

### 问题 3：删除 Document 时要清理 ES / Milvus

问题：

- Phase 3 删除 Document 只处理 PostgreSQL 和本地上传文件。
- Phase 4 引入外部索引后，如果不清理，会导致 ES / Milvus 残留已删除文档的 chunk。

决策：

- 删除入口仍然以 `document_id` 为主键。
- ES 使用 `_delete_by_query` 按 `document_id` 删除。
- Milvus 使用 filter 表达式按 `document_id` 删除。
- 删除失败不阻塞 PostgreSQL 删除，但结果会返回到 service 层，便于后续审计。

实现：

- `ElasticsearchChunkIndex.delete_document`。
- `MilvusChunkIndex.delete_document`。
- `delete_document_indexes` 聚合 ES / Milvus 删除结果。
- `delete_document` 在删除本地文件和 PostgreSQL 行之前尝试清理外部索引。
- Milvus 默认 collection 调整为 `persona_graph_chunks_v4`，避免继续使用早期 128 维 hashing embedding 创建的旧 collection。

延迟项：

- Neo4j 图节点还未接入删除清理，留到 Career GraphRAG 阶段。
- 删除操作还没有完整审计日志和后台重试队列。

## 2026-06-14：Phase 4.2 Rerank 与检索质量层

### 背景

Phase 4.1 已经让 Hybrid RAG 具备可运行、可观测、可降级、可清理的工程闭环。

但是 RRF 只能融合不同召回源的排名信号，并不真正理解“当前 query 与证据内容是否高度相关”。

因此 Phase 4.2 先引入 rerank，把检索质量层插在 RRF 与 Evidence Pack 输出之间。

### 问题 1：rerank 应该放在链路的哪个位置

决策：

- 不把 rerank 放进 ES、Milvus 或 local retriever 内部。
- 正确位置是：BM25 / Vector / Local 召回后，先 RRF 得到候选，再用 reranker 对候选证据重新排序。
- 这样底层 retriever 继续负责“召回尽可能多的相关候选”，reranker 负责“从候选中挑出更适合回答当前问题的证据”。

实现：

```text
BM25 / Vector / Local
-> RRF Fusion
-> Parent Fetch
-> qwen3-rerank
-> Evidence Pack
```

### 问题 2：qwen3-rerank 的配置如何复用 LLM

决策：

- 默认模型为 `qwen3-rerank`。
- `RERANK_API_KEY` 和 `RERANK_BASE_URL` 为空时，自动复用 `LLM_API_KEY` 和 `LLM_BASE_URL`。
- DashScope rerank 的 endpoint 与 chat/embedding 的 compatible-mode 地址不同，adapter 内部会优先把 `/compatible-mode/v1` 规范化为 `/compatible-api/v1/reranks`，并保留原始 base URL + `/reranks` 作为 fallback endpoint。

实现：

- 新增配置：
  - `RAG_RERANK_ENABLED`
  - `RAG_RERANK_CANDIDATE_MULTIPLIER`
  - `RAG_RERANK_DOCUMENT_MAX_CHARS`
  - `RERANK_API_KEY`
  - `RERANK_MODEL_ID`
  - `RERANK_BASE_URL`
  - `RERANK_INSTRUCT`
- 新增 `app/domains/rag/rerankers.py`。

### 问题 3：rerank 失败时不能让 RAG 整体不可用

决策：

- rerank 是质量增强层，不是可用性的唯一依赖。
- 如果 rerank 请求失败，系统会记录 `errors.rerank`，并回退到 RRF 顺序返回 Evidence。

实现：

- `/rag` 页面展示：
  - reranker model
  - enabled
  - candidate count
  - status
  - fallback
- API 返回 `reranker` 元数据，方便后续 JD Match workflow 判断本次 evidence 是否经过重排。

### 当前范围

已经完成：

- `qwen3-rerank` adapter。
- RRF 后候选扩展：最终 `top_k` 之前先按 multiplier 取更多候选。
- rerank 后 Evidence Pack 输出。
- rerank 失败回退 RRF。
- `/rag` 页面支持 auto / on / off。
- rerank 单元测试。

有意延迟：

- retrieval eval 样例集。
- query rewrite。
- chunk size / overlap 重新调参。
- rerank 结果持久化。
- 根据 JD Match 场景定制不同 rerank instruct。

## 2026-06-14：Phase 4.3a Index Versioning 与 Re-index 基础

### 背景

RAG 索引不是一次构建后永远有效。它依赖当时的解析策略、chunk 策略、embedding 模型、向量维度、ES index、Milvus collection 和 rerank 配置。

当这些策略变化时，旧文档可能仍然显示为 indexed，但它的外部索引已经不再匹配当前系统配置。

### 问题 1：系统不知道某份文档是按哪套规则解析和索引的

决策：

- 不急着新增数据库列，先把版本信息写入 JSONB metadata。
- parse 阶段写：
  - `parse_version`
  - `parse_strategy`
- index 阶段写：
  - `index_version`
  - `index_strategy`
- chunk metadata 中也保留 parse / index version，方便后续排查外部索引和数据库 chunk 的一致性。

实现：

- 新增 `app/domains/rag/versioning.py`。
- 通过稳定 JSON 序列化 + SHA256 生成策略指纹。
- `/api/rag/indexes/status` 返回当前 parse / index version 和 stale 文档数量。

### 问题 2：什么时候 re-index，什么时候 re-parse

决策：

- embedding、ES index、Milvus collection、rerank 配置变化：需要 re-index。
- parser、OCR、parent section、child chunk size、overlap 变化：需要 re-parse，然后再 index。

实现：

- 新增 `reindex_document`。
- re-index 时先按 `document_id` 清理 ES / Milvus，再用当前策略重新写入。
- 新增 Celery task：`documents.reindex`。
- 新增 API：
  - `POST /api/rag/documents/{document_id}/reindex`
  - `POST /api/rag/reindex-stale`
  - `POST /api/documents/{document_id}/parse`
- `/documents` 页面新增 Re-parse / Re-index。
- `/rag` 页面新增 Re-index Stale。

### 问题 3：后续可能加入 OCR 或图片文本识别，需要提前留策略位置

决策：

- 只预留 OCR / 多模态配置，不在当前阶段实现 OCR。
- 当前不开放图片上传解析，避免用户以为图片已经可用。
- 明确不考虑音频。

实现：

- 新增配置：
  - `DOCUMENT_OCR_ENABLED`
  - `DOCUMENT_OCR_PROVIDER`
  - `DOCUMENT_MULTIMODAL_ENABLED`
  - `DOCUMENT_IMAGE_EXTENSIONS`
- 这些字段进入 `parse_strategy`，未来只要打开 OCR 或换 OCR provider，就会触发 parse version 变化。

延迟项：

- OCR adapter。
- 图片上传解析。
- 一键 re-parse stale documents。
- 更完整的索引版本详情页。
- 后台补偿队列和审计日志。
