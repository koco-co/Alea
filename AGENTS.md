# Alea Agent Rules

These rules apply to every task in this repository.

## Preserve user work

- Treat existing tracked, untracked, staged, and deleted files as user-owned unless the current request explicitly places them in scope.
- Never restore, discard, reformat, or overwrite unrelated changes to make the worktree look clean.
- Read the current diff and the relevant source documents before editing.

## Product sources of truth

- `docs/PRD.md` is the product-behavior and information-architecture source of truth.
- `DESIGN.md` is the visual-system source of truth.
- The OpenDesign prototype is an executable representation of those documents, not an independent source of product requirements.
- Before changing a product flow, role, permission, route, state, field, label, rule, or interaction, identify the corresponding PRD section.
- Any user-requested product change must be synchronized in the same task:
  - update `docs/PRD.md`;
  - update every affected OpenDesign prototype screen and state;
  - update `DESIGN.md` when tokens, typography, layout rules, components, imagery, or motion conventions change;
  - update any route/coverage/evidence ledger maintained for the prototype.
- Do not silently resolve a conflict between PRD and prototype. State the conflict, choose the user-requested behavior, and synchronize both sides.
- A visual-only polish that does not change product meaning does not require a PRD behavior change, but shared visual rules must still be reflected in `DESIGN.md`.

## Visual verification is mandatory

- Never approve a prototype change by reading HTML, CSS, JavaScript, or component source alone.
- Open the actual prototype in OpenDesign and visually inspect the rendered result.
- Exercise every affected navigation item, tab, menu, dropdown, modal, form control, toggle, filter, empty state, loading state, error state, permission state, and recovery path.
- Capture fresh screenshots after each material change. Inspect the saved image before accepting it; reject blank, loading, cropped, stale, wrong-window, or wrong-state captures.
- Compare the reference and implementation at the same viewport. Fix visible mismatches, capture again, and repeat until the comparison passes.
- Desktop acceptance viewport: `1440 × 900`. Mobile acceptance viewport: `390 × 844`. Add narrower/wider checks when a layout breakpoint is involved.
- For each verified route/state, record the exact action performed, observed result, screenshot path, and any unverified remainder.
- Static checks and a generated runner are supplementary evidence only. They never replace rendered visual verification.

## Production-grade prototype bar

- The prototype must cover every in-scope route and state declared by `docs/PRD.md`; missing pages must be listed explicitly and block a “production-ready” claim.
- Primary navigation and cross-module transitions must work from the rendered prototype, preserve the active state, and land on the correct content.
- No screen may be an empty shell, a title-only placeholder, or a dead control.
- Check hierarchy, alignment, spacing rhythm, typography, line height, wrapping, truncation, grid balance, density, card proportions, borders, radii, shadows, icon alignment, hover/focus/pressed/disabled states, overflow, sticky elements, and responsive reflow.
- Use realistic, internally consistent demonstration data. Never invent data where the PRD requires a missing-source state.
- User and administrator shells must follow the PRD permission matrix. A user must not see administrator entry points.
- Do not claim “all routes”, “full flow”, “production-ready”, or equivalent unless the route/state matrix is complete and every declared item has fresh visual evidence.

## Asset and identity quality

- Never fake visible assets with text symbols, emoji, ASCII, placeholder boxes, CSS drawings, handcrafted SVGs, or initials pretending to be finished artwork.
- Use official or authoritative assets when a real club, national team, competition, player, coach, referee, or AI vendor is shown and the asset can be used lawfully.
- For fictional demonstration entities, use coherent generated raster assets rather than borrowing a real organization’s identity.
- Club and national-team badges must share a consistent optical size, transparent padding, crop, background treatment, and fallback behavior.
- Player, coach, referee, and account avatars must have consistent crop, lighting, aspect ratio, resolution, and fallback states. Random unrelated portraits are not acceptable.
- AI identities must use official vendor marks or wordmarks. In particular, do not approximate the Anthropic mark or wordmark with ordinary text; verify its font treatment, optical size, padding, and contrast visually.
- Record each nontrivial asset’s source, license/provenance, intended use, file path, dimensions, and fallback in an asset ledger.
- Broken images, mismatched visual styles, stretched crops, low-resolution assets, and undocumented temporary placeholders block completion.

## OpenDesign workflow

- Use OpenDesign as an iterative design partner, not as an automatic completion oracle.
- Before sending any OpenDesign prompt, inspect the current run state and queue. Keep at most one OpenDesign task active: if a run is executing, wait for it to finish, inspect its actual file changes and rendered result, and clear any accidental queued messages before sending the next prompt.
- Use the Design Toolbox shortcuts when relevant, including:
  - `智能匹配下一步`
  - `找图 / 找参考图`
  - `找 icon / 替换 icon`
  - `替换页面图片`
  - `参考图获取 / 风格提取`
  - `加动画 / 动效`
  - `动效润色`
- Every OpenDesign prompt must name the exact target file/route/state, the observed visual problem, the intended result, preserved behavior, and acceptance criteria.
- After each OpenDesign response, inspect the rendered page. If the request was ignored or only partially applied, send a narrower correction prompt. If repeated prompts still fail, edit the prototype source directly and re-run visual verification.
- Never treat OpenDesign’s success message as evidence that the design changed.

## Reference implementation policy

- Search established open-source products and component libraries before inventing complex settings, administration, tables, filters, charts, or configuration experiences.
- Inspect source, tests, states, and screenshots—not only a marketing image.
- Adapt information architecture and interaction patterns to Alea’s PRD and design system. Do not copy unrelated product semantics or paste an entire foreign interface into Alea.
- When source code is reused, verify its license, preserve required attribution, record provenance, and keep the adapted code maintainable.
- For AI configuration and settings, the official `nexu-io/open-design` repository is a required reference. Inspect at least:
  - `apps/web/src/components/SettingsDialog.tsx`
  - `apps/web/tests/components/SettingsDialog.execution.test.tsx`
  - `docs/testing/e2e-coverage/settings.md`

## Settings and AI configuration minimum

- `/console/admin/lineup` and `/console/admin/settings` must be complete interactive prototype surfaces, not empty pages.
- AI provider configuration must visibly cover provider identity, endpoint/protocol, masked API key with replace/clear behavior, model search and selection, custom model ID, connection test and result, loading/saving/saved/error states, and secure secret-tail display.
- AI instance management must support 1–3 instances per provider, nickname, enable/disable, instance badge, model, reasoning level where supported, timeout/concurrency or other PRD-approved runtime controls, prompt version, and clear validation.
- System settings must cover every category declared in PRD §15.6, including versioned scoring weights, betting-rule versions, simulated-account parameters, sync cadence, scheduled roundtables, auto-review, user management, risk copy, and prompt versions.
- Configuration patterns borrowed from Open Design must be restyled and renamed for Alea; Local CLI/BYOK concepts must not be copied unless the PRD is explicitly updated to require them.

## Completion evidence

- Maintain a route/state traceability matrix mapping:
  - PRD section;
  - route or prototype file;
  - role;
  - important states and interactions;
  - reference used;
  - latest screenshot;
  - verification result;
  - remaining gap.
- Before final handoff, run syntax and asset-reference checks, then perform a fresh visual regression pass.
- Final reporting must include exact workflow targets, exit codes for executable checks, passed/failed/skipped counts, screenshot and audit paths, and a literal list of anything not verified.
- A task remains active while any safe, in-scope, immediately executable verification or repair remains.

<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->
