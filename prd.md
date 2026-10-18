\## 2026-10-18 Outeniqua PGS Digital Platform — Design



\### 1. Purpose \& Objectives

Digitize the Outeniqua Participatory Guarantee System (PGS) to eliminate paper clipboards, reduce administrative overhead, and build consumer trust. The system provides:

1\. \*\*Offline-First Assessor PWA:\*\* A zero-build mobile web app for farm walkabouts to capture checklist data, high-resolution evidence photos, and digital signatures without cellular reception.

2\. \*\*Public RAG Chatbot:\*\* A strictly grounded AI assistant allowing farmers and consumers to query the SAOSO v2.1 Organic Standards and Outeniqua SOPs without hallucinations.



\### 2. Architecture \& Tech Stack (Zero-Build Monolith)

\* \*\*Architecture Pattern:\*\* Majestic Monolith (Zero-Build). Single Django deployment; no Node.js runtime or frontend bundler required.

\* \*\*Backend:\*\* Python / Django with PostgreSQL + `pgvector`.

\* \*\*Frontend (Assessor PWA):\*\* Native ES Modules Vanilla JS (`<script type="module">`). Uses browser-native APIs and raw Service Workers (`sw.js`).

\* \*\*Frontend (Public / Chatbot):\*\* Standard Django Templates (`.html`) with lightweight server-rendered HTML.

\* \*\*Vendored Dependencies:\*\* Self-hosted in `static/pwa/vendor/`:

&#x20; \* `localforage.min.js` (IndexedDB wrapper for offline storage)

&#x20; \* `signature\_pad.umd.min.js` (Canvas-based signature capture)

\* \*\*Storage:\*\* PostgreSQL for structured data and vector embeddings; AWS S3 (or S3-compatible storage) for production evidence photos and generated PDFs.



\### 3. Domain Modules (Django Apps)

Organized into three bounded contexts to respect vertical slicing:

\* `\_core`:

&#x20; \* \*\*Models:\*\* `User` (Admin, Peer Assessor, Consumer), `Farm` profiles, public registry.

&#x20; \* \*\*Views:\*\* Marketing pages, public farm profiles with QR-code verification.

\* `\_assessment`:

&#x20; \* \*\*Models:\*\*

&#x20;   \* `AssessmentTemplate`: Defines questions as a JSON schema. Versioned/snapshotted on audit creation to guarantee historical audit immutability.

&#x20;   \* `AssessmentResponse`: Stores answers in a `JSONField`, linked to a specific template snapshot.

&#x20;   \* `EvidencePhoto`: Stores individual photos linked to an `AssessmentResponse`.

&#x20;   \* `CorrectiveAction`: Tracks non-conformances (`Minor`, `Major`, `Critical`), remedies, and due dates.

&#x20; \* \*\*Services:\*\* `pdf\_service.py` (WeasyPrint compilation for "Sheet J: Outcome Summary"), `sync\_service.py` (validating and persisting incoming offline audits).

\* `\_chatbot`:

&#x20; \* \*\*Models:\*\* `DocumentChunk` (stores chunked SAOSO 2.1 text + `pgvector` embeddings), `ChatSession`, `EscalatedQuery` (stores questions where the bot triggered fallback).

&#x20; \* \*\*Services:\*\* `rag\_service.py` (Hybrid Search combining Postgres `tsvector` full-text search with `pgvector` cosine similarity; strict system prompt runner).



\### 4. Data Flow \& Offline Protocols

\* \*\*PWA Caching \& Walkabout:\*\*

&#x20; 1. On Wi-Fi, `sw.js` caches the PWA shell, styles, and vendored JS.

&#x20; 2. The app pre-fetches active `AssessmentTemplate` schemas and assigned `Farm` metadata into IndexedDB.

&#x20; 3. During the walkabout (offline), all checklist taps, notes, signature vectors, and full-resolution Base64 photos are persisted to IndexedDB.

\* \*\*The Split-Sync Protocol:\*\*

&#x20; 1. Once `navigator.onLine` fires, the app immediately POSTs the text JSON payload to `/api/assessments/sync/`.

&#x20; 2. Django validates the schema, records the `AssessmentResponse`, and returns a `response\_id`.

&#x20; 3. A background queue iterates through the stored photos and POSTs them one-by-one to `/api/assessments/<id>/photos/` to prevent HTTP timeouts.

&#x20; 4. On queue completion, Django compiles the final "Sheet J" PDF, sends email notifications, and updates the farm's public status.

\* \*\*Strict RAG Execution \& Fallback:\*\*

&#x20; 1. User submits query on public site.

&#x20; 2. Backend performs hybrid search (`pgvector` <=> cosine distance + `tsvector` @@ query).

&#x20; 3. Retrieved chunks are injected into a strict system prompt forbidding external training data.

&#x20; 4. If context is insufficient, LLM returns the exact string: `"I cannot find a definitive answer in the SAOSO standards."`

&#x20; 5. The UI detects this string and displays an `\[Escalate to PGS Committee]` action, creating an `EscalatedQuery` for administrative follow-up.



\### 5. Architectural Constraints \& Risks

\* \*\*Zero Build Pipeline:\*\* No npm, Vite, or Webpack in CI/CD or Docker. Static files are collected purely via `python manage.py collectstatic`.

\* \*\*BUILD\_PRINCIPLES Compliance:\*\*

&#x20; \* Views must remain under 20 lines (routing and HTTP serialization only).

&#x20; \* All orchestration resides in `services.py` modules with explicit Data Flow Contract docstrings.

&#x20; \* Code units must not exceed the 30KB limit per file.

\* \*\*Storage Quota:\*\* Mobile Safari can clear IndexedDB if device storage is depleted. \*Mitigation:\* The PWA checks `navigator.storage.estimate()` and prompts the user to sync as soon as network connectivity is restored.

Public facing frontend ideally replacing the website at - https://pgsouteniqua.wordpress.com/ all relevant info
