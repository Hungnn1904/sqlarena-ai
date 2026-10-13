-- EnterpriseDB / PostgreSQL / 16 Business Rule validators
-- RUN AFTER schema_code.sql + constraint.sql + seed data have completed.
-- Run whole file in ONE session (pgAdmin Query Tool or psql -f).
-- READ ONLY against business tables; temporary results only.
-- Any row in br_validation_violations = failure.
-- Assumptions: post-migration columns salary_history.salary,
-- inventory_transactions.order_item_id, payments.attempted_at (no completed_at).
-- Policy choices requiring confirmation are documented in agent prompt.

BEGIN;
CREATE TEMP TABLE br_validation_violations (
    br_code text NOT NULL,
    check_name text NOT NULL,
    entity_id text,
    details jsonb
) ON COMMIT PRESERVE ROWS;

-- BR01: Order placed after customer registration.
INSERT INTO br_validation_violations
SELECT 'BR01','order_before_registration',o.order_id::text,
       jsonb_build_object('order_date',o.order_date,'registered_at',c.registered_at)
FROM orders o JOIN customers c USING(customer_id)
WHERE o.order_date < c.registered_at;

-- BR02: Each order has at least one line; total includes shipping fee.
INSERT INTO br_validation_violations
SELECT 'BR02','order_total_or_missing_items',o.order_id::text,
       jsonb_build_object('total_amount',o.total_amount,'expected',COALESCE(x.items_total,0)+o.shipping_fee,'item_count',COALESCE(x.item_count,0))
FROM orders o LEFT JOIN (
 SELECT order_id, SUM(line_total) items_total, COUNT(*) item_count
 FROM order_items GROUP BY order_id
) x USING(order_id)
WHERE COALESCE(x.item_count,0)=0 OR o.total_amount IS DISTINCT FROM (COALESCE(x.items_total,0)+o.shipping_fee);

-- BR03: Every order starts at pending, history links continuously,
-- legal transitions only, last status equals orders.status.
WITH h AS (
 SELECT osh.*,
        ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY changed_at,history_id) rn,
        LAG(new_status) OVER(PARTITION BY order_id ORDER BY changed_at,history_id) prev_status,
        LEAD(history_id) OVER(PARTITION BY order_id ORDER BY changed_at,history_id) next_id
 FROM order_status_history osh
)
INSERT INTO br_validation_violations
SELECT 'BR03','invalid_status_history_event',history_id::text,
       jsonb_build_object('order_id',order_id,'old',old_status,'new',new_status,'previous',prev_status,'position',rn)
FROM h WHERE
 (rn=1 AND (old_status IS NOT NULL OR new_status <> 'pending'))
 OR (rn>1 AND old_status IS DISTINCT FROM prev_status)
 OR NOT ( (old_status IS NULL AND new_status='pending')
       OR (old_status='pending' AND new_status IN ('processing','cancelled'))
       OR (old_status='processing' AND new_status IN ('shipped','cancelled'))
       OR (old_status='shipped' AND new_status='delivered') );

WITH last_h AS (
 SELECT order_id,new_status, ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY changed_at DESC,history_id DESC) rn
 FROM order_status_history
)
INSERT INTO br_validation_violations
SELECT 'BR03','missing_or_mismatched_final_status',o.order_id::text,
       jsonb_build_object('order_status',o.status,'last_history_status',h.new_status)
FROM orders o LEFT JOIN last_h h ON h.order_id=o.order_id AND h.rn=1
WHERE h.order_id IS NULL OR o.status IS DISTINCT FROM h.new_status
   OR o.status NOT IN ('pending','processing','shipped','delivered','cancelled');

-- BR04: Order timestamps and event timeline.
INSERT INTO br_validation_violations
SELECT 'BR04','invalid_order_timeline',o.order_id::text,
       jsonb_build_object('created_at',created_at,'order_date',order_date,'shipped_at',shipped_at,'delivered_at',delivered_at,'status',status)
FROM orders o
WHERE created_at > order_date
   OR (shipped_at IS NOT NULL AND shipped_at < order_date)
   OR (delivered_at IS NOT NULL AND (shipped_at IS NULL OR delivered_at < shipped_at))
   OR (status IN ('shipped','delivered') AND shipped_at IS NULL)
   OR (status='delivered' AND delivered_at IS NULL)
   OR (status IN ('pending','processing','cancelled') AND delivered_at IS NOT NULL);

INSERT INTO br_validation_violations
SELECT 'BR04','status_event_before_order',h.history_id::text,
       jsonb_build_object('order_id',h.order_id,'changed_at',h.changed_at,'order_date',o.order_date)
FROM order_status_history h JOIN orders o USING(order_id)
WHERE h.changed_at < o.order_date;

-- BR05: Running stock for each product + warehouse (tie break by transaction_id).
WITH running AS (
 SELECT transaction_id,product_id,warehouse_id,transaction_date,
        SUM(quantity_change) OVER(PARTITION BY product_id,warehouse_id ORDER BY transaction_date,transaction_id ROWS UNBOUNDED PRECEDING) stock_after
 FROM inventory_transactions
)
INSERT INTO br_validation_violations
SELECT 'BR05','negative_running_stock',transaction_id::text,
       jsonb_build_object('product_id',product_id,'warehouse_id',warehouse_id,'stock_after',stock_after)
FROM running WHERE stock_after < 0;

-- BR06: Aggregate warehouse stock at EACH transaction event, not only final.
-- Assumes inventory ordering is (transaction_date,transaction_id).
WITH events AS (
 SELECT t.transaction_id,t.warehouse_id,t.transaction_date,w.capacity,
        SUM(t.quantity_change) OVER(PARTITION BY t.warehouse_id ORDER BY t.transaction_date,t.transaction_id ROWS UNBOUNDED PRECEDING) warehouse_stock
 FROM inventory_transactions t JOIN warehouses w USING(warehouse_id)
)
INSERT INTO br_validation_violations
SELECT 'BR06','warehouse_capacity_exceeded',transaction_id::text,
       jsonb_build_object('warehouse_id',warehouse_id,'warehouse_stock',warehouse_stock,'capacity',capacity)
FROM events WHERE warehouse_stock > capacity;

-- BR07: inventory transaction type / sign / nullable link.
INSERT INTO br_validation_violations
SELECT 'BR07','invalid_transaction_shape',t.transaction_id::text,
       jsonb_build_object('type',transaction_type,'quantity_change',quantity_change,'order_item_id',order_item_id)
FROM inventory_transactions t
WHERE NOT COALESCE(
 (transaction_type='import' AND quantity_change>0 AND order_item_id IS NULL)
 OR (transaction_type='sale' AND quantity_change<0 AND order_item_id IS NOT NULL)
 OR (transaction_type='return' AND quantity_change>0 AND order_item_id IS NOT NULL)
 OR (transaction_type='adjustment' AND quantity_change<>0 AND order_item_id IS NULL),false);

-- Sale/return must match the order line, warehouse, quantity, status.
INSERT INTO br_validation_violations
SELECT 'BR07','sale_return_mismatch',t.transaction_id::text,
       jsonb_build_object('type',t.transaction_type,'order_id',oi.order_id,'order_status',o.status,'product_id',t.product_id,'warehouse_id',t.warehouse_id,'quantity_change',t.quantity_change)
FROM inventory_transactions t
JOIN order_items oi ON oi.order_item_id=t.order_item_id
JOIN orders o ON o.order_id=oi.order_id
WHERE t.transaction_type IN ('sale','return') AND (
      t.product_id<>oi.product_id
   OR t.warehouse_id IS DISTINCT FROM o.warehouse_id
   OR (t.transaction_type='sale' AND (t.quantity_change<>-oi.quantity OR o.status IN ('pending','cancelled')))
   OR (t.transaction_type='return' AND (t.quantity_change<>oi.quantity OR o.status<>'delivered'))
);

-- Shipped/delivered orders require exactly one sale per line;
-- pending/cancelled orders require zero sales.
WITH sales AS (
 SELECT order_item_id,COUNT(*) n FROM inventory_transactions
 WHERE transaction_type='sale' GROUP BY order_item_id
)
INSERT INTO br_validation_violations
SELECT 'BR07','sale_count_by_order_item',oi.order_item_id::text,
       jsonb_build_object('order_id',o.order_id,'status',o.status,'sale_count',COALESCE(s.n,0))
FROM order_items oi JOIN orders o USING(order_id)
LEFT JOIN sales s USING(order_item_id)
WHERE (o.status IN ('shipped','delivered') AND COALESCE(s.n,0)<>1)
   OR (o.status IN ('pending','cancelled') AND COALESCE(s.n,0)<>0)
   OR COALESCE(s.n,0)>1;

-- If any line in a delivered order is physically returned, all must be returned.
WITH r AS (
 SELECT oi.order_id, COUNT(*) FILTER(WHERE t.transaction_id IS NOT NULL) returned_lines,
        COUNT(*) total_lines
 FROM order_items oi LEFT JOIN inventory_transactions t
 ON t.order_item_id=oi.order_item_id AND t.transaction_type='return'
 GROUP BY oi.order_id
)
INSERT INTO br_validation_violations
SELECT 'BR07','partial_physical_return',o.order_id::text,
       jsonb_build_object('returned_lines',r.returned_lines,'total_lines',r.total_lines)
FROM r JOIN orders o USING(order_id)
WHERE r.returned_lines>0 AND r.returned_lines<>r.total_lines;

-- Maximum one sale and one return per order_item.
INSERT INTO br_validation_violations
SELECT 'BR07','duplicate_sale_or_return',order_item_id::text,
       jsonb_build_object('transaction_type',transaction_type,'count',COUNT(*))
FROM inventory_transactions
WHERE transaction_type IN ('sale','return')
GROUP BY order_item_id,transaction_type HAVING COUNT(*)>1;

-- Return must follow a matching earlier sale.
INSERT INTO br_validation_violations
SELECT 'BR07','return_without_matching_prior_sale',r.transaction_id::text,
       jsonb_build_object('order_item_id',r.order_item_id,'return_at',r.transaction_date)
FROM inventory_transactions r
WHERE r.transaction_type='return' AND NOT EXISTS (
 SELECT 1 FROM inventory_transactions s
 WHERE s.transaction_type='sale' AND s.order_item_id=r.order_item_id
 AND s.product_id=r.product_id AND s.warehouse_id=r.warehouse_id
 AND (s.transaction_date,s.transaction_id)<(r.transaction_date,r.transaction_id)
);

-- Orders with sales must identify warehouse.
INSERT INTO br_validation_violations
SELECT 'BR07','missing_warehouse_for_shipment',order_id::text,jsonb_build_object('status',status)
FROM orders WHERE status IN ('shipped','delivered') AND warehouse_id IS NULL;

-- BR08: Inventory cannot predate product creation.
INSERT INTO br_validation_violations
SELECT 'BR08','transaction_before_product',t.transaction_id::text,
       jsonb_build_object('transaction_date',t.transaction_date,'product_created_at',p.created_at)
FROM inventory_transactions t JOIN products p USING(product_id)
WHERE t.transaction_date<p.created_at;

-- BR09: Designated department manager belongs to department.
INSERT INTO br_validation_violations
SELECT 'BR09','department_manager_wrong_department',d.department_id::text,
       jsonb_build_object('manager_employee_id',d.manager_employee_id,'employee_department_id',e.department_id)
FROM departments d JOIN employees e ON e.employee_id=d.manager_employee_id
WHERE e.department_id<>d.department_id;

-- BR10: No employee may appear twice on their own upward manager chain.
WITH RECURSIVE chain AS (
 SELECT employee_id AS origin,employee_id,manager_id,ARRAY[employee_id] AS path,false AS cycle
 FROM employees
 UNION ALL
 SELECT c.origin,m.employee_id,m.manager_id,c.path||m.employee_id,
        m.employee_id=ANY(c.path)
 FROM chain c JOIN employees m ON m.employee_id=c.manager_id
 WHERE NOT c.cycle
)
INSERT INTO br_validation_violations
SELECT 'BR10','management_cycle',origin::text,
       jsonb_build_object('path',path)
FROM chain WHERE cycle;

-- BR11: Salary records must be after hiring; unique date; latest salary=current.
INSERT INTO br_validation_violations
SELECT 'BR11','salary_history_invalid',s.salary_history_id::text,
       jsonb_build_object('employee_id',s.employee_id,'effective_date',s.effective_date,'hire_date',e.hire_date,'salary',s.salary)
FROM salary_history s JOIN employees e USING(employee_id)
WHERE s.effective_date<e.hire_date OR s.salary<=0;

INSERT INTO br_validation_violations
SELECT 'BR11','duplicate_salary_effective_date',employee_id::text,
       jsonb_build_object('effective_date',effective_date,'count',COUNT(*))
FROM salary_history GROUP BY employee_id,effective_date HAVING COUNT(*)>1;

WITH latest AS (
 SELECT employee_id,salary,ROW_NUMBER() OVER(PARTITION BY employee_id ORDER BY effective_date DESC,salary_history_id DESC) rn
 FROM salary_history
)
INSERT INTO br_validation_violations
SELECT 'BR11','latest_salary_not_current',e.employee_id::text,
       jsonb_build_object('current_salary',e.current_salary,'latest_history_salary',l.salary)
FROM employees e JOIN latest l ON l.employee_id=e.employee_id AND l.rn=1
WHERE e.current_salary IS DISTINCT FROM l.salary;

-- BR12: Each payment amount equals order total; success at most once;
-- processing/shipped/delivered exactly one success; pending none.
INSERT INTO br_validation_violations
SELECT 'BR12','invalid_payment_amount_or_status',p.payment_id::text,
       jsonb_build_object('order_id',p.order_id,'amount',p.amount,'order_total',o.total_amount,'status',p.payment_status)
FROM payments p JOIN orders o USING(order_id)
WHERE p.amount<=0 OR p.amount IS DISTINCT FROM o.total_amount
   OR p.payment_status NOT IN ('success','failed');

WITH successes AS (
 SELECT order_id,COUNT(*) success_count,COALESCE(SUM(amount),0) success_amount
 FROM payments WHERE payment_status='success' GROUP BY order_id
)
INSERT INTO br_validation_violations
SELECT 'BR12','invalid_success_count_or_amount',o.order_id::text,
       jsonb_build_object('status',o.status,'success_count',COALESCE(s.success_count,0),'success_amount',COALESCE(s.success_amount,0),'order_total',o.total_amount)
FROM orders o LEFT JOIN successes s USING(order_id)
WHERE COALESCE(s.success_count,0)>1
   OR COALESCE(s.success_amount,0)>o.total_amount
   OR (o.status IN ('processing','shipped','delivered') AND COALESCE(s.success_count,0)<>1)
   OR (o.status='pending' AND COALESCE(s.success_count,0)<>0);

-- BR13: Every refund references successful payment.
INSERT INTO br_validation_violations
SELECT 'BR13','refund_for_non_success_payment',r.refund_id::text,
       jsonb_build_object('payment_id',p.payment_id,'payment_status',p.payment_status)
FROM refunds r JOIN payments p USING(payment_id)
WHERE p.payment_status<>'success';

-- BR14: Only completed refunds count toward total.
INSERT INTO br_validation_violations
SELECT 'BR14','completed_refunds_exceed_payment',p.payment_id::text,
       jsonb_build_object('completed_refund_sum',x.refund_sum,'payment_amount',p.amount)
FROM payments p JOIN (
 SELECT payment_id,SUM(refund_amount) refund_sum FROM refunds
 WHERE refund_status='completed' GROUP BY payment_id
) x USING(payment_id)
WHERE x.refund_sum>p.amount;

-- BR15: Payment attempted after order, refund requested after success attempt,
-- completed refund not earlier than requested.
INSERT INTO br_validation_violations
SELECT 'BR15','payment_before_order',p.payment_id::text,
       jsonb_build_object('attempted_at',p.attempted_at,'order_date',o.order_date)
FROM payments p JOIN orders o USING(order_id)
WHERE p.attempted_at<o.order_date;

INSERT INTO br_validation_violations
SELECT 'BR15','invalid_refund_timeline',r.refund_id::text,
       jsonb_build_object('requested_at',r.requested_at,'payment_attempted_at',p.attempted_at,'completed_at',r.completed_at)
FROM refunds r JOIN payments p USING(payment_id)
WHERE r.requested_at<p.attempted_at
   OR (r.completed_at IS NOT NULL AND r.completed_at<r.requested_at);

-- BR16: Expense date after hire date of approver, when present.
INSERT INTO br_validation_violations
SELECT 'BR16','expense_before_approver_hire',x.expense_id::text,
       jsonb_build_object('expense_date',x.expense_date,'hire_date',e.hire_date,'approver',e.employee_id)
FROM operating_expenses x JOIN employees e ON e.employee_id=x.approved_by_employee_id
WHERE x.expense_date<e.hire_date;

-- ===== RESULTS: DETAIL / SUMMARY / OVERALL =====
SELECT br_code,check_name,entity_id,details
FROM br_validation_violations
ORDER BY br_code,check_name,entity_id;

WITH rules AS (SELECT 'BR'||LPAD(n::text,2,'0') br_code FROM generate_series(1,16) n)
SELECT r.br_code,CASE WHEN COUNT(v.br_code)=0 THEN 'PASS' ELSE 'FAIL' END status,
       COUNT(v.br_code) violation_count
FROM rules r LEFT JOIN br_validation_violations v USING(br_code)
GROUP BY r.br_code ORDER BY r.br_code;

SELECT CASE WHEN COUNT(*)=0 THEN 'PASS' ELSE 'FAIL' END overall_status,
       COUNT(*) total_violations
FROM br_validation_violations;

-- OPTIONAL for automation: uncomment to make psql / agent see an SQL exception
-- on failed validation. Keep the above result queries for diagnostics.
-- DO $$ BEGIN
--   IF EXISTS (SELECT 1 FROM br_validation_violations) THEN
--      RAISE EXCEPTION 'EnterpriseDB BR validation FAILED';
--   END IF;
-- END $$;

COMMIT;


SELECT
    t.transaction_id,
    o.order_id,
    o.delivered_at,
    t.transaction_date AS return_date
FROM inventory_transactions t
JOIN order_items oi
    ON oi.order_item_id = t.order_item_id
JOIN orders o
    ON o.order_id = oi.order_id
WHERE t.transaction_type = 'return'
  AND (
      o.delivered_at IS NULL
      OR t.transaction_date < o.delivered_at
  );

 SELECT
    o.order_id,
    o.status,
    o.shipped_at,
    o.delivered_at,
    h.new_status,
    h.changed_at
FROM orders o
JOIN order_status_history h
    ON h.order_id = o.order_id
WHERE
    (h.new_status = 'shipped'
     AND h.changed_at IS DISTINCT FROM o.shipped_at)
 OR (h.new_status = 'delivered'
     AND h.changed_at IS DISTINCT FROM o.delivered_at);