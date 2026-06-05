# Phase Review Log

This document records design issues, implementation decisions, fixes, and
deferred work discovered during each phase. Keep it updated after every phase
or meaningful phase refinement.

## How To Use This Log

For each phase update, record:

- Context: what was being built or tested.
- Issue: what was confusing, missing, risky, or incorrectly modeled.
- Decision: the design choice we made.
- Implementation: what changed in code or schema.
- Verification: how it was tested.
- Deferred work: what is intentionally left for a later phase.

## 2026-06-05: Phase 3 Document Ingestion Refinement

### Context

Phase 3 introduced document ingestion for resumes, JDs, and supporting career
materials. The first implementation supported upload, file persistence,
text-only parsing, parent sections, child chunks, Celery parsing tasks, and a
basic documents page.

During manual testing with a real resume PDF, several product and data-model
gaps appeared around how uploaded documents connect to the career domain.

### Issue 1: Resume Upload Did Not Create A Resume Profile

Problem:

- Uploading a document with `doc_type=resume` created a `Document`.
- The `/resumes` page stayed empty because no `ResumeProfile` or
  `ResumeVersion` was created.
- The documents page only allowed selecting an existing resume profile, so the
  first resume upload only showed `None`.

Decision:

- A resume upload should be a complete career-domain action.
- If the user uploads a resume and does not choose an existing profile, the
  system creates a new `ResumeProfile` from the supplied profile title or the
  document title.
- The system then creates a `ResumeVersion` linked to the uploaded `Document`.

Implementation:

- Added `app/domains/documents/career_links.py`.
- Shared the document-to-career linking logic between page routes and API
  routes.
- Added optional `resume_profile_title` and `resume_target_role` fields to
  document upload and text ingestion.
- Backfilled the already uploaded resume document in the local database by
  creating a matching profile and version.

Verification:

- `/documents` renders the new profile fields.
- `/resumes` shows the uploaded resume as a profile with one version.
- `python -m pytest -q` passed.

### Issue 2: Resume Profile, Resume Version, And Document Boundaries Were Unclear

Problem:

- It was easy to assume an uploaded PDF "lives inside" a resume profile.
- In the data model, the relationship is indirect:

```text
ResumeProfile
`-- ResumeVersion
    `-- document_id
        `-- Document
```

Decision:

- Keep raw materials and career organization separate.
- `Document` is the source material and parsed corpus.
- `ResumeProfile` is a career-facing container, such as "AI Agent Intern
  Resume".
- `ResumeVersion` is a specific version under that profile. It may reference a
  document or contain manually entered text.

Implementation:

- The `/resumes` page now shows versions under each profile.
- Version rows show source type and linked document title when available.

Verification:

- Manual page check confirmed profile/version/document data appears as
  separate but connected concepts.

### Issue 3: Delete Semantics Needed To Be Explicit

Problem:

- A document delete and a resume version delete can look similar in the UI, but
  they should not mean the same thing.
- Deleting a resume profile or version should not accidentally delete the raw
  uploaded PDF.

Decision:

- Deleting a `Document` is destructive for the raw corpus:

```text
Delete Document
-> delete documents row
-> delete document_sections
-> delete document_chunks
-> delete stored upload file under uploads/documents
```

- Deleting a `ResumeVersion` only removes the career-domain version record.
- Deleting a `ResumeProfile` removes the profile and its versions, but keeps
  raw documents.

Implementation:

- Added `delete_document` and `delete_stored_file` in document service.
- Added page and API delete routes for documents.
- Added delete routes for resume profiles and resume versions.
- Added delete buttons with browser confirmation prompts.
- `delete_stored_file` only deletes files under the configured upload
  directory.

Verification:

- Created a temporary document, parsed it, deleted it, and confirmed:
  - document row removed
  - sections removed
  - chunks removed
  - stored file removed
- `python -m pytest -q` passed.

### Issue 4: Existing Documents Could Not Be Reattached After Deleting A Version

Problem:

- If a user deleted a `ResumeVersion`, the `Document` stayed in `/documents`,
  but there was no UI path to attach that existing document to a profile again.

Decision:

- Resume version creation should support selecting an existing resume document.
- This keeps raw documents reusable and makes delete/recovery behavior
  understandable.

Implementation:

- Added a `Source Document` select field to the `/resumes` version form.
- Added `doc_type` filtering to `list_documents`.
- The `/resumes` page now passes existing resume documents into the template.
- Fixed API resume-version creation so `document_id` and `source_type` are
  actually persisted.
- Added a service guard: if `document_id` is present and `source_type` is still
  `manual`, store it as `document`.

Verification:

- Smoke tested creating a temporary profile and attaching the existing resume
  document as a version.
- Confirmed the new version stored the expected `document_id` and
  `source_type=document`.
- Cleaned up the temporary profile.
- `python -m pytest -q` passed.

### Issue 5: Should Deletes Use Hash Or Document ID?

Problem:

- It was unclear whether deleting chunks/files should be driven by content hash
  or by document id.

Decision:

- Deletion should be driven by `document_id`, not content hash.
- A hash is not a business identity. The same content can be uploaded more than
  once for different purposes.
- Hashes are better suited for duplicate detection, cache keys, content-change
  checks, and index consistency.

Implementation:

- PostgreSQL deletes are keyed by `Document.id`.
- Parsed sections and chunks are related through `document_id` with cascade
  behavior.
- Stored file deletion is driven by the deleted document's `file_path`, with an
  upload-directory safety check.

Deferred work:

- Later Milvus vectors, Elasticsearch documents, and Neo4j graph nodes should
  also store `document_id` in metadata/properties.
- A future delete flow should remove external index records by `document_id`.

### Phase 3 Current Scope

Implemented now:

- Upload or paste document.
- Store raw file.
- Parse text.
- Create parent sections and child chunks.
- Create or attach resume profile/version records.
- Delete document plus local parsed corpus.
- Delete resume profile/version without deleting raw documents.
- Reattach existing resume documents to resume profiles.

Intentionally deferred:

- Layout-aware PDF parsing.
- Deduplication by content hash.
- Milvus vector deletion.
- Elasticsearch document deletion.
- Neo4j graph deletion.
- A richer UI confirmation modal.
- Full audit log for delete operations.

### Rule For Future Phases

Every phase should update this document when:

- A model boundary changes.
- A UX confusion appears during manual testing.
- A deletion, recovery, or data ownership rule is clarified.
- A placeholder is intentionally kept.
- An implementation is deferred to a later phase.
