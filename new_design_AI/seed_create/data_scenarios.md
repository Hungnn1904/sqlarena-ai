# EnterpriseDB Seed Scenarios

This dataset is generated with fixed seed `20261010` for a local PostgreSQL test database named `enterprise_db`.

## Scale Targets

| Area | Target |
| --- | ---: |
| Customers | 300 |
| Products | 250 |
| Employees | 100 |
| Warehouses | 8 |
| Orders | 1000 |
| Order items | about 2500+ |
| Operating expenses | 240 |

## Designed Coverage

- Customers include active and inactive accounts, multiple cities, single-address and multi-address customers, and at least 20 customers with no orders.
- Products include inactive products, a category tree, multiple suppliers, products with stock but no sales, and at least 10 products never ordered.
- Orders cover all approved statuses: `pending`, `processing`, `shipped`, `delivered`, and `cancelled`.
- Status history always starts at `pending`, follows legal transitions, and ends at `orders.status`.
- Processing orders include successful payment and a subset with partial inventory sale rows.
- Shipped and delivered orders have one sale transaction for every order item.
- Pending and cancelled orders have no sale transactions.
- Delivered orders include full physical-return scenarios; when any item is returned, every item in that order is returned.
- Payments include failed attempts and exactly one successful payment for `processing`, `shipped`, and `delivered` orders.
- Refunds include `completed`, `pending`, and `failed`, with completed refund totals never exceeding the successful payment amount.
- HR data has 8 departments, 100 employees, a depth-3 management tree, valid department managers, and employees with no salary history.
- Salary history uses the post-migration `salary` column. Latest salary history equals `employees.current_salary` when history exists.
- Inventory has imports before sales/returns, no negative running stock, and warehouse capacity is intentionally high enough to avoid capacity violations while preserving realistic movement.
- Expenses span multiple departments/categories and use approvers hired before the expense date.

## Intentional Zero-Row / Sparse-Join Cases

- Customers without orders.
- Products without order items.
- Employees without salary history.
- Departments and employees with nullable optional references.
- Pending orders without successful payments.
- Orders without refunds.

## Document Conflicts Resolved

- Older document text mentions `confirmed`, but the enforced lifecycle is `pending -> processing -> shipped -> delivered`, with cancellation from `pending` or `processing`.
- Older document text mentions `inventory_transactions.reference_type/reference_id`; the migrated schema uses `order_item_id`.
- Older document text mentions `salary_history.old_salary/new_salary`; the migrated schema uses `salary_history.salary`.
- Older document text mentions `payments.completed_at`; the migrated schema drops that column and uses `payments.attempted_at`.
