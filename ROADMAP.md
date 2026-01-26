# PivotStream Studio — Product & Engineering Roadmap

## Assumptions
- Team size: 1–3 engineers + 1 designer (part‑time).
- Stack remains FastAPI + vanilla JS + static assets.
- Target: polished, production‑ready RSVP reader with EPUB/PDF import.

## MVP‑First Path (Shortest viable route)
- **Week 1–2:** Stabilize core flows (imports, parsing, playback), add basic tests, ship a minimal deploy.
- **Week 3:** Tighten UX/accessibility, add documentation and telemetry basics, complete production checklist.

## Delighter Path (Extended polish)
- **Weeks 4–8:** Advanced reading controls, richer library/chapter navigation, offline support, better typography/animations, and deeper analytics.

---

## Phase 0 — Baseline Audit & Planning (Week 1)
**Goals**
- Establish baseline metrics and a production checklist.
- Identify critical UX/tech debt and missing tests.

**Key Tasks**
- Map current user flows: paste, EPUB, PDF, playback, chapters.
- Create a simple QA checklist and bug backlog.
- Define performance targets (e.g., first render < 1s for 50k words).
- Decide deployment target (single‑container on Render/Fly/VM).

**Dependencies**
- Access to current repo and sample EPUB/PDFs.

**Risks**
- Large documents cause UI slowdowns or parsing delays.

**Demo Criteria**
- Documented baseline metrics + prioritized backlog.

---

## Phase 1 — Core Stability & Reliability (Weeks 1–2)
**Goals**
- Make imports and playback reliable with clear errors.
- Ensure parsing performance for large docs.

**Key Tasks**
- Backend: harden `/api/epub` and `/api/pdf` with robust error messages and timeouts.
- Backend: add text extraction fallbacks (e.g., skip empty pages, clean whitespace).
- Frontend: add load spinners + progress messages for imports.
- Frontend: ensure chapter list updates for EPUB and hides gracefully for PDF.
- Performance: debounce parsing and avoid unnecessary DOM reflows.
- Add unit tests for text parsing and EPUB/PDF extraction edge cases.

**Dependencies**
- Sample EPUB/PDF test fixtures.

**Risks**
- Some PDFs are image‑only → extraction fails.

**Acceptance Criteria**
- Imports succeed or fail with clear UI messages.
- EPUB chapters list is populated or a clear fallback is shown.
- No crashes when switching between inputs and sources.

**Demo Criteria**
- Import a large EPUB and PDF live; playback starts immediately.

---

## Phase 2 — UX/UI Polish & Accessibility (Weeks 2–3)
**Goals**
- Make the UI feel cohesive and usable for long reading sessions.
- Meet baseline accessibility standards.

**Key Tasks**
- Typography tune‑up: refine font sizes/line heights, ORP visibility.
- Improve layout responsiveness for tablet/mobile.
- Add keyboard shortcuts + visible help.
- Ensure ARIA labels for buttons, focus states, and color contrast.
- Add in‑app tips for speed controls and chapter navigation.

**Dependencies**
- Design pass or quick style guide.

**Risks**
- Accessibility regressions when adding custom controls.

**Acceptance Criteria**
- Keyboard navigation works for all controls.
- Viewer and controls are clear on 375px and 1440px widths.

**Demo Criteria**
- Live run on mobile + desktop with full keyboard control.

---

## Phase 3 — Testing & Release Hardening (Weeks 3–4)
**Goals**
- Prevent regressions and ship confidently.

**Key Tasks**
- Add tests for parsing, chapter mapping, and PDF extraction.
- Add basic E2E smoke test (import + play).
- Pre‑commit checks for formatting/linting.
- Add error logging and client‑side event tracking (minimal analytics).

**Dependencies**
- Test harness choice (pytest + minimal JS test runner).

**Risks**
- Time spent on tooling over delivery.

**Acceptance Criteria**
- CI passes on every push.
- E2E import/play smoke test is green.

**Demo Criteria**
- CI pipeline runs on sample EPUB/PDF assets.

---

## Phase 4 — Deployment & Documentation (Weeks 4–5)
**Goals**
- Production deploy with clear docs and operational runbooks.

**Key Tasks**
- Create deployment instructions (Docker or simple host).
- Add environment configuration and secrets guidance.
- Add README usage and troubleshooting guide.
- Create a basic changelog.

**Dependencies**
- Hosting target decision.

**Risks**
- Deployment complexity (file sizes, memory limits).

**Acceptance Criteria**
- One‑command deploy documented.
- Public demo URL or self‑host instructions verified.

**Demo Criteria**
- Production instance running with sample imports.

---

## Phase 5 — Delight & Advanced Features (Weeks 5–8)
**Goals**
- Make the app a standout reader tool.

**Key Tasks**
- Reading modes: speed ramp profiles, theme presets.
- Save/restore reading sessions (position, speed, last chapter).
- Library management: recent files, bookmarks, history.
- Improved chapter navigation with anchors.
- Auto‑create chapter chunks for long documents without a TOC (≈20‑minute readable segments).
- Offline support via Service Worker.
- Advanced analytics: reading sessions, completion rates.

**Dependencies**
- Storage approach (localStorage/IndexedDB).

**Risks**
- Feature creep.

**Acceptance Criteria**
- New features are optional, don’t regress core flow.
- Session restore returns to last position and speed within 1 click.

**Demo Criteria**
- Bookmarks and chapter jumping are reliable across sessions.
- A PDF without chapters gets auto‑chunked into ~20‑minute segments.

---

## Work Breakdown by Domain

### UX/Design
- Visual hierarchy for panels, spacing, and typography.
- Clearer empty states and loading states.

### Performance
- Avoid heavy DOM updates per word.
- Precompute token arrays; lazy‑load chapter content if needed.

### Accessibility
- Full keyboard control and visible focus.
- Contrast checks on focus window and panel labels.

### Backend Stability
- Graceful errors for malformed EPUB/PDF.
- Avoid blocking operations in request handlers.

### Imports (EPUB/PDF)
- Chapter detection improvements for EPUB.
- PDF extraction fallback and messaging for image‑only pages.
- Auto‑chunking into ~20‑minute segments when chapter data is missing.

### Testing
- Parsing unit tests, import tests.
- Minimal E2E for play/pause and jump.
- Session save/restore tests for local storage.

### Analytics/Telemetry
- Simple events: import success/failure, session start/end.
- Opt‑out and privacy notes.

### Reading Sessions
- Save current position, speed, and chapter on exit/refresh.
- Quick resume CTA on load with last session metadata.

### Deployment
- Dockerfile + minimal hosting instructions.
- Health check endpoint.

### Documentation
- “Getting Started” and troubleshooting.
- Feature guide and keyboard shortcuts.

---

## Milestone Summary (By Week)
- **Week 1:** Baseline audit + reliability fixes.
- **Week 2:** UX/accessibility improvements.
- **Week 3:** Tests + CI hardening.
- **Week 4:** Deployment + docs.
- **Weeks 5–8:** Delighters and advanced features.
