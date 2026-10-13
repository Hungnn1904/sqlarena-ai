# EnterpriseDB Validation Report

## Environment

- Run date: 2026-10-10
- Database: `enterprise_db`
- Host/port: `localhost:5432`
- User: `postgres`
- PostgreSQL: 18.3
- Random seed: `20261010`
- Runner: `python .\generate_seed.py --validate`

## Schema Audit

- Fixed `postgre/schema_code.sql` so `chk_salary_history_amounts` is dropped before `old_salary` is removed.
- Confirmed post-migration columns:
  - `salary_history`: `salary`, no `old_salary/new_salary`.
  - `payments`: `attempted_at`, no `completed_at`.
  - `inventory_transactions`: `order_item_id`, no `reference_type/reference_id`.
- Kept the supplied BR validator logic intact; no validator checks were weakened or bypassed.

## Seeded Table Counts

| Table | Rows |
| --- | ---: |
| customers | 300 |
| customer_addresses | 363 |
| categories | 20 |
| suppliers | 30 |
| products | 250 |
| departments | 8 |
| employees | 100 |
| warehouses | 8 |
| orders | 1000 |
| order_items | 2892 |
| order_status_history | 2958 |
| inventory_transactions | 3160 |
| salary_history | 184 |
| payments | 1729 |
| refunds | 35 |
| operating_expenses | 240 |

## Business Rule Validation

Result from `logs/05_br_validation.log`: all BR01-BR16 PASS.

| Result | Value |
| --- | ---: |
| Overall status | PASS |
| Total violations | 0 |

## Scenario Coverage

Result from `logs/06_coverage_validation.log`: PASS, 18/18 checks.

Highlights:

- Order statuses: pending 110, processing 160, shipped 240, delivered 390, cancelled 100.
- Payments: failed 939, success 790.
- Refunds: completed 25, failed 5, pending 5.
- Customers without orders: 37.
- Products without orders: 20.
- Full physical-return orders: 39.
- Processing orders with partial inventory sale rows: 39.
- Employees without salary history: 16.
- Employees with multiple salary records: 67.
- Order month span: 19 months, from 2025-03-01 to 2026-09-12.

## Source Document Conflicts Noted

- Older text mentions order status `confirmed`; final validator/schema uses `processing`.
- Older text mentions `inventory_transactions.reference_type/reference_id`; final migration uses `order_item_id`.
- Older text mentions `salary_history.old_salary/new_salary`; final migration uses `salary`.
- Older text mentions `payments.completed_at`; final migration drops it.
- Cancelled-after-success-payment was not generated because the refund policy for that case is not fully specified.

## Evidence Files

- `logs/05_br_validation.log`
- `logs/06_coverage_validation.log`
- `build/seed_summary.json`
- `build/enterprise_seed_data.sql`
