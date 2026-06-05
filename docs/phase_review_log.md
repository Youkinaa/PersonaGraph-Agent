# 阶段复盘记录

这个文档用于记录每个阶段中暴露出来的设计问题、实现决策、修复内容、验证方式和后续延迟项。之后每完成一个阶段，或者对某个阶段做了比较重要的优化，都要继续更新这里。

## 如何维护这个文档

每次阶段复盘建议记录以下内容：

- 背景：当时在实现或测试什么。
- 问题：哪里让人困惑、缺失、有风险，或者数据模型不够准确。
- 决策：最后采用了什么设计取舍。
- 实现：具体改了哪些代码、表结构或页面交互。
- 验证：如何确认这个改动是可用的。
- 延迟项：哪些事情是有意留到后续阶段做的。

## 2026-06-05：Phase 3 文档摄取与简历生命周期优化

### 背景

Phase 3 引入了面向简历、JD 和求职材料的 Document Ingestion 能力。最初版本已经支持文件上传、文件落盘、文本解析、Parent Section 切分、Child Chunk 切分、Celery 解析任务，以及一个基础的 `/documents` 页面。

在用真实简历 PDF 手动测试时，发现上传文档和求职业务对象之间的关系还不够完整，尤其是 `Document`、`ResumeProfile`、`ResumeVersion` 的边界和删除语义不够清楚。

### 问题 1：上传简历后没有自动生成 Resume Profile

问题：

- 上传 `doc_type=resume` 的文档时，只创建了 `Document`。
- `/resumes` 页面仍然为空，因为没有创建 `ResumeProfile` 和 `ResumeVersion`。
- `/documents` 页面只能选择已有 Resume Profile。第一次上传简历时，下拉框只有 `None`。

决策：

- 上传简历不应该只是创建一个原始文档，还应该完成求职业务侧的关联。
- 如果用户上传简历时没有选择已有 Profile，系统应该根据用户填写的 Profile 标题，或者根据文档标题，自动创建一个新的 `ResumeProfile`。
- 随后系统创建一个 `ResumeVersion`，并通过 `document_id` 关联到刚上传的 `Document`。

实现：

- 新增 `app/domains/documents/career_links.py`。
- 将 document-to-career 关联逻辑从页面层和 API 层抽到共享 helper 中。
- 文档上传和文本录入新增可选字段：
  - `resume_profile_title`
  - `resume_target_role`
- 对本地已经上传过的一份简历文档做了补关联，创建了对应的 Profile 和 Version。

验证：

- `/documents` 页面可以看到新建 Profile 相关字段。
- `/resumes` 页面可以看到上传的简历 Profile，并且下面有一个版本。
- `python -m pytest -q` 通过。

### 问题 2：Resume Profile、Resume Version 和 Document 的边界不清楚

问题：

- 很容易误以为上传的 PDF 是“放在 Resume Profile 里面”的。
- 实际数据模型不是这样。正确关系是：

```text
ResumeProfile
`-- ResumeVersion
    `-- document_id
        `-- Document
```

决策：

- 原始材料和求职业务组织方式要分开。
- `Document` 表示原始材料和解析后的语料，比如 PDF、txt、JD、项目材料。
- `ResumeProfile` 表示求职侧的简历档案，比如“AI Agent 实习简历”。
- `ResumeVersion` 表示某个 Profile 下的一版具体简历。它可以关联一个 Document，也可以直接存手写内容。

实现：

- `/resumes` 页面现在会在 Profile 下展示 Version 列表。
- Version 行展示 `source_type`，如果有关联文档，也会展示文档标题。

验证：

- 手动打开 `/resumes` 页面，确认 Profile、Version、Document 的展示关系清楚。

### 问题 3：删除语义需要明确区分

问题：

- `/documents` 页面里的 Delete 和 `/resumes` 页面里的 Delete Version 看起来都像“删除”，但实际含义不同。
- 删除 Resume Profile 或 Resume Version 不应该误删原始上传的 PDF。

决策：

- 删除 `Document` 是对原始语料的破坏性删除：

```text
Delete Document
-> 删除 documents 表记录
-> 删除 document_sections
-> 删除 document_chunks
-> 删除 uploads/documents 下的本地上传文件
```

- 删除 `ResumeVersion` 只删除求职业务侧的一条版本记录。
- 删除 `ResumeProfile` 会删除该 Profile 和它下面的所有 Version，但保留原始 `Document`。

实现：

- 在 document service 中新增：
  - `delete_document`
  - `delete_stored_file`
- 新增 Document 的页面删除路由和 API 删除路由。
- 新增 Resume Profile 和 Resume Version 的删除路由。
- 页面上增加 Delete 按钮和浏览器确认弹窗。
- `delete_stored_file` 只允许删除配置的上传目录下的文件，避免误删项目外部路径。

验证：

- 创建临时文档，解析后删除，确认：
  - document row 被删除
  - sections 被删除
  - chunks 被删除
  - 本地文件被删除
- `python -m pytest -q` 通过。

### 问题 4：删除 Version 后，已有 Document 无法重新关联

问题：

- 如果用户删除了 `ResumeVersion`，原始 `Document` 仍然会保留在 `/documents`。
- 但最初页面没有提供“把已有 Document 重新挂到某个 Resume Profile 下”的入口。

决策：

- 创建 Resume Version 时应该支持选择已有的 resume Document。
- 这样即使用户删掉了 Version，只要原始 Document 还在，就可以重新关联。

实现：

- `/resumes` 的 Version 表单新增 `Source Document` 下拉框。
- `list_documents` 支持按 `doc_type` 过滤。
- `/resumes` 页面向模板传入已有的 resume documents。
- 修复 API 中 `resume-versions` 创建逻辑，让 `document_id` 和 `source_type` 真正写入数据库。
- 在 service 层增加防呆逻辑：如果传了 `document_id`，但 `source_type` 还是 `manual`，则自动保存为 `document`。

验证：

- 创建临时 Profile。
- 将已有 resume Document 绑定为一个临时 Version。
- 确认新 Version 中的 `document_id` 正确，`source_type=document`。
- 删除临时 Profile 做清理。
- `python -m pytest -q` 通过。

### 问题 5：删除时应该用 hash 还是 document_id

问题：

- 一开始不确定删除 chunks、文件或后续索引时，应该靠 content hash 还是靠 document id。

决策：

- 删除应该以 `document_id` 为主，而不是 content hash。
- hash 不是业务主键。同一份内容可能因为不同用途被上传多次，如果用 hash 删除，容易误删多个逻辑文档。
- hash 更适合用于：
  - 重复上传检测
  - 缓存 key
  - 内容是否变更的判断
  - 外部索引一致性校验

实现：

- PostgreSQL 删除以 `Document.id` 为入口。
- `document_sections` 和 `document_chunks` 都通过 `document_id` 关联，并依赖级联删除。
- 本地文件删除通过当前 `Document.file_path` 执行，并做上传目录安全检查。

延迟项：

- 后续 Milvus vectors、Elasticsearch documents、Neo4j graph nodes 都应该在 metadata/properties 中保存 `document_id`。
- 未来删除 Document 时，需要按 `document_id` 删除外部索引中的记录。

### Phase 3 当前范围

目前已经实现：

- 上传或粘贴 Document。
- 原始文件落盘。
- 文本解析。
- Parent Section 切分。
- Child Chunk 切分。
- 自动创建或关联 Resume Profile / Resume Version。
- 删除 Document，并清理本地文件和本地解析语料。
- 删除 Resume Profile / Resume Version，但不删除原始 Document。
- 将已有 resume Document 重新关联到 Resume Profile。

当前有意延迟：

- 更强的 PDF 版面解析。
- 基于 content hash 的重复上传检测。
- Milvus vector 删除。
- Elasticsearch document 删除。
- Neo4j graph 删除。
- 更完整的删除确认弹窗。
- 删除操作审计日志。

### 后续阶段维护规则

之后每个阶段都应该在这个文档中记录：

- 数据模型边界是否发生变化。
- 手动测试中出现了哪些 UX 困惑。
- 删除、恢复、数据归属规则是否被澄清。
- 哪些地方只是当前阶段的最小实现。
- 哪些能力被明确延迟到了后续阶段。
