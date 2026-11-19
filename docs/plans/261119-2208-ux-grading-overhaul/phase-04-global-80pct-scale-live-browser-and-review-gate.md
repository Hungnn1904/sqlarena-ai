# Phase 04: Global 80% Visual Scale, Live Browser QA, `code-reviewer` Audit & Git Push

- **Evaluator**: `fe-gate.mjs` + `browser` subagent + `code-reviewer` (`Hunter != Verifier`)
- **Verify**: `node ~/.gemini/config/skills/fe-anti-slop/scripts/fe-gate.mjs frontend/src --app`

## Tasks & Done Means
- [x] Scale global typography/spacing via `html { font-size: 80%; }` (`12.8px` root `rem`) in `frontend/src/app/globals.css`, align container max-width (`max-w-[95rem]` = `1216px` across `AuthBar`, `home-client`, `PitchTourBanner`), and isolate Monaco Editor pixel `fontSize: 13` / `lineHeight: 20` so 100% browser zoom renders at compact 80% density with exact cursor coordinates.
- [x] Deploy live Docker stack (`./scripts/deploy-vps.sh`) and verify all 9 items via `browser` subagent at Desktop (`1440x900`) and Mobile (`375x812`) with `0` console errors.
- [x] Run fresh-context `code-reviewer` diff verification (`Hunter != Verifier`, resolving any findings with Round-2 sign-off).
- [x] Run all MyKit gates (`spec-gate.mjs --strict`, `clean-arch-gate.cjs`, `fe-gate.mjs --app`, `debug-gate.mjs`, `devops-gate.mjs`, `verification-before-completion-verify.cjs`) + `mykit run --` receipt (`all exit 0`), commit, push to `origin/main`, and clean up Docker containers.
