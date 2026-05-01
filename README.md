# Four Pavilion Cognitive Architecture — Timestamp Record

This repository maintains SHA-256 hashes of key intellectual property documents
for the Four Pavilion Cognitive Architecture (四阁架构).

> **Purpose**: Establish an immutable timestamp record for IP protection.
> Hashes are one-way — they prove file contents existed at a point in time
> without revealing the contents themselves.

---

## Repository Structure

| Directory | Period | Documents | Description |
|-----------|--------|-----------|-------------|
| [三阁时期/](三阁时期/) | 2026-04-29 — 2026-04-30 | 8 | Three Pavilion era (v1–v3): original architecture, proposals, communication framework |
| [四阁项目/](四阁项目/) | 2026-05-01 — | 15 | Four Pavilion project: core docs, test materials, mind maps, architecture comparison |

---

## Timeline

- **v1** (2026-04-29): Initial 6 core IP documents timestamped
- **v2** (2026-04-29): Apple Intelligence proposal added
- **v3** (2026-04-30): Three Pavilion → Four Pavilion evolution, hourglass pipeline designed
- **v4** (2026-05-01): Complete Four Pavilion project system — 15 documents across core design, test materials, mind maps, and independent architecture comparison analysis. First test executed. Decision to abandon Hermes and build native system.

---

### Verification

```bash
shasum -a 256 <document_path>
```
