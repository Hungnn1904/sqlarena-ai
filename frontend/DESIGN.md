# SQLArena AI — Design System (`DESIGN.md`)

> **Archetype**: `editorial-proof` / `dense-workspace` (`Operate` mode)
> **Canonical Team Palette**: **Editorial Sage & Warm Paper** (`329554e` baseline — locked against brownfield drift)

## 1. Overview
- **Mode**: `Operate` (nền tảng thực hành, chấm bài tự động & quản trị ngân hàng đề PostgreSQL 17 kiểu Code-PTIT).
- **Identity Lock**: Bề mặt giấy ấm (`#F5EDDC` / `#FBF7EC`) kết hợp xanh xô thơm (`#5C7F71`), đồng đỏ (`#B2653B`) và lưới kỹ thuật 48px tinh tế. Tuyệt đối không ghi đè sang nền xám lạnh SaaS hoặc chèn khối quảng cáo rườm rà ở màn hình chưa đăng nhập.

## 2. Color Tokens (`frontend/src/app/globals.css`)
| Role | Token | Light Mode (`html.light`) | Dark Mode (`html.dark`) |
| :--- | :--- | :--- | :--- |
| Canvas | `--paper` | `#F5EDDC` | `#131514` |
| Card Surface | `--surface` | `#FBF7EC` | `#1B1E1C` |
| Muted Surface | `--soft` | `#EBE2CD` | `#262A27` |
| Primary Ink | `--ink` | `#181818` | `#F5EDDC` |
| Secondary Text | `--text2` | `#45423A` | `#D3CCBA` |
| Muted Text | `--muted` | `#6F6B60` | `#A19C8E` |
| Primary Brand | `--green` | `#5C7F71` (hover `#496B5D`) | `#7DA796` (hover `#97BCAB`) |
| Secondary Accent | `--copper` | `#B2653B` | `#D47F4E` |
| Warning / Medium | `--gold` | `#8A5D14` | `#D6A04A` |
| Danger / Hard | `--red` | `#802520` | `#DE6A63` |

## 3. Typography & Layout Rules
- **Font Family**: `Be Vietnam Pro` cho toàn bộ giao diện tiếng Việt có dấu; `ui-monospace` chỉ dùng bên trong `<code>`, `<pre>`, và trình soạn thảo SQL Monaco; số liệu bảng bật `font-variant-numeric: tabular-nums`.
- **Unauthenticated Surface**: Chỉ hiển thị thanh tiêu đề `SQLArena` và thẻ `Đăng nhập / Đăng ký` gọn ở trung tâm — không hiển thị Hero quảng cáo hay bảng kết quả giả lập.
- **Role-Contextual Navigation**: Học viên (`role = learner`) chỉ thấy `Làm bài · Tiến độ · Xếp hạng`; Quản trị viên (`role = admin`) luôn hiển thị đúng vai trò `Quản trị viên` và truy cập được `Quản trị` trên cả cổng `:3000` lẫn `:4000` / `/admin`.
