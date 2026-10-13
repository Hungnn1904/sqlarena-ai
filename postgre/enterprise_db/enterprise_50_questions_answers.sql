-- ENT-001: Khách hàng hoạt động đăng ký trước năm 2025
-- Liệt kê khách hàng status='active' và registered_at < 2025-01-01.
-- Sắp xếp: registered_at tăng, customer_id tăng.
SELECT customer_id, full_name, email, registered_at
FROM customers WHERE status='active' AND registered_at < TIMESTAMP '2025-01-01'
ORDER BY registered_at, customer_id;

-- ENT-002: Các thành phố có địa chỉ khách hàng
-- Liệt kê các city khác nhau xuất hiện trong địa chỉ khách hàng.
-- Sắp xếp: city tăng.
SELECT DISTINCT city FROM customer_addresses ORDER BY city;

-- ENT-003: Hàng đợi đơn chờ xử lý
-- Liệt kê tất cả đơn status='pending', gồm người mua, kho được gán và giá trị đơn.
-- Sắp xếp: order_date tăng, order_id tăng.
SELECT order_id, customer_id, warehouse_id, order_date, total_amount
FROM orders WHERE status='pending' ORDER BY order_date, order_id;

-- ENT-004: Đơn đã giao đặt trong năm 2026
-- Liệt kê đơn status='delivered' có order_date từ 2026-01-01 đến trước 2027-01-01, kèm mốc gửi và giao.
-- Sắp xếp: order_date tăng, order_id tăng.
SELECT order_id, order_date, shipped_at, delivered_at, carrier_name FROM orders
WHERE status='delivered' AND order_date >= TIMESTAMP '2026-01-01'
  AND order_date < TIMESTAMP '2027-01-01' ORDER BY order_date, order_id;

-- ENT-005: Sản phẩm đang bán có giá niêm yết cao
-- Liệt kê sản phẩm is_active=true có list_price >= 1000000.
-- Sắp xếp: list_price giảm, product_id tăng.
SELECT product_id, product_name, sku, list_price, cost_price FROM products
WHERE is_active AND list_price >= 1000000 ORDER BY list_price DESC, product_id;

-- ENT-006: Nhân viên không có quản lý trực tiếp
-- Liệt kê nhân viên có manager_id IS NULL, không giới hạn status.
-- Sắp xếp: employee_id tăng.
SELECT employee_id, full_name, department_id, job_title FROM employees
WHERE manager_id IS NULL ORDER BY employee_id;

-- ENT-007: Yêu cầu hoàn tiền còn chờ
-- Liệt kê yêu cầu refund_status='pending' và completed_at IS NULL, theo thứ tự tiếp nhận.
-- Sắp xếp: requested_at tăng, refund_id tăng.
SELECT refund_id, payment_id, refund_amount, requested_at FROM refunds
WHERE refund_status='pending' AND completed_at IS NULL ORDER BY requested_at, refund_id;

-- ENT-008: Quốc gia trong mạng lưới nhà cung cấp
-- Liệt kê country khác nhau, loại NULL, của toàn bộ nhà cung cấp không giới hạn status.
-- Sắp xếp: country tăng.
SELECT DISTINCT country FROM suppliers WHERE country IS NOT NULL ORDER BY country;

-- ENT-009: Danh bạ địa chỉ mặc định
-- Với mọi khách hàng, nối các địa chỉ is_default=true. Nếu không có thì vẫn giữ khách với các cột địa
-- chỉ NULL.
-- Sắp xếp: customer_id tăng, address_id tăng NULLS LAST.
SELECT c.customer_id, c.full_name, a.address_id, a.city, a.address_line
FROM customers c LEFT JOIN customer_addresses a ON a.customer_id=c.customer_id AND a.is_default
ORDER BY c.customer_id, a.address_id NULLS LAST;

-- ENT-010: Tên sản phẩm trên từng dòng hàng
-- Liệt kê mọi dòng order_items cùng tên sản phẩm, số lượng và line_total; không lọc trạng thái đơn.
-- Sắp xếp: order_item_id tăng.
SELECT i.order_item_id, i.order_id, p.product_name, i.quantity, i.line_total
FROM order_items i JOIN products p ON p.product_id=i.product_id ORDER BY i.order_item_id;

-- ENT-011: Danh mục trực tiếp của sản phẩm
-- Liệt kê sản phẩm với tên danh mục trực tiếp và trạng thái is_active của danh mục, không duyệt cha.
-- Sắp xếp: product_id tăng.
SELECT p.product_id, p.product_name, c.category_name, c.is_active AS category_active
FROM products p JOIN categories c ON c.category_id=p.category_id ORDER BY p.product_id;

-- ENT-012: Liên hệ nguồn cung cho sản phẩm
-- Liệt kê sản phẩm, nhà cung cấp, quốc gia và email liên hệ; giữ email hoặc quốc gia NULL.
-- Sắp xếp: product_id tăng.
SELECT p.product_id, p.sku, s.supplier_name, s.country, s.contact_email
FROM products p JOIN suppliers s ON s.supplier_id=p.supplier_id ORDER BY p.product_id;

-- ENT-013: Danh bạ nhân viên và quản lý trực tiếp
-- Liệt kê mọi nhân viên cùng ID và tên quản lý trực tiếp; nhân viên gốc vẫn xuất hiện.
-- Sắp xếp: employee_id tăng.
SELECT e.employee_id, e.full_name AS employee_name, e.manager_id, m.full_name AS manager_name
FROM employees e LEFT JOIN employees m ON m.employee_id=e.manager_id ORDER BY e.employee_id;

-- ENT-014: Trưởng phòng được chỉ định
-- Liệt kê tất cả phòng ban và nhân viên được manager_employee_id chỉ định, không suy từ manager_id.
-- Sắp xếp: department_id tăng.
SELECT d.department_id, d.department_name, d.manager_employee_id, e.full_name AS manager_name
FROM departments d LEFT JOIN employees e ON e.employee_id=d.manager_employee_id ORDER BY d.department_id;

-- ENT-015: Người phê duyệt từng khoản chi
-- Liệt kê mọi khoản operating_expenses và tên người phê duyệt; khoản chưa có người phê duyệt vẫn xuất
-- hiện.
-- Sắp xếp: expense_id tăng.
SELECT x.expense_id, x.expense_category, x.amount, x.expense_date, e.full_name AS approver_name
FROM operating_expenses x LEFT JOIN employees e ON e.employee_id=x.approved_by_employee_id ORDER BY x.expense_id;

-- ENT-016: Quy mô khách hàng theo trạng thái
-- Đếm khách hàng theo status; mỗi khách chỉ đếm một lần.
-- Sắp xếp: status tăng.
SELECT status, COUNT(*) AS customer_count FROM customers GROUP BY status ORDER BY status;

-- ENT-017: Giá trị đơn hàng theo trạng thái
-- Theo status của đơn, tính số đơn và tổng total_amount. Đây là giá trị đơn gồm phí giao hàng, không
-- phải tiền đã thu.
-- Sắp xếp: status tăng.
SELECT status, COUNT(*) AS order_count, SUM(total_amount) AS order_value
FROM orders GROUP BY status ORDER BY status;

-- ENT-018: Tổng biến động theo loại giao dịch kho
-- Theo transaction_type, tính số giao dịch và tổng quantity_change có dấu, trên toàn bộ kho và thời
-- gian.
-- Sắp xếp: transaction_type tăng.
SELECT transaction_type, COUNT(*) AS transaction_count, SUM(quantity_change) AS net_units
FROM inventory_transactions GROUP BY transaction_type ORDER BY transaction_type;

-- ENT-019: Quỹ lương hiện tại theo mã phòng
-- Theo department_id của nhân viên, tính số nhân viên và tổng current_salary, không lọc status.
-- Sắp xếp: department_id tăng.
SELECT department_id, COUNT(*) AS employee_count, SUM(current_salary) AS current_payroll
FROM employees GROUP BY department_id ORDER BY department_id;

-- ENT-020: Thời gian xử lý hoàn tiền đã hoàn tất
-- Trong refund_status='completed' có completed_at không NULL, tính số yêu cầu và thời gian xử lý ngắn
-- nhất, dài nhất, trung bình bằng giờ từ requested_at đến completed_at. Làm tròn các số giờ 2 chữ số.
-- Sắp xếp: Một dòng nên không có yêu cầu thứ tự.
SELECT COUNT(*) AS completed_refunds,
 ROUND(MIN(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS min_hours,
 ROUND(MAX(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS max_hours,
 ROUND(AVG(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS avg_hours
FROM refunds WHERE refund_status='completed' AND completed_at IS NOT NULL;

-- ENT-021: Đơn giao đến thành phố khác địa chỉ mặc định
-- Liệt kê đơn có city của địa chỉ giao khác city của một địa chỉ mặc định hiện có của khách. Chỉ so với
-- địa chỉ mặc định được lưu hiện tại, không suy lịch sử thay đổi địa chỉ.
-- Sắp xếp: order_id tăng, default_address_id tăng.
SELECT o.order_id, o.customer_id, a.city AS shipping_city,
       d.address_id AS default_address_id, d.city AS default_city
FROM orders o JOIN customer_addresses a
  ON a.address_id=o.shipping_address_id AND a.customer_id=o.customer_id
JOIN customer_addresses d ON d.customer_id=o.customer_id AND d.is_default
WHERE a.city<>d.city ORDER BY o.order_id, d.address_id;

-- ENT-022: Tiến độ xuất từng dòng đơn đang xử lý
-- Liệt kê từng dòng của đơn status='processing', kho của đơn và tên kho nếu có; nối giao dịch sale bằng
-- order_item_id để cho biết đã xuất hay chưa và thời điểm xuất.
-- Sắp xếp: order_id tăng, order_item_id tăng.
SELECT o.order_id, i.order_item_id, i.product_id, i.quantity, o.warehouse_id,
       w.warehouse_name, t.transaction_id IS NOT NULL AS has_sale, t.transaction_date AS sale_at
FROM orders o JOIN order_items i ON i.order_id=o.order_id
LEFT JOIN warehouses w ON w.warehouse_id=o.warehouse_id
LEFT JOIN inventory_transactions t ON t.order_item_id=i.order_item_id AND t.transaction_type='sale'
WHERE o.status='processing' ORDER BY o.order_id, i.order_item_id;

-- ENT-023: Đối chiếu vai trò quản lý kho và trưởng phòng
-- Với mỗi kho, tìm người quản lý kho, phòng của người đó và trưởng phòng được chỉ định. Cho biết người
-- quản lý kho có đồng thời là trưởng phòng đó hay không.
-- Sắp xếp: warehouse_id tăng.
SELECT w.warehouse_id, e.employee_id AS warehouse_manager_id,
       e.full_name AS warehouse_manager_name, d.department_name,
       d.manager_employee_id AS department_manager_id,
       e.employee_id=d.manager_employee_id AS same_person
FROM warehouses w LEFT JOIN employees e ON e.employee_id=w.manager_employee_id
LEFT JOIN departments d ON d.department_id=e.department_id ORDER BY w.warehouse_id;

-- ENT-024: Nhân viên xử lý ít nhất năm đơn đã giao
-- Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, số đơn delivered và tổng total_amount
-- chỉ của đơn delivered. Giữ người có ít nhất 5 đơn delivered.
-- Sắp xếp: employee_id tăng.
SELECT employee_id, COUNT(*) AS assigned_orders,
       COUNT(*) FILTER (WHERE status='delivered') AS delivered_orders,
       SUM(total_amount) FILTER (WHERE status='delivered') AS delivered_order_value
FROM orders WHERE employee_id IS NOT NULL GROUP BY employee_id
HAVING COUNT(*) FILTER (WHERE status='delivered')>=5 ORDER BY employee_id;

-- ENT-025: Nhà cung cấp có danh mục hàng hoạt động đa dạng
-- Trong sản phẩm is_active=true, theo supplier_id tính số sản phẩm, số category_id khác nhau và trung
-- bình list_price-cost_price. Chỉ giữ nhóm có ít nhất 5 sản phẩm và 3 danh mục.
-- Sắp xếp: supplier_id tăng.
SELECT supplier_id, COUNT(*) AS active_products, COUNT(DISTINCT category_id) AS category_count,
       ROUND(AVG(list_price-cost_price),2) AS avg_unit_margin
FROM products WHERE is_active GROUP BY supplier_id
HAVING COUNT(*)>=5 AND COUNT(DISTINCT category_id)>=3 ORDER BY supplier_id;

-- ENT-026: Khách có địa chỉ tại nhiều thành phố
-- Theo customer_id trong customer_addresses, đếm địa chỉ, số city khác nhau và số địa chỉ mặc định. Chỉ
-- giữ khách có ít nhất 2 city.
-- Sắp xếp: customer_id tăng.
SELECT customer_id, COUNT(*) AS address_count, COUNT(DISTINCT city) AS city_count,
       COUNT(*) FILTER (WHERE is_default) AS default_count
FROM customer_addresses GROUP BY customer_id HAVING COUNT(DISTINCT city)>=2 ORDER BY customer_id;

-- ENT-027: Chi phí tháng theo phòng và tình trạng phê duyệt
-- Theo tháng expense_date và department_id, tính số khoản chi, tổng amount và tổng amount có
-- approved_by_employee_id không NULL. Chỉ giữ nhóm có ít nhất 2 khoản.
-- Sắp xếp: month tăng, department_id tăng NULLS LAST.
SELECT DATE_TRUNC('month',expense_date)::date AS month, department_id,
       COUNT(*) AS expense_count, SUM(amount) AS total_expense,
       COALESCE(SUM(amount) FILTER (WHERE approved_by_employee_id IS NOT NULL),0) AS approved_expense
FROM operating_expenses GROUP BY DATE_TRUNC('month',expense_date)::date, department_id
HAVING COUNT(*)>=2 ORDER BY month, department_id NULLS LAST;

-- ENT-028: Sức chứa còn lại của từng kho
-- Với mọi kho, tính tồn hiện tại từ tổng quantity_change của mọi sản phẩm, sức chứa còn lại và phần trăm
-- sử dụng capacity. Bao gồm kho không có giao dịch.
-- Sắp xếp: warehouse_id tăng.
SELECT w.warehouse_id, w.capacity, COALESCE(SUM(t.quantity_change),0) AS current_units,
       w.capacity-COALESCE(SUM(t.quantity_change),0) AS free_capacity,
       ROUND(100.0*COALESCE(SUM(t.quantity_change),0)/NULLIF(w.capacity,0),2) AS utilization_pct
FROM warehouses w LEFT JOIN inventory_transactions t ON t.warehouse_id=w.warehouse_id
GROUP BY w.warehouse_id, w.capacity ORDER BY w.warehouse_id;

-- ENT-029: Khách hàng chưa từng đặt đơn
-- Tìm khách hàng không có bất kỳ bản ghi orders nào, không giới hạn status của khách hoặc đơn.
-- Sắp xếp: customer_id tăng.
SELECT c.customer_id, c.full_name, c.registered_at FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id) ORDER BY c.customer_id;

-- ENT-030: Hàng chưa được đặt nhưng vẫn có tồn
-- Tìm sản phẩm không xuất hiện trong bất kỳ order_items nào nhưng có ít nhất một kho với
-- SUM(quantity_change)>0.
-- Sắp xếp: product_id tăng.
SELECT p.product_id, p.product_name FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.product_id=p.product_id)
  AND EXISTS (SELECT 1 FROM inventory_transactions t WHERE t.product_id=p.product_id
              GROUP BY t.warehouse_id HAVING SUM(t.quantity_change)>0) ORDER BY p.product_id;

-- ENT-031: Lương cao hơn trung bình phòng
-- Tìm nhân viên có current_salary cao hơn trung bình current_salary của mọi nhân viên cùng
-- department_id, gồm cả bản thân và không lọc status.
-- Sắp xếp: employee_id tăng.
SELECT e.employee_id, e.department_id, e.current_salary FROM employees e
WHERE e.current_salary>(SELECT AVG(p.current_salary) FROM employees p WHERE p.department_id=e.department_id)
ORDER BY e.employee_id;

-- ENT-032: Đơn thanh toán thành công sau lần thất bại
-- Liệt kê mỗi payment success có ít nhất một payment failed của cùng đơn xảy ra trước, theo cặp
-- (attempted_at,payment_id).
-- Sắp xếp: order_id tăng.
SELECT s.order_id, s.payment_id AS success_payment_id, s.attempted_at AS success_at FROM payments s
WHERE s.payment_status='success' AND EXISTS (
  SELECT 1 FROM payments f WHERE f.order_id=s.order_id AND f.payment_status='failed'
  AND (f.attempted_at,f.payment_id)<(s.attempted_at,s.payment_id)) ORDER BY s.order_id;

-- ENT-033: Nhà cung cấp hoạt động không có hàng ngừng bán
-- Tìm supplier status='active' có ít nhất một sản phẩm và không có sản phẩm is_active=false.
-- Sắp xếp: supplier_id tăng.
SELECT s.supplier_id, s.supplier_name FROM suppliers s
WHERE s.status='active' AND EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id)
AND NOT EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id AND NOT p.is_active)
ORDER BY s.supplier_id;

-- ENT-034: Đơn trả hàng vật lý chưa có hoàn tiền hoàn tất
-- Tìm đơn delivered có giao dịch return liên kết ít nhất một dòng hàng, nhưng không có refund completed
-- qua bất kỳ payment của đơn. Đây là danh sách đối soát, không kết luận vi phạm BR.
-- Sắp xếp: order_id tăng.
SELECT o.order_id, o.customer_id, o.total_amount FROM orders o WHERE o.status='delivered'
AND EXISTS (SELECT 1 FROM order_items i JOIN inventory_transactions t ON t.order_item_id=i.order_item_id
            WHERE i.order_id=o.order_id AND t.transaction_type='return')
AND NOT EXISTS (SELECT 1 FROM payments p JOIN refunds r ON r.payment_id=p.payment_id
                WHERE p.order_id=o.order_id AND r.refund_status='completed') ORDER BY o.order_id;

-- ENT-035: Hai đơn giá trị lớn nhất tại mỗi kho
-- Trong mọi đơn có warehouse_id không NULL, lấy tối đa 2 đơn mỗi kho theo total_amount giảm, order_date
-- tăng, order_id tăng; không giới hạn trạng thái.
-- Sắp xếp: warehouse_id tăng, position tăng.
WITH ranked AS (
 SELECT warehouse_id, ROW_NUMBER() OVER (PARTITION BY warehouse_id
        ORDER BY total_amount DESC,order_date,order_id) AS position, order_id,total_amount,order_date
 FROM orders WHERE warehouse_id IS NOT NULL)
SELECT warehouse_id,position,order_id,total_amount,order_date FROM ranked WHERE position<=2
ORDER BY warehouse_id,position;

-- ENT-036: Ba mức giá cao nhất trong từng danh mục
-- Trong toàn bộ sản phẩm, lấy sản phẩm thuộc 3 mức list_price cao nhất khác nhau mỗi category_id. Các
-- sản phẩm đồng giá có cùng hạng và đều được giữ.
-- Sắp xếp: category_id tăng, price_rank tăng, product_id tăng.
WITH ranked AS (
 SELECT category_id,DENSE_RANK() OVER (PARTITION BY category_id ORDER BY list_price DESC) AS price_rank,
        product_id,list_price FROM products)
SELECT category_id,price_rank,product_id,list_price FROM ranked WHERE price_rank<=3
ORDER BY category_id,price_rank,product_id;

-- ENT-037: Biến động lương giữa hai mốc liên tiếp
-- Với mỗi bản ghi salary_history ngoài bản ghi đầu của nhân viên, trả mức lương trước, mới và phần trăm
-- thay đổi. Thứ tự lịch sử là effective_date, salary_history_id.
-- Sắp xếp: employee_id tăng, effective_date tăng.
WITH previous AS (
 SELECT employee_id,effective_date,salary,
 LAG(salary) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_salary
 FROM salary_history)
SELECT employee_id,effective_date,previous_salary,salary,
       ROUND(100.0*(salary-previous_salary)/previous_salary,2) AS change_pct
FROM previous WHERE previous_salary IS NOT NULL ORDER BY employee_id,effective_date;

-- ENT-038: Biến động giá trị đơn đã giao theo tháng đặt
-- Nhóm đơn status='delivered' theo tháng order_date, tính tổng total_amount và phần trăm thay đổi so với
-- tháng có dữ liệu ngay trước trong kết quả.
-- Sắp xếp: month tăng.
WITH monthly AS (
 SELECT DATE_TRUNC('month',order_date)::date AS month,SUM(total_amount) AS order_value
 FROM orders WHERE status='delivered' GROUP BY 1), compared AS (
 SELECT month,order_value,LAG(order_value) OVER (ORDER BY month) AS previous_value FROM monthly)
SELECT month,order_value,previous_value,
       ROUND(100.0*(order_value-previous_value)/NULLIF(previous_value,0),2) AS change_pct
FROM compared ORDER BY month;

-- ENT-039: Tiền thu thành công lũy kế theo tháng
-- Nhóm payments payment_status='success' theo tháng attempted_at; trả tiền thu tháng và tổng tiền thu
-- lũy kế từ tháng đầu. Không trừ refunds.
-- Sắp xếp: month tăng.
WITH monthly AS (
 SELECT DATE_TRUNC('month',attempted_at)::date AS month,SUM(amount) AS collected_amount
 FROM payments WHERE payment_status='success' GROUP BY 1)
SELECT month,collected_amount,SUM(collected_amount) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS cumulative_collected
FROM monthly ORDER BY month;

-- ENT-040: Khoảng cách giữa các lần đặt của khách
-- Với mỗi đơn ngoài đơn đầu của khách, trả order_id trước đó và số ngày giữa hai order_date liên tiếp.
-- Bao gồm mọi trạng thái; thứ tự order_date,order_id.
-- Sắp xếp: customer_id tăng, order_date tăng, order_id tăng.
WITH previous AS (
 SELECT customer_id,order_id,order_date,
 LAG(order_id) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_order_id,
 LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_date FROM orders)
SELECT customer_id,order_id,previous_order_id,
       ROUND(EXTRACT(EPOCH FROM order_date-previous_date)/86400,2) AS gap_days
FROM previous WHERE previous_order_id IS NOT NULL ORDER BY customer_id,order_date,order_id;

-- ENT-041: Nguồn cung phủ đầy đủ hàng bán và kho có tồn
-- Tìm nhà cung cấp có ít nhất 2 sản phẩm đang hoạt động. Mỗi sản phẩm đang hoạt động phải có ít nhất một
-- dòng thuộc đơn delivered; tại mọi kho từng có đơn delivered chứa sản phẩm đó, tổng quantity_change của
-- chính sản phẩm tại kho đó phải >0. Sản phẩm không hoạt động không tham gia điều kiện.
-- Sắp xếp: supplier_id tăng.
SELECT s.supplier_id,s.supplier_name FROM suppliers s
WHERE (SELECT COUNT(*) FROM products p WHERE p.supplier_id=s.supplier_id AND p.is_active)>=2
AND NOT EXISTS (
 SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id AND p.is_active AND (
  NOT EXISTS (SELECT 1 FROM order_items i JOIN orders o ON o.order_id=i.order_id
              WHERE i.product_id=p.product_id AND o.status='delivered')
  OR EXISTS (
   SELECT 1 FROM order_items i JOIN orders o ON o.order_id=i.order_id
   WHERE i.product_id=p.product_id AND o.status='delivered' AND NOT EXISTS (
    SELECT 1 FROM inventory_transactions t WHERE t.product_id=p.product_id AND t.warehouse_id=o.warehouse_id
    GROUP BY t.product_id,t.warehouse_id HAVING SUM(t.quantity_change)>0))))
ORDER BY s.supplier_id;

-- ENT-042: Chuỗi thắng tháng dài nhất của nhân viên
-- Trong đơn delivered có employee_id không NULL, tính giá trị total_amount theo nhân viên và tháng
-- order_date. Mỗi tháng chọn đúng một người thắng theo tổng giảm rồi employee_id tăng. Với mỗi người
-- từng thắng, trả chuỗi thắng ở các tháng lịch liên tiếp dài nhất; nếu hòa chọn chuỗi bắt đầu sớm hơn.
-- Sắp xếp: employee_id tăng.
WITH totals AS (
 SELECT DATE_TRUNC('month',order_date)::date AS month,employee_id,SUM(total_amount) AS value
 FROM orders WHERE status='delivered' AND employee_id IS NOT NULL GROUP BY 1,2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY month ORDER BY value DESC,employee_id) AS pos FROM totals), wins AS (
 SELECT employee_id,month,
 (EXTRACT(YEAR FROM month)::int*12+EXTRACT(MONTH FROM month)::int)
 -ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY month) AS island
 FROM ranked WHERE pos=1), streaks AS (
 SELECT employee_id,MIN(month) AS start_month,MAX(month) AS end_month,COUNT(*) AS streak_months
 FROM wins GROUP BY employee_id,island), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY streak_months DESC,start_month) AS pos FROM streaks)
SELECT employee_id,start_month,end_month,streak_months FROM picked WHERE pos=1 ORDER BY employee_id;

-- ENT-043: Ba cửa sổ ba tháng có tiền ròng lớn nhất
-- Gộp tiền vào từ payment success theo attempted_at và tiền ra từ refund completed theo completed_at.
-- Tạo đủ các tháng từ tháng sự kiện sớm nhất đến muộn nhất; tháng trống bằng 0. Tính tiền ròng trong cửa
-- sổ 3 tháng lịch kết thúc mỗi tháng, chỉ giữ cửa sổ đủ 3 tháng. Chọn tối đa 3 cửa sổ có tổng ròng lớn
-- nhất, hòa chọn tháng kết thúc sớm hơn.
-- Sắp xếp: net_three_months giảm, end_month tăng.
WITH events AS (
 SELECT DATE_TRUNC('month',attempted_at)::date AS month,amount AS delta FROM payments WHERE payment_status='success'
 UNION ALL
 SELECT DATE_TRUNC('month',completed_at)::date,-refund_amount FROM refunds WHERE refund_status='completed'),
calendar AS (
 SELECT GENERATE_SERIES(MIN(month)::timestamp,MAX(month)::timestamp,INTERVAL '1 month')::date AS month FROM events),
monthly AS (
 SELECT c.month,COALESCE(SUM(e.delta),0) AS net FROM calendar c LEFT JOIN events e USING(month) GROUP BY c.month),
rolling AS (
 SELECT month,SUM(net) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS net_three_months,
 COUNT(*) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS months_in_window FROM monthly)
SELECT (month-INTERVAL '2 months')::date AS start_month,month AS end_month,net_three_months
FROM rolling WHERE months_in_window=3 ORDER BY net_three_months DESC,month LIMIT 3;

-- ENT-044: Nhóm loại chi nhỏ nhất đạt 80 phần trăm chi phòng
-- Trong chi có expense_date thuộc năm 2025, tổng hợp amount theo phòng và expense_category. Xếp loại chi
-- theo tổng giảm, tên loại tăng; với mỗi phòng, giữ tiền tố ngắn nhất mà tổng tích lũy đạt ít nhất 80%
-- tổng chi phòng. Trả từng loại trong tiền tố, vị trí, tiền loại và phần trăm tích lũy.
-- Sắp xếp: department_id tăng NULLS LAST, position tăng.
WITH categories AS (
 SELECT department_id,expense_category,SUM(amount) AS category_amount FROM operating_expenses
 WHERE expense_date>=DATE '2025-01-01' AND expense_date<DATE '2026-01-01' GROUP BY 1,2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category) AS position,
 SUM(category_amount) OVER (PARTITION BY department_id) AS total,
 SUM(category_amount) OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category
 ROWS UNBOUNDED PRECEDING) AS cumulative FROM categories)
SELECT department_id,position,expense_category,category_amount,ROUND(100.0*cumulative/total,2) AS cumulative_pct
FROM ranked WHERE cumulative-category_amount<0.8*total ORDER BY department_id NULLS LAST,position;

-- ENT-045: Nhân viên dẫn đầu quý và sản phẩm đóng góp lớn nhất
-- Trong đơn delivered được gán nhân viên, tổng line_total theo quý order_date, nhân viên và sản phẩm;
-- chọn sản phẩm có tổng lớn nhất mỗi nhân viên-quý (hòa chọn product_id nhỏ). Tính tổng line_total của
-- nhân viên-quý rồi lấy tối đa 3 nhân viên mỗi quý theo tổng giảm, employee_id tăng. Trả sản phẩm dẫn
-- đầu và tỷ trọng đóng góp của nó. Đây là giá trị hàng theo dòng, không gồm shipping_fee, không trừ
-- refund hoặc trả hàng vật lý, không phải tiền ròng.
-- Sắp xếp: quarter tăng, employee_rank tăng.
WITH products AS (
 SELECT DATE_TRUNC('quarter',o.order_date)::date AS quarter,o.employee_id,i.product_id,SUM(i.line_total) AS product_value
 FROM orders o JOIN order_items i ON i.order_id=o.order_id
 WHERE o.status='delivered' AND o.employee_id IS NOT NULL GROUP BY 1,2,3), product_ranks AS (
 SELECT *,SUM(product_value) OVER (PARTITION BY quarter,employee_id) AS merchandise_value,
 ROW_NUMBER() OVER (PARTITION BY quarter,employee_id ORDER BY product_value DESC,product_id) AS product_pos FROM products),
leaders AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY quarter ORDER BY merchandise_value DESC,employee_id) AS employee_rank
 FROM product_ranks WHERE product_pos=1)
SELECT quarter,employee_rank,employee_id,merchandise_value,product_id AS top_product_id,
       product_value AS top_product_value,ROUND(100.0*product_value/NULLIF(merchandise_value,0),2) AS top_share_pct
FROM leaders WHERE employee_rank<=3 ORDER BY quarter,employee_rank;

-- ENT-046: Chuỗi giảm tồn liên tiếp dưới ngưỡng 50 đơn vị
-- Xét tháng 2025-03 đến 2026-09 cho mỗi cặp sản phẩm-kho có giao dịch. Tồn cuối tháng là tổng mọi
-- quantity_change trước đầu tháng tiếp theo, kể cả giao dịch trước kỳ. Tháng đủ điều kiện khi tồn cuối <
-- tồn đầu và tồn cuối <=50 đơn vị. Với mỗi cặp có tháng đủ điều kiện, tìm chuỗi tháng lịch đủ điều kiện
-- liên tục dài nhất; hòa chọn chuỗi bắt đầu sớm hơn. Trả đầu/cuối chuỗi, số tháng và tổng số đơn vị
-- giảm. Ngưỡng 50 là tham số phân tích, không phải Business Rule.
-- Sắp xếp: product_id tăng, warehouse_id tăng.
WITH pairs AS (
 SELECT DISTINCT product_id,warehouse_id FROM inventory_transactions), calendar AS (
 SELECT GENERATE_SERIES(TIMESTAMP '2025-03-01',TIMESTAMP '2026-09-01',INTERVAL '1 month')::date AS month),
opening AS (
 SELECT product_id,warehouse_id,SUM(quantity_change) AS opening_stock FROM inventory_transactions
 WHERE transaction_date<TIMESTAMP '2025-03-01' GROUP BY 1,2), movements AS (
 SELECT product_id,warehouse_id,DATE_TRUNC('month',transaction_date)::date AS month,SUM(quantity_change) AS delta
 FROM inventory_transactions WHERE transaction_date>=TIMESTAMP '2025-03-01' AND transaction_date<TIMESTAMP '2026-10-01'
 GROUP BY 1,2,3), monthly AS (
 SELECT p.product_id,p.warehouse_id,c.month,COALESCE(m.delta,0) AS delta,
 COALESCE(o.opening_stock,0)+SUM(COALESCE(m.delta,0)) OVER (
 PARTITION BY p.product_id,p.warehouse_id ORDER BY c.month ROWS UNBOUNDED PRECEDING) AS closing_stock
 FROM pairs p CROSS JOIN calendar c LEFT JOIN movements m
 ON m.product_id=p.product_id AND m.warehouse_id=p.warehouse_id AND m.month=c.month
 LEFT JOIN opening o ON o.product_id=p.product_id AND o.warehouse_id=p.warehouse_id), eligible AS (
 SELECT *,EXTRACT(YEAR FROM month)::int*12+EXTRACT(MONTH FROM month)::int
 -ROW_NUMBER() OVER (PARTITION BY product_id,warehouse_id ORDER BY month) AS island
 FROM monthly WHERE delta<0 AND closing_stock<=50), streaks AS (
 SELECT product_id,warehouse_id,MIN(month) AS start_month,MAX(month) AS end_month,
 COUNT(*) AS streak_months,-SUM(delta) AS depleted_units FROM eligible GROUP BY product_id,warehouse_id,island), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY product_id,warehouse_id ORDER BY streak_months DESC,start_month) AS pos FROM streaks)
SELECT product_id,warehouse_id,start_month,end_month,streak_months,depleted_units FROM picked WHERE pos=1
ORDER BY product_id,warehouse_id;

-- ENT-047: Quy mô cây nhân sự dưới trưởng phòng
-- Với mỗi phòng ban, bắt đầu từ manager_employee_id được chỉ định và duyệt mọi hậu duệ qua
-- employees.manager_id, không giới hạn phòng của hậu duệ. Trả số hậu duệ (không gồm gốc), độ sâu lớn
-- nhất với con trực tiếp ở độ sâu 1, và tổng current_salary của hậu duệ. Không có gốc hoặc không có con
-- thì các số bằng 0.
-- Sắp xếp: department_id tăng.
WITH RECURSIVE tree AS (
 SELECT d.department_id,d.manager_employee_id AS root_manager_id,e.employee_id,0 AS depth,
        ARRAY[e.employee_id] AS path,e.current_salary
 FROM departments d JOIN employees e ON e.employee_id=d.manager_employee_id
 UNION ALL
 SELECT t.department_id,t.root_manager_id,e.employee_id,t.depth+1,t.path||e.employee_id,e.current_salary
 FROM tree t JOIN employees e ON e.manager_id=t.employee_id WHERE NOT e.employee_id=ANY(t.path))
SELECT d.department_id,d.manager_employee_id AS root_manager_id,
       COUNT(t.employee_id) FILTER (WHERE t.depth>0) AS descendant_count,
       COALESCE(MAX(t.depth),0) AS max_depth,
       COALESCE(SUM(t.current_salary) FILTER (WHERE t.depth>0),0) AS descendant_payroll
FROM departments d LEFT JOIN tree t ON t.department_id=d.department_id
GROUP BY d.department_id,d.manager_employee_id ORDER BY d.department_id;

-- ENT-048: Mức lương tháng bình quân có bằng chứng trong năm 2025
-- Theo phòng hiện tại, xét từng nhân viên từ max(hire_date,2025-01-01) đến hết 2025-12-31; ngày trước
-- tuyển không tính. Mỗi salary_history.salary áp dụng từ effective_date đến trước mốc kế tiếp. Tính số
-- ngày-nhân viên có mức lương lịch sử xác định, số ngày-nhân viên chưa xác định, và tổng (salary * số
-- ngày áp dụng trong 2025) / 365 làm mức lương tháng bình quân quy đổi trên phần có bằng chứng. Đây là
-- chỉ số lập ngân sách, không phải lương đã trả; không dùng current_salary để lấp giai đoạn thiếu.
-- Sắp xếp: department_id tăng.
WITH intervals AS (
 SELECT employee_id,salary,effective_date,
 LEAD(effective_date,1,DATE '2026-01-01') OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS next_date
 FROM salary_history), clipped AS (
 SELECT e.employee_id,e.department_id,s.salary,
 GREATEST(LEAST(s.next_date,DATE '2026-01-01')-GREATEST(s.effective_date,e.hire_date,DATE '2025-01-01'),0) AS days
 FROM employees e JOIN intervals s ON s.employee_id=e.employee_id WHERE e.hire_date<DATE '2026-01-01'),
known AS (
 SELECT employee_id,SUM(days) AS known_days,SUM(salary*days) AS weighted_salary FROM clipped GROUP BY employee_id),
eligible AS (
 SELECT e.department_id,DATE '2026-01-01'-GREATEST(e.hire_date,DATE '2025-01-01') AS eligible_days,
 COALESCE(k.known_days,0) AS known_days,COALESCE(k.weighted_salary,0) AS weighted_salary
 FROM employees e LEFT JOIN known k USING(employee_id) WHERE e.hire_date<DATE '2026-01-01')
SELECT department_id,SUM(eligible_days) AS eligible_employee_days,SUM(known_days) AS known_salary_days,
       SUM(eligible_days-known_days) AS unknown_salary_days,
       ROUND(SUM(weighted_salary)/365.0,2) AS evidenced_monthly_payroll
FROM eligible GROUP BY department_id ORDER BY department_id;

-- ENT-049: Nút thắt trạng thái phổ biến theo kho và quý
-- Với đơn hiện tại delivered có warehouse_id không NULL, sắp history theo changed_at,history_id. Thời
-- gian một trạng thái là từ sự kiện vào trạng thái đến sự kiện kế tiếp. Trong
-- pending,processing,shipped, chọn trạng thái có thời gian dài nhất của mỗi đơn; hòa ưu tiên pending rồi
-- processing rồi shipped. Nhóm theo warehouse_id và quý order_date; chọn trạng thái được nhiều đơn chọn
-- nhất, hòa theo ưu tiên trên. Trả số đơn chọn trạng thái đó và số giờ trung bình của đoạn trạng thái
-- trên những đơn đó.
-- Sắp xếp: warehouse_id tăng, quarter tăng.
WITH episodes AS (
 SELECT o.order_id,o.warehouse_id,DATE_TRUNC('quarter',o.order_date)::date AS quarter,h.new_status,
 h.changed_at,LEAD(h.changed_at) OVER (PARTITION BY o.order_id ORDER BY h.changed_at,h.history_id) AS next_at
 FROM orders o JOIN order_status_history h ON h.order_id=o.order_id
 WHERE o.status='delivered' AND o.warehouse_id IS NOT NULL), stages AS (
 SELECT *,EXTRACT(EPOCH FROM next_at-changed_at)/3600 AS hours,
 CASE new_status WHEN 'pending' THEN 1 WHEN 'processing' THEN 2 WHEN 'shipped' THEN 3 END AS priority
 FROM episodes WHERE new_status IN ('pending','processing','shipped') AND next_at IS NOT NULL),
per_order AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY hours DESC,priority) AS pos FROM stages), totals AS (
 SELECT warehouse_id,quarter,new_status,priority,COUNT(*) AS selected_orders,AVG(hours) AS average_hours
 FROM per_order WHERE pos=1 GROUP BY 1,2,3,4), picked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY warehouse_id,quarter ORDER BY selected_orders DESC,priority) AS pos FROM totals)
SELECT warehouse_id,quarter,new_status AS bottleneck_status,selected_orders,ROUND(average_hours,2) AS avg_stage_hours
FROM picked WHERE pos=1 ORDER BY warehouse_id,quarter;

-- ENT-050: Chuỗi tăng lương liên tiếp có mức tăng tổng cao nhất
-- Theo từng nhân viên, sắp salary_history bằng effective_date,salary_history_id. Một chuỗi tăng là một
-- đoạn tối đa gồm các mốc liên tiếp có salary sau > salary trước; mốc bằng hoặc giảm cắt chuỗi. Chỉ xét
-- chuỗi có ít nhất 2 lần tăng. Chọn một chuỗi mỗi nhân viên theo tỷ lệ (lương cuối/lương đầu-1) giảm, số
-- lần tăng giảm, ngày bắt đầu tăng. Trả ngày đầu (mốc trước lần tăng thứ nhất), ngày cuối, số lần tăng,
-- lương đầu/cuối và tỷ lệ tăng phần trăm.
-- Sắp xếp: employee_id tăng.
WITH previous AS (
 SELECT *,LAG(salary) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_salary,
 LAG(effective_date) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_date
 FROM salary_history), numbered AS (
 SELECT *,SUM(CASE WHEN previous_salary IS NULL OR salary<=previous_salary THEN 1 ELSE 0 END)
 OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id ROWS UNBOUNDED PRECEDING) AS island
 FROM previous), streaks AS (
 SELECT employee_id,island,MIN(previous_date) AS start_date,MAX(effective_date) AS end_date,
 COUNT(*) AS raise_count,MIN(previous_salary) AS start_salary,MAX(salary) AS end_salary
 FROM numbered WHERE salary>previous_salary GROUP BY employee_id,island HAVING COUNT(*)>=2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY employee_id
 ORDER BY (end_salary/start_salary-1) DESC,raise_count DESC,start_date) AS pos FROM streaks)
SELECT employee_id,start_date,end_date,raise_count,start_salary,end_salary,
       ROUND(100.0*(end_salary/start_salary-1),2) AS growth_pct
FROM ranked WHERE pos=1 ORDER BY employee_id;

