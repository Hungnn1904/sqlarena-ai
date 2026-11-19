# Approval Brief: SQLArena AI v2.4 — 9-Point UX, ORDER BY Sync & Multi-Case Grading Overhaul

- **Approval State**: `approved`
- **Mode**: `SOLO-INDIE`
- **Plan Link**: `./plan.md`
- **Owner**: PTIT Capstone Team (`approved_by`: User `/mykit:retro` -> `/mykit:plan` -> `/mykit:fix` -> `/mykit:build` directive, `2026-11-19 22:08`) | **Updated**: 2026-11-19 22:12

---

## 1. Outcome & Success Measure
- **Outcome**: All 9 UX and grading friction points documented in `Các-lỗi-cần-sửa_p2.docx` are resolved across Backend, AI prompt pipeline, and Frontend, delivering compact 80% visual density, explicit sorting prompts, and transparent per-test-case grading.
- **Success Metric**: `9/9` checklist items verified in live Docker browser (`Desktop` + `375px` mobile, `0` console errors), `0` false-WA failures from unstated `ORDER BY`, and `100%` exit-0 pass rate across `pytest`, AI `unittest`, and MyKit gates within 1 build cycle.

## 2. Plain Why
- Students submitting valid SQL failed grading silently when `compare_mode = 'ordered'` checked a hidden `ORDER BY` not written in the Vietnamese prompt, couldn't see database table schemas alongside the prompt without scrolling away, and had no per-test-case feedback after clicking `Nộp bài`. Meanwhile, Admins needed account inspection modals, cleaner manual-review separation, shelf statistics, and compact 80% page density.

## 3. Real Failure Scenario
- **Scenario A (Monaco Hitbox Drift under CSS `zoom: 0.8`)**: Applying `body { zoom: 0.8 }` or `transform: scale(0.8)` shrinks DOM pixels while Monaco Editor computes mouse coordinates in unscaled `clientX`/`clientY` pixels, causing clicks on line 5 column 20 to place the cursor on line 6 column 25 and leaving a 20% whitespace strip below `min-h-screen`.
- **Scenario B (False Wrong-Answer on Unstated Sort)**: `SQL1` (`compare_mode = 'ordered'`) executes `ORDER BY department_id ASC` in `reference_sql` without mentioning sorting in `question`; a learner returning identical rows sorted by `department_name` receives `Sai kết quả` despite satisfying every written requirement.

## 4. Blind-Spots & Trade-offs
| Blind-Spot / Choice | Cost / Latency / Risk | Knowns vs Unknowns |
|---|---|---|
| Root `html { font-size: 80% }` (`12.8px`) vs CSS `zoom: 0.8` | Zero runtime cost; preserves `100svh` and Monaco mouse coordinates when Monaco `fontSize`/`lineHeight` are explicit pixels | `OBSERVED`: Tailwind v4 sizes spacing/typography in `rem`; hardcoded `px` values in `globals.css` must convert to `rem` |
| Deterministic 3-checkpoint decomposition when `live.test_cases` has 1 row | Zero extra DB round-trips (`<2ms`); guarantees `Test case 1..3` verdicts without mutating `enterprise_db` seed tables | `OBSERVED`: Multi-row `live.test_cases` still evaluate every stored dataset row first, appending checkpoints if `<3` |

## 5. Micro-Lesson (`Teaching Moment`)
- **Concept -> Practice**: Scaling a web IDE is like resizing architectural blueprints — shrinking the paper on a photocopier (`CSS zoom`) distorts the ruler grid on an embedded CAD canvas (`Monaco Editor`), whereas changing the base grid unit (`html { font-size: 80% }` `rem` + native Monaco pixel `fontSize`/`lineHeight`) scales every panel proportionally while keeping cursor coordinates exact to the pixel.

## 6. Options, Recommendation & Explicit Decision
- **Option A (Recommended — Active)**: Scale via root `html { font-size: 80% }` + native Monaco options, synchronize `ORDER BY` via `pglast`/SQL parser at both generation/promotion time and startup schema heal, and return `>=3` structured `test_details` checkpoints from `POST /api/v1/submissions`.
- **Option B (Rejected)**: Use CSS `zoom: 0.8` and manual one-off SQL updates (breaks Monaco cursor accuracy and regresses on future AI-generated drafts).
- **Decision Prompt**: Option A executed per user `/mykit:fix` + `/mykit:build` instruction under `SOLO-INDIE` mode.
