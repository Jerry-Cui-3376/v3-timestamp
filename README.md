# v3 Architecture — Timestamp Record

This repository maintains SHA-256 hashes of key intellectual property documents
for the Three Pavilion Cognitive Architecture and v3 Language Behavior Recognition System.

> **Purpose**: Establish an immutable timestamp record for IP protection.
> Hashes are one-way — they prove file contents existed at a point in time
> without revealing the contents themselves.

---

## Version 2 — 2026-04-29 20:21:11 UTC

**Context**: Architecture advancement — Apple Intelligence proposal (full_proposal_v1.md) added.
The Three Pavilion architecture has been formalized into a complete proposal for Apple,
representing a significant architecture version iteration.

### Document Hashes

| SHA-256 Hash | Document |
|-------------|----------|
| `c9ce1dda82faa84397dc9cdb2c64cae6de72e56af57d341e0e2953dfa74f8c70` | v3语言行为识别系统方案v2.txt |
| `beb1818acac163e17dc80977992f37717ce4ca62be4bbef89f70fd41653bd903` | v3商业化完整策略.txt |
| `c5e6d14f978285d4e6b5e7aba0ef1c96e62443cbd94a721f1099a1e40b0244eb` | 三阁认知架构方案v1.txt |
| `ef9795e453d963c1e0357a036a3628deafec8f620b79cc5c46d19b2bd5e17ac3` | ai_communication_framework.md |
| `d5047886da4f4e54699a99e4a2a2828d2e855f57e94442f95baa6f651ef92722` | EXTRACTION_PROMPT_v3.txt |
| `7a47886c3ec175b5f97267db76b3a7595ec7c33fa43bf9fce792722c5e4cc0ce` | 人类沟通行为分析与描述 - 给AI的教材.txt |
| `fc202eb9eefd1b2f60001391352927a4d1cc7556f07fd8467ecdd6b996e82824` | **full_proposal_v1.md** *(Apple Intelligence Architecture Upgrade Proposal — NEW)* |

> Documents marked **NEW** were added in this version.

---

## Version 1 — 2026-04-29 07:25:57 UTC

**Context**: Initial timestamp record. Original SHA-256 hashes of 6 core IP documents.

### Document Hashes

| SHA-256 Hash | Document |
|-------------|----------|
| `c9ce1dda82faa84397dc9cdb2c64cae6de72e56af57d341e0e2953dfa74f8c70` | v3语言行为识别系统方案v2.txt |
| `beb1818acac163e17dc80977992f37717ce4ca62be4bbef89f70fd41653bd903` | v3商业化完整策略.txt |
| `c5e6d14f978285d4e6b5e7aba0ef1c96e62443cbd94a721f1099a1e40b0244eb` | 三阁认知架构方案v1.txt |
| `ef9795e453d963c1e0357a036a3628deafec8f620b79cc5c46d19b2bd5e17ac3` | ai_communication_framework.md |
| `d5047886da4f4e54699a99e4a2a2828d2e855f57e94442f95baa6f651ef92722` | EXTRACTION_PROMPT_v3.txt |
| `7a47886c3ec175b5f97267db76b3a7595ec7c33fa43bf9fce792722c5e4cc0ce` | 人类沟通行为分析与描述 - 给AI的教材.txt |

---

### Verification

Any party with access to the original documents can verify authenticity by
computing the SHA-256 hash of each document and comparing it against the
record above.

```bash
shasum -a 256 <document_path>
```
