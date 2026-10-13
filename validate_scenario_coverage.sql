-- EnterpriseDB scenario coverage validator.
-- RUN AFTER seed data. Read-only against business tables.

BEGIN;

CREATE TEMP TABLE scenario_coverage_results (
    check_name text PRIMARY KEY,
    observed numeric NOT NULL,
    required numeric NOT NULL,
    status text NOT NULL,
    details jsonb
) ON COMMIT PRESERVE ROWS;

INSERT INTO scenario_coverage_results
SELECT 'customers_count', COUNT(*), 300,
       CASE WHEN COUNT(*) >= 300 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','customers')
FROM customers;

INSERT INTO scenario_coverage_results
SELECT 'products_count', COUNT(*), 250,
       CASE WHEN COUNT(*) >= 250 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','products')
FROM products;

INSERT INTO scenario_coverage_results
SELECT 'employees_count', COUNT(*), 100,
       CASE WHEN COUNT(*) >= 100 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','employees')
FROM employees;

INSERT INTO scenario_coverage_results
SELECT 'warehouses_count', COUNT(*), 8,
       CASE WHEN COUNT(*) = 8 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','warehouses')
FROM warehouses;

INSERT INTO scenario_coverage_results
SELECT 'orders_count', COUNT(*), 1000,
       CASE WHEN COUNT(*) >= 1000 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','orders')
FROM orders;

INSERT INTO scenario_coverage_results
SELECT 'order_items_count', COUNT(*), 2400,
       CASE WHEN COUNT(*) >= 2400 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('table_name','order_items')
FROM order_items;

INSERT INTO scenario_coverage_results
SELECT 'all_order_statuses_present', COUNT(DISTINCT status), 5,
       CASE WHEN COUNT(DISTINCT status) = 5 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_object_agg(status, n)
FROM (SELECT status, COUNT(*) n FROM orders GROUP BY status) x;

INSERT INTO scenario_coverage_results
SELECT 'payments_success_and_failed', COUNT(DISTINCT payment_status), 2,
       CASE WHEN COUNT(DISTINCT payment_status) = 2 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_object_agg(payment_status, n)
FROM (SELECT payment_status, COUNT(*) n FROM payments GROUP BY payment_status) x;

INSERT INTO scenario_coverage_results
SELECT 'refund_status_mix', COUNT(DISTINCT refund_status), 3,
       CASE WHEN COUNT(DISTINCT refund_status) >= 3 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_object_agg(refund_status, n)
FROM (SELECT refund_status, COUNT(*) n FROM refunds GROUP BY refund_status) x;

INSERT INTO scenario_coverage_results
SELECT 'customers_without_orders', COUNT(*), 20,
       CASE WHEN COUNT(*) >= 20 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','left join / anti join')
FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

INSERT INTO scenario_coverage_results
SELECT 'products_without_orders', COUNT(*), 10,
       CASE WHEN COUNT(*) >= 10 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','products that can return zero sales')
FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.product_id);

WITH returned_orders AS (
    SELECT oi.order_id,
           COUNT(*) FILTER (WHERE t.transaction_id IS NOT NULL) returned_lines,
           COUNT(*) total_lines
    FROM order_items oi
    LEFT JOIN inventory_transactions t
      ON t.order_item_id = oi.order_item_id
     AND t.transaction_type = 'return'
    GROUP BY oi.order_id
)
INSERT INTO scenario_coverage_results
SELECT 'full_physical_return_orders', COUNT(*), 20,
       CASE WHEN COUNT(*) >= 20 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','full order returns, no partial physical return')
FROM returned_orders
WHERE returned_lines = total_lines AND total_lines > 0;

INSERT INTO scenario_coverage_results
SELECT 'partial_processing_sales', COUNT(DISTINCT o.order_id), 10,
       CASE WHEN COUNT(DISTINCT o.order_id) >= 10 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','processing orders with partial inventory sale rows')
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN inventory_transactions t ON t.order_item_id = oi.order_item_id
WHERE o.status = 'processing' AND t.transaction_type = 'sale';

INSERT INTO scenario_coverage_results
SELECT 'employees_without_salary_history', COUNT(*), 10,
       CASE WHEN COUNT(*) >= 10 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','optional salary history')
FROM employees e
WHERE NOT EXISTS (SELECT 1 FROM salary_history s WHERE s.employee_id = e.employee_id);

INSERT INTO scenario_coverage_results
SELECT 'employees_with_multiple_salary_records', COUNT(*), 20,
       CASE WHEN COUNT(*) >= 20 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','salary history over time')
FROM (
    SELECT employee_id, COUNT(*) n
    FROM salary_history
    GROUP BY employee_id
    HAVING COUNT(*) >= 2
) x;

INSERT INTO scenario_coverage_results
SELECT 'manager_tree_depth_3', COUNT(*), 20,
       CASE WHEN COUNT(*) >= 20 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('scenario','employee -> lead -> department manager')
FROM employees e
JOIN employees m ON m.employee_id = e.manager_id
JOIN employees gm ON gm.employee_id = m.manager_id;

INSERT INTO scenario_coverage_results
SELECT 'order_month_span', COUNT(DISTINCT date_trunc('month', order_date)), 12,
       CASE WHEN COUNT(DISTINCT date_trunc('month', order_date)) >= 12 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_build_object('min_order_date', MIN(order_date), 'max_order_date', MAX(order_date))
FROM orders;

INSERT INTO scenario_coverage_results
SELECT 'inventory_transaction_types', COUNT(DISTINCT transaction_type), 3,
       CASE WHEN COUNT(DISTINCT transaction_type) >= 3 THEN 'PASS' ELSE 'FAIL' END,
       jsonb_object_agg(transaction_type, n)
FROM (SELECT transaction_type, COUNT(*) n FROM inventory_transactions GROUP BY transaction_type) x;

SELECT check_name, status, observed, required, details
FROM scenario_coverage_results
ORDER BY check_name;

SELECT
    CASE WHEN COUNT(*) FILTER (WHERE status = 'FAIL') = 0 THEN 'PASS' ELSE 'FAIL' END AS overall_status,
    COUNT(*) FILTER (WHERE status = 'FAIL') AS failed_checks,
    COUNT(*) AS total_checks
FROM scenario_coverage_results;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM scenario_coverage_results WHERE status = 'FAIL') THEN
        RAISE EXCEPTION 'EnterpriseDB scenario coverage FAILED';
    END IF;
END $$;

SELECT
    CASE
        WHEN COUNT(*) FILTER (WHERE status = 'FAIL') = 0
        THEN 'PASS'
        ELSE 'FAIL'
    END AS overall_status,
    COUNT(*) FILTER (WHERE status = 'FAIL') AS failed_checks,
    COUNT(*) AS total_checks
FROM scenario_coverage_results;

COMMIT;
