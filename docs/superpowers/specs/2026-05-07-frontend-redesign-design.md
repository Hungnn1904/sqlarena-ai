# SQLArena Frontend v2 Design Spec
## 2026-05-07

### Visual System (từ pipeline.html)
- **bg**: #080c14, **surface**: #0d1320, **surface2**: #111827, **border**: #1e2d45
- **text**: #e2eaf6, **muted**: #5a7298, **muted2**: #8ba3c7
- **cyan**: #00d4ff, **green**: #00e5a0, **amber**: #ffb830, **rose**: #ff4d6d, **purple**: #a78bfa
- **Fonts**: Syne (sans), JetBrains Mono (mono)
- **Grid**: 48px grid background pattern, opacity 0.3
- **Animations**: Framer Motion — slide-in, pulse, glow, layoutId

### Components

1. **Header** — gradient text (white→cyan→green), pulse badge, 72px padding
2. **StatsBar** — 5-column grid, count-up animation, border hover
3. **PipelineTimeline** — vertical line, numbered dots, accordion, slide-in delays
4. **FlowDiagram** — ASCII nodes với cyan/green/amber/rose borders
5. **ComparisonTable** — full-width, hover highlight, ok/warn/bad badges
6. **ScheduleGrid** — time-based 2-column layout
7. **QuestionCards** — card grid thay table, expandable detail, badges
8. **GenerateForm** — difficulty chips, topic select, animated submit
9. **VerifySQLEditor** — Monaco dark, 3-panel layout, pass/fail animation
10. **Navigation** — tab bar với layoutId animated underline

### Pages
- Dashboard: Header + StatsBar + PipelineTimeline (3 sections)
- Generate: Form + live preview
- Questions: Card grid + filter + pagination
- Pipeline: Full timeline + flow diagram + comparison table + schedule
- Verify: SQL editor + results

### Technical
- Next.js 16 + TypeScript + Tailwind CSS v4
- Framer Motion cho animations
- React Query cho API
- Axios instance gọi localhost:8000
- Responsive (mobile-first)
