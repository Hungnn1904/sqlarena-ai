"""Reviewed question designs. This module never connects to or changes a database."""

DOMAINS = {'C': 'Customer Management', 'O': 'Sales & Orders',
           'P': 'Product & Inventory', 'H': 'Human Resources', 'F': 'Finance'}
SPECS = []


def design(n, difficulty, skill, domain, title, goal, grain, columns, tables,
           transform, reason, order, *, edge='', time='', limit=None):
    SPECS.append({
        'question_id': f'ENT-{n:03d}', 'world_id': 'enterprise_v1',
        'taxonomy_version': 'v1', 'difficulty': difficulty,
        'primary_skill_group': skill, 'primary_business_domain': DOMAINS[domain],
        'title': title, 'business_goal': goal, 'output_grain': grain,
        'expected_output': columns.split(), 'tables_used': tables.split(),
        'difficulty_reason': reason, 'order_by': order,
        'edge_cases': edge or 'Giữ nguyên NULL ở cột tùy chọn; không suy diễn giá trị thiếu.',
        'time_basis': time or 'Dữ liệu hiện có; không phụ thuộc CURRENT_DATE.',
        'result_limit': limit,
        'logic_signature': {'goal': title, 'central_table': tables.split()[0],
                            'grain': grain, 'transformation': transform,
                            'predicate': goal, 'edge_cases': edge},
        'secondary_skills': [],
    })


design(1, 'easy', 'S1', 'C', 'Khách hàng hoạt động đăng ký trước năm 2025',
       "Liệt kê khách hàng status='active' và registered_at < 2025-01-01.",
       'Một khách hàng', 'customer_id full_name email registered_at', 'customers',
       'filter active and registration cutoff', 'Chỉ lọc và sắp xếp trên một bảng.',
       'registered_at tăng, customer_id tăng', time='registered_at; mốc đầu năm 2025 loại trừ.')
design(2, 'easy', 'S1', 'C', 'Các thành phố có địa chỉ khách hàng',
       'Liệt kê các city khác nhau xuất hiện trong địa chỉ khách hàng.',
       'Một thành phố', 'city', 'customer_addresses', 'distinct address cities',
       'Loại trùng trực tiếp một cột, không cần tổng hợp.', 'city tăng')
design(3, 'easy', 'S1', 'O', 'Hàng đợi đơn chờ xử lý',
       "Liệt kê tất cả đơn status='pending', gồm người mua, kho được gán và giá trị đơn.",
       'Một đơn hàng', 'order_id customer_id warehouse_id order_date total_amount', 'orders',
       'filter pending queue', 'Lọc trực tiếp trạng thái trên một bảng.',
       'order_date tăng, order_id tăng', edge='warehouse_id có thể NULL và phải được giữ.',
       time='order_date; không lọc theo ngày hiện tại.')
design(4, 'easy', 'S1', 'O', 'Đơn đã giao đặt trong năm 2026',
       "Liệt kê đơn status='delivered' có order_date từ 2026-01-01 đến trước 2027-01-01, kèm mốc gửi và giao.",
       'Một đơn hàng', 'order_id order_date shipped_at delivered_at carrier_name', 'orders',
       'filter delivered order date interval', 'Lọc trạng thái và khoảng thời gian trực tiếp.',
       'order_date tăng, order_id tăng', time='Lọc order_date, không lọc delivered_at; khoảng nửa mở năm 2026.')
design(5, 'easy', 'S1', 'P', 'Sản phẩm đang bán có giá niêm yết cao',
       'Liệt kê sản phẩm is_active=true có list_price >= 1000000.',
       'Một sản phẩm', 'product_id product_name sku list_price cost_price', 'products',
       'active product price threshold', 'Lọc giá và trạng thái trên một bảng.',
       'list_price giảm, product_id tăng')
design(6, 'easy', 'S1', 'H', 'Nhân viên không có quản lý trực tiếp',
       'Liệt kê nhân viên có manager_id IS NULL, không giới hạn status.',
       'Một nhân viên', 'employee_id full_name department_id job_title', 'employees',
       'root employee null manager', 'Kiểm tra NULL trực tiếp, không duyệt cây quản lý.', 'employee_id tăng')
design(7, 'easy', 'S1', 'F', 'Yêu cầu hoàn tiền còn chờ',
       "Liệt kê yêu cầu refund_status='pending' và completed_at IS NULL, theo thứ tự tiếp nhận.",
       'Một yêu cầu hoàn tiền', 'refund_id payment_id refund_amount requested_at', 'refunds',
       'pending refund queue', 'Lọc hai điều kiện trực tiếp, không tính tiền ròng.',
       'requested_at tăng, refund_id tăng', time='requested_at.')
design(8, 'easy', 'S1', 'P', 'Quốc gia trong mạng lưới nhà cung cấp',
       'Liệt kê country khác nhau, loại NULL, của toàn bộ nhà cung cấp không giới hạn status.',
       'Một quốc gia', 'country', 'suppliers', 'distinct supplier countries nonnull',
       'DISTINCT và loại NULL trực tiếp.', 'country tăng', edge='Loại country IS NULL.')
design(9, 'easy', 'S2', 'C', 'Danh bạ địa chỉ mặc định',
       'Với mọi khách hàng, nối các địa chỉ is_default=true. Nếu không có thì vẫn giữ khách với các cột địa chỉ NULL.',
       'Một khách hàng và địa chỉ mặc định; một dòng NULL nếu không có',
       'customer_id full_name address_id city address_line', 'customers customer_addresses',
       'left join default addresses preserving customers', 'Một LEFT JOIN trực tiếp với điều kiện địa chỉ mặc định.',
       'customer_id tăng, address_id tăng NULLS LAST',
       edge='Nếu có nhiều địa chỉ mặc định thì giữ từng địa chỉ; không tự giả định unique.')
design(10, 'easy', 'S2', 'O', 'Tên sản phẩm trên từng dòng hàng',
       'Liệt kê mọi dòng order_items cùng tên sản phẩm, số lượng và line_total; không lọc trạng thái đơn.',
       'Một dòng hàng', 'order_item_id order_id product_name quantity line_total', 'order_items products',
       'line product lookup', 'Một JOIN qua khóa ngoại để bổ sung tên sản phẩm.', 'order_item_id tăng')
design(11, 'easy', 'S2', 'P', 'Danh mục trực tiếp của sản phẩm',
       'Liệt kê sản phẩm với tên danh mục trực tiếp và trạng thái is_active của danh mục, không duyệt cha.',
       'Một sản phẩm', 'product_id product_name category_name category_active', 'products categories',
       'product direct category lookup', 'Nối trực tiếp sản phẩm với danh mục.', 'product_id tăng')
design(12, 'easy', 'S2', 'P', 'Liên hệ nguồn cung cho sản phẩm',
       'Liệt kê sản phẩm, nhà cung cấp, quốc gia và email liên hệ; giữ email hoặc quốc gia NULL.',
       'Một sản phẩm', 'product_id sku supplier_name country contact_email', 'products suppliers',
       'product supplier contact lookup', 'Một JOIN để tra cứu quan hệ nguồn cung.', 'product_id tăng')
design(13, 'easy', 'S2', 'H', 'Danh bạ nhân viên và quản lý trực tiếp',
       'Liệt kê mọi nhân viên cùng ID và tên quản lý trực tiếp; nhân viên gốc vẫn xuất hiện.',
       'Một nhân viên', 'employee_id employee_name manager_id manager_name', 'employees',
       'self left join immediate manager', 'SELF LEFT JOIN một cấp, không đệ quy.', 'employee_id tăng')
design(14, 'easy', 'S2', 'H', 'Trưởng phòng được chỉ định',
       'Liệt kê tất cả phòng ban và nhân viên được manager_employee_id chỉ định, không suy từ manager_id.',
       'Một phòng ban', 'department_id department_name manager_employee_id manager_name', 'departments employees',
       'department designated manager left lookup', 'Một LEFT JOIN trực tiếp theo khóa trưởng phòng.', 'department_id tăng',
       edge='Phòng chưa chỉ định trưởng phòng vẫn xuất hiện với manager_name NULL.')
design(15, 'easy', 'S2', 'F', 'Người phê duyệt từng khoản chi',
       'Liệt kê mọi khoản operating_expenses và tên người phê duyệt; khoản chưa có người phê duyệt vẫn xuất hiện.',
       'Một khoản chi', 'expense_id expense_category amount expense_date approver_name', 'operating_expenses employees',
       'expense optional approver lookup', 'Một LEFT JOIN để đọc quan hệ phê duyệt.', 'expense_id tăng',
       edge='Không có approved_at; expense_date không được gọi là ngày phê duyệt.')
design(16, 'easy', 'S3', 'C', 'Quy mô khách hàng theo trạng thái',
       'Đếm khách hàng theo status; mỗi khách chỉ đếm một lần.', 'Một trạng thái khách hàng',
       'status customer_count', 'customers', 'group customer status count',
       'GROUP BY và COUNT đơn giản trên một bảng.', 'status tăng')
design(17, 'easy', 'S3', 'O', 'Giá trị đơn hàng theo trạng thái',
       'Theo status của đơn, tính số đơn và tổng total_amount. Đây là giá trị đơn gồm phí giao hàng, không phải tiền đã thu.',
       'Một trạng thái đơn hàng', 'status order_count order_value', 'orders', 'group status count sum order value',
       'Một bước nhóm và tổng hợp trên orders.', 'status tăng')
design(18, 'easy', 'S3', 'P', 'Tổng biến động theo loại giao dịch kho',
       'Theo transaction_type, tính số giao dịch và tổng quantity_change có dấu, trên toàn bộ kho và thời gian.',
       'Một loại giao dịch', 'transaction_type transaction_count net_units', 'inventory_transactions',
       'group inventory type signed movement sum', 'Tổng hợp một bảng; không tính tồn tích lũy.', 'transaction_type tăng',
       edge='sale có tổng âm; không lấy trị tuyệt đối.')
design(19, 'easy', 'S3', 'H', 'Quỹ lương hiện tại theo mã phòng',
       'Theo department_id của nhân viên, tính số nhân viên và tổng current_salary, không lọc status.',
       'Một mã phòng có nhân viên', 'department_id employee_count current_payroll', 'employees',
       'group department present salary sum', 'Một bước tổng hợp lương hiện tại, không suy lương lịch sử.', 'department_id tăng')
design(20, 'easy', 'S3', 'F', 'Thời gian xử lý hoàn tiền đã hoàn tất',
       "Trong refund_status='completed' có completed_at không NULL, tính số yêu cầu và thời gian xử lý ngắn nhất, dài nhất, trung bình bằng giờ từ requested_at đến completed_at. Làm tròn các số giờ 2 chữ số.",
       'Một dòng thống kê toàn bộ refund hoàn tất', 'completed_refunds min_hours max_hours avg_hours', 'refunds',
       'completed refund turnaround global min max average hours',
       'Tổng hợp trực tiếp độ dài thời gian trên một bảng, không ghép lịch sử sự kiện.',
       'Một dòng nên không có yêu cầu thứ tự', edge='Nếu không có refund hoàn tất thì số yêu cầu=0 và các số giờ=NULL.',
       time='completed_at-requested_at; không dùng attempted_at.')

design(21, 'medium', 'S2', 'C', 'Đơn giao đến thành phố khác địa chỉ mặc định',
       'Liệt kê đơn có city của địa chỉ giao khác city của một địa chỉ mặc định hiện có của khách. Chỉ so với địa chỉ mặc định được lưu hiện tại, không suy lịch sử thay đổi địa chỉ.',
       'Một đơn và địa chỉ mặc định được so sánh',
       'order_id customer_id shipping_city default_address_id default_city', 'orders customer_addresses',
       'two address roles composite owner join city comparison',
       'Phân biệt hai vai trò địa chỉ, nối đúng chủ sở hữu rồi so sánh city; không chỉ tra tên.',
       'order_id tăng, default_address_id tăng', edge='Không có địa chỉ mặc định thì không xuất hiện; nhiều mặc định thì so từng địa chỉ.')
design(22, 'medium', 'S2', 'O', 'Tiến độ xuất từng dòng đơn đang xử lý',
       "Liệt kê từng dòng của đơn status='processing', kho của đơn và tên kho nếu có; nối giao dịch sale bằng order_item_id để cho biết đã xuất hay chưa và thời điểm xuất.",
       'Một dòng hàng của đơn processing',
       'order_id order_item_id product_id quantity warehouse_id warehouse_name has_sale sale_at',
       'orders order_items warehouses inventory_transactions', 'processing line optional warehouse and conditional sale join',
       'Phối hợp dòng hàng, kho tùy chọn và liên kết sale có điều kiện, vẫn giữ dòng chưa xuất.',
       'order_id tăng, order_item_id tăng', edge='Kho hoặc sale có thể NULL; has_sale=false khi chưa xuất.', time='sale_at là transaction_date của sale.')
design(23, 'medium', 'S2', 'H', 'Đối chiếu vai trò quản lý kho và trưởng phòng',
       'Với mỗi kho, tìm người quản lý kho, phòng của người đó và trưởng phòng được chỉ định. Cho biết người quản lý kho có đồng thời là trưởng phòng đó hay không.',
       'Một kho', 'warehouse_id warehouse_manager_id warehouse_manager_name department_name department_manager_id same_person',
       'warehouses employees departments', 'warehouse manager department designated manager role comparison',
       'Nối chuỗi vai trò quản lý và so sánh hai khóa có thể NULL; cần phân biệt quản lý kho với trưởng phòng.',
       'warehouse_id tăng', edge='same_person=NULL nếu thiếu một trong hai ID, không thay NULL bằng false.')
design(24, 'medium', 'S3', 'O', 'Nhân viên xử lý ít nhất năm đơn đã giao',
       'Theo employee_id được gán trên đơn (loại NULL), đếm toàn bộ đơn, số đơn delivered và tổng total_amount chỉ của đơn delivered. Giữ người có ít nhất 5 đơn delivered.',
       'Một nhân viên được gán đơn', 'employee_id assigned_orders delivered_orders delivered_order_value', 'orders',
       'conditional order aggregates employee having delivered minimum',
       'Tổng hợp có điều kiện và lọc nhóm; tránh tính đơn chưa giao vào giá trị đã giao.', 'employee_id tăng')
design(25, 'medium', 'S3', 'P', 'Nhà cung cấp có danh mục hàng hoạt động đa dạng',
       'Trong sản phẩm is_active=true, theo supplier_id tính số sản phẩm, số category_id khác nhau và trung bình list_price-cost_price. Chỉ giữ nhóm có ít nhất 5 sản phẩm và 3 danh mục.',
       'Một nhà cung cấp đạt điều kiện', 'supplier_id active_products category_count avg_unit_margin', 'products',
       'supplier active assortment distinct category having average margin',
       'Kết hợp lọc dòng, nhiều phép tổng hợp và hai điều kiện HAVING.', 'supplier_id tăng',
       edge='avg_unit_margin làm tròn 2 chữ số; là chênh giá trên một đơn vị, không phải lợi nhuận thực tế.')
design(26, 'medium', 'S3', 'C', 'Khách có địa chỉ tại nhiều thành phố',
       'Theo customer_id trong customer_addresses, đếm địa chỉ, số city khác nhau và số địa chỉ mặc định. Chỉ giữ khách có ít nhất 2 city.',
       'Một khách đa thành phố', 'customer_id address_count city_count default_count', 'customer_addresses',
       'customer address diversity distinct count having', 'Cần COUNT DISTINCT, tổng hợp có điều kiện và lọc nhóm.', 'customer_id tăng')
design(27, 'medium', 'S3', 'F', 'Chi phí tháng theo phòng và tình trạng phê duyệt',
       'Theo tháng expense_date và department_id, tính số khoản chi, tổng amount và tổng amount có approved_by_employee_id không NULL. Chỉ giữ nhóm có ít nhất 2 khoản.',
       'Một tháng và phòng; NULL là nhóm chưa gán phòng', 'month department_id expense_count total_expense approved_expense',
       'operating_expenses', 'monthly department conditional expense sums having',
       'Nhóm theo thời gian và phòng, tách chi có người phê duyệt rồi lọc nhóm.',
       'month tăng, department_id tăng NULLS LAST', edge='Nhóm department_id NULL được giữ; không có chi được phê duyệt thì approved_expense=0.', time='expense_date; month là ngày đầu tháng.')
design(28, 'medium', 'S3', 'P', 'Sức chứa còn lại của từng kho',
       'Với mọi kho, tính tồn hiện tại từ tổng quantity_change của mọi sản phẩm, sức chứa còn lại và phần trăm sử dụng capacity. Bao gồm kho không có giao dịch.',
       'Một kho', 'warehouse_id capacity current_units free_capacity utilization_pct', 'warehouses inventory_transactions',
       'warehouse left aggregate current stock capacity ratio',
       'Tổng hợp quan hệ một-nhiều và xử lý kho không có giao dịch hoặc capacity=0.', 'warehouse_id tăng',
       edge='Không có giao dịch thì current_units=0; capacity=0 thì utilization_pct=NULL; phần trăm làm tròn 2 chữ số.')
design(29, 'medium', 'S4', 'C', 'Khách hàng chưa từng đặt đơn',
       'Tìm khách hàng không có bất kỳ bản ghi orders nào, không giới hạn status của khách hoặc đơn.',
       'Một khách hàng', 'customer_id full_name registered_at', 'customers orders',
       'customer anti existence any order', 'Cần xét sự không tồn tại của quan hệ đơn hàng, không chỉ lọc trạng thái khách.', 'customer_id tăng')
design(30, 'medium', 'S4', 'P', 'Hàng chưa được đặt nhưng vẫn có tồn',
       'Tìm sản phẩm không xuất hiện trong bất kỳ order_items nào nhưng có ít nhất một kho với SUM(quantity_change)>0.',
       'Một sản phẩm', 'product_id product_name', 'products order_items inventory_transactions',
       'product anti order existence positive warehouse balance existence',
       'Kết hợp không tồn tại dòng hàng và tồn tại một nhóm tồn dương.', 'product_id tăng')
design(31, 'medium', 'S4', 'H', 'Lương cao hơn trung bình phòng',
       'Tìm nhân viên có current_salary cao hơn trung bình current_salary của mọi nhân viên cùng department_id, gồm cả bản thân và không lọc status.',
       'Một nhân viên', 'employee_id department_id current_salary', 'employees',
       'correlated department salary average comparison', 'So sánh từng nhân viên với tổng hợp tương quan theo phòng.', 'employee_id tăng')
design(32, 'medium', 'S4', 'O', 'Đơn thanh toán thành công sau lần thất bại',
       "Liệt kê mỗi payment success có ít nhất một payment failed của cùng đơn xảy ra trước, theo cặp (attempted_at,payment_id).",
       'Một đơn có success sau failed', 'order_id success_payment_id success_at', 'payments',
       'success payment correlated earlier failed existence',
       'Cần kiểm tra tồn tại sự kiện trước success với khóa thời gian ổn định.', 'order_id tăng', time='attempted_at; cùng thời điểm phân thứ tự bằng payment_id.')
design(33, 'medium', 'S4', 'P', 'Nhà cung cấp hoạt động không có hàng ngừng bán',
       "Tìm supplier status='active' có ít nhất một sản phẩm và không có sản phẩm is_active=false.",
       'Một nhà cung cấp', 'supplier_id supplier_name', 'suppliers products',
       'supplier nonvacuous all products active', 'Kết hợp EXISTS và NOT EXISTS để diễn đạt điều kiện mọi sản phẩm mà không nhận nhóm rỗng.', 'supplier_id tăng')
design(34, 'medium', 'S4', 'O', 'Đơn trả hàng vật lý chưa có hoàn tiền hoàn tất',
       "Tìm đơn delivered có giao dịch return liên kết ít nhất một dòng hàng, nhưng không có refund completed qua bất kỳ payment của đơn. Đây là danh sách đối soát, không kết luận vi phạm BR.",
       'Một đơn hàng', 'order_id customer_id total_amount', 'orders order_items inventory_transactions payments refunds',
       'physical return existence anti completed monetary refund',
       'Đối chiếu tồn tại trả hàng vật lý với không tồn tại hoàn tiền qua hai quan hệ khác.', 'order_id tăng',
       edge='Refund pending/failed không loại đơn; không giả định trả hàng vật lý luôn có refund.')
design(35, 'medium', 'S5', 'O', 'Hai đơn giá trị lớn nhất tại mỗi kho',
       'Trong mọi đơn có warehouse_id không NULL, lấy tối đa 2 đơn mỗi kho theo total_amount giảm, order_date tăng, order_id tăng; không giới hạn trạng thái.',
       'Một đơn được chọn tại mỗi kho', 'warehouse_id position order_id total_amount order_date', 'orders',
       'partition warehouse row number top two order value',
       'Xếp hạng trong từng kho rồi lọc top 2; tie được phá bằng ngày và ID.',
       'warehouse_id tăng, position tăng', edge='Không giữ thêm đồng hạng; loại kho NULL.', limit='Tối đa 2 dòng mỗi kho.')
design(36, 'medium', 'S5', 'P', 'Ba mức giá cao nhất trong từng danh mục',
       'Trong toàn bộ sản phẩm, lấy sản phẩm thuộc 3 mức list_price cao nhất khác nhau mỗi category_id. Các sản phẩm đồng giá có cùng hạng và đều được giữ.',
       'Một sản phẩm thuộc mức giá được chọn', 'category_id price_rank product_id list_price', 'products',
       'category dense rank price bands', 'Cần DENSE_RANK theo danh mục để giữ đầy đủ đồng giá.',
       'category_id tăng, price_rank tăng, product_id tăng', edge='Giữ mọi đồng hạng; có thể hơn 3 sản phẩm mỗi danh mục.', limit='Tối đa 3 mức giá mỗi danh mục.')
design(37, 'medium', 'S5', 'H', 'Biến động lương giữa hai mốc liên tiếp',
       'Với mỗi bản ghi salary_history ngoài bản ghi đầu của nhân viên, trả mức lương trước, mới và phần trăm thay đổi. Thứ tự lịch sử là effective_date, salary_history_id.',
       'Một mốc lương có mốc trước', 'employee_id effective_date previous_salary salary change_pct', 'salary_history',
       'salary lag adjacent event percent change', 'Dùng LAG để so sánh hai mốc kề nhau; chưa tìm chuỗi tăng nhiều lần.',
       'employee_id tăng, effective_date tăng', edge='Bỏ mốc đầu; phần trăm làm tròn 2 chữ số.', time='effective_date, salary_history_id.')
design(38, 'medium', 'S5', 'O', 'Biến động giá trị đơn đã giao theo tháng đặt',
       "Nhóm đơn status='delivered' theo tháng order_date, tính tổng total_amount và phần trăm thay đổi so với tháng có dữ liệu ngay trước trong kết quả.",
       'Một tháng có đơn delivered', 'month order_value previous_value change_pct', 'orders',
       'monthly delivered order value aggregate lag', 'Tổng hợp tháng rồi so sánh nhóm liền trước bằng LAG.',
       'month tăng', edge='Tháng đầu hoặc previous_value=0 có change_pct=NULL; không tự thêm tháng trống; làm tròn 2 chữ số.', time='order_date; không dùng delivered_at.')
design(39, 'medium', 'S5', 'F', 'Tiền thu thành công lũy kế theo tháng',
       "Nhóm payments payment_status='success' theo tháng attempted_at; trả tiền thu tháng và tổng tiền thu lũy kế từ tháng đầu. Không trừ refunds.",
       'Một tháng có thanh toán success', 'month collected_amount cumulative_collected', 'payments',
       'monthly successful cash aggregate running total', 'Tổng hợp tiền thu thực tế rồi tính lũy kế trên các nhóm tháng.', 'month tăng',
       time='attempted_at của success; chỉ tháng có success.')
design(40, 'medium', 'S5', 'C', 'Khoảng cách giữa các lần đặt của khách',
       'Với mỗi đơn ngoài đơn đầu của khách, trả order_id trước đó và số ngày giữa hai order_date liên tiếp. Bao gồm mọi trạng thái; thứ tự order_date,order_id.',
       'Một đơn có đơn trước của cùng khách', 'customer_id order_id previous_order_id gap_days', 'orders',
       'customer repeat order lag fractional day gap', 'Cần LAG theo khách để xác định đơn kề trước và tính khoảng cách.',
       'customer_id tăng, order_date tăng, order_id tăng', edge='Bỏ đơn đầu; gap_days tính cả phần lẻ ngày, làm tròn 2 chữ số.', time='order_date,order_id.')

design(41, 'hard', 'S4', 'P', 'Nguồn cung phủ đầy đủ hàng bán và kho có tồn',
       'Tìm nhà cung cấp có ít nhất 2 sản phẩm đang hoạt động. Mỗi sản phẩm đang hoạt động phải có ít nhất một dòng thuộc đơn delivered; tại mọi kho từng có đơn delivered chứa sản phẩm đó, tổng quantity_change của chính sản phẩm tại kho đó phải >0. Sản phẩm không hoạt động không tham gia điều kiện.',
       'Một nhà cung cấp đạt phép chia quan hệ', 'supplier_id supplier_name',
       'suppliers products order_items orders inventory_transactions',
       'supplier all active products delivered exposure all exposed warehouses positive stock',
       'Phép lượng hóa mọi sản phẩm lồng mọi kho đã giao, kết hợp tồn tại bán và tổng tồn tương quan. Cần chống điều kiện đúng trên tập rỗng ở cả hai tầng.',
       'supplier_id tăng', edge='Kho không có giao dịch được xem có tồn 0; nhà cung cấp ít hơn 2 hàng active bị loại.')
design(42, 'hard', 'S5', 'O', 'Chuỗi thắng tháng dài nhất của nhân viên',
       "Trong đơn delivered có employee_id không NULL, tính giá trị total_amount theo nhân viên và tháng order_date. Mỗi tháng chọn đúng một người thắng theo tổng giảm rồi employee_id tăng. Với mỗi người từng thắng, trả chuỗi thắng ở các tháng lịch liên tiếp dài nhất; nếu hòa chọn chuỗi bắt đầu sớm hơn.",
       'Một nhân viên từng thắng tháng', 'employee_id start_month end_month streak_months', 'orders',
       'monthly employee sums deterministic winner calendar consecutive islands longest',
       'Phải tổng hợp, chọn người thắng từng tháng, phát hiện khoảng đứt theo lịch rồi chọn chuỗi dài nhất từng người. Một ranking đơn lẻ không đủ.',
       'employee_id tăng', edge='Tháng không có đơn eligible cắt chuỗi; tie thắng tháng chọn ID nhỏ; tie chuỗi chọn bắt đầu sớm.', time='Tháng order_date; liên tiếp theo tháng lịch.')
design(43, 'hard', 'S5', 'F', 'Ba cửa sổ ba tháng có tiền ròng lớn nhất',
       "Gộp tiền vào từ payment success theo attempted_at và tiền ra từ refund completed theo completed_at. Tạo đủ các tháng từ tháng sự kiện sớm nhất đến muộn nhất; tháng trống bằng 0. Tính tiền ròng trong cửa sổ 3 tháng lịch kết thúc mỗi tháng, chỉ giữ cửa sổ đủ 3 tháng. Chọn tối đa 3 cửa sổ có tổng ròng lớn nhất, hòa chọn tháng kết thúc sớm hơn.",
       'Một cửa sổ ba tháng được chọn', 'start_month end_month net_three_months', 'payments refunds',
       'signed cash event union calendar zero fill complete three month rolling top windows',
       'Cần hợp nhất hai dòng tiền khác ngày ghi nhận, lấp tháng trống, kiểm tra độ dài cửa sổ và xếp hạng tổng trượt. Đây không phải một SUM lũy kế đơn giản.',
       'net_three_months giảm, end_month tăng', edge='Chỉ completed refund được trừ; không dùng requested_at; không giữ thêm đồng hạng.',
       time='attempted_at và completed_at; cửa sổ tháng lịch.', limit=3)
design(44, 'hard', 'S5', 'F', 'Nhóm loại chi nhỏ nhất đạt 80 phần trăm chi phòng',
       'Trong chi có expense_date thuộc năm 2025, tổng hợp amount theo phòng và expense_category. Xếp loại chi theo tổng giảm, tên loại tăng; với mỗi phòng, giữ tiền tố ngắn nhất mà tổng tích lũy đạt ít nhất 80% tổng chi phòng. Trả từng loại trong tiền tố, vị trí, tiền loại và phần trăm tích lũy.',
       'Một phòng và loại chi trong tiền tố đạt 80%',
       'department_id position expense_category category_amount cumulative_pct', 'operating_expenses',
       'department category sum sorted prefix threshold crossing minimal cover',
       'Cần tổng hợp hai cấp, sắp xếp theo đóng góp, tính tích lũy và giữ đúng loại vượt ngưỡng lần đầu. Phải xử lý nhóm phòng NULL và tie để tiền tố tối thiểu xác định.',
       'department_id tăng NULLS LAST, position tăng', edge='Phòng NULL là một nhóm riêng; làm tròn phần trăm sau khi lọc bằng số chính xác.', time='expense_date >=2025-01-01 và <2026-01-01.')
design(45, 'hard', 'S5', 'O', 'Nhân viên dẫn đầu quý và sản phẩm đóng góp lớn nhất',
       "Trong đơn delivered được gán nhân viên, tổng line_total theo quý order_date, nhân viên và sản phẩm; chọn sản phẩm có tổng lớn nhất mỗi nhân viên-quý (hòa chọn product_id nhỏ). Tính tổng line_total của nhân viên-quý rồi lấy tối đa 3 nhân viên mỗi quý theo tổng giảm, employee_id tăng. Trả sản phẩm dẫn đầu và tỷ trọng đóng góp của nó. Đây là giá trị hàng theo dòng, không gồm shipping_fee, không trừ refund hoặc trả hàng vật lý, không phải tiền ròng.",
       'Một nhân viên được chọn mỗi quý', 'quarter employee_rank employee_id merchandise_value top_product_id top_product_value top_share_pct',
       'orders order_items', 'quarter employee product aggregate product leader employee totals top three share',
       'Xếp hạng ở hai grain khác nhau: sản phẩm trong nhân viên-quý và nhân viên trong quý; tổng nhân viên phải bao gồm cả sản phẩm không thắng. Tie và mẫu số cần xác định riêng.',
       'quarter tăng, employee_rank tăng', edge='Tổng bằng 0 thì tỷ trọng NULL; phần trăm làm tròn 2 chữ số; không giữ thêm đồng hạng.',
       time='Quý order_date; quarter là ngày đầu quý.', limit='Tối đa 3 nhân viên mỗi quý.')
design(46, 'hard', 'S6', 'P', 'Chuỗi giảm tồn liên tiếp dưới ngưỡng 50 đơn vị',
       'Xét tháng 2025-03 đến 2026-09 cho mỗi cặp sản phẩm-kho có giao dịch. Tồn cuối tháng là tổng mọi quantity_change trước đầu tháng tiếp theo, kể cả giao dịch trước kỳ. Tháng đủ điều kiện khi tồn cuối < tồn đầu và tồn cuối <=50 đơn vị. Với mỗi cặp có tháng đủ điều kiện, tìm chuỗi tháng lịch đủ điều kiện liên tục dài nhất; hòa chọn chuỗi bắt đầu sớm hơn. Trả đầu/cuối chuỗi, số tháng và tổng số đơn vị giảm. Ngưỡng 50 là tham số phân tích, không phải Business Rule.',
       'Một cặp sản phẩm-kho có chuỗi giảm', 'product_id warehouse_id start_month end_month streak_months depleted_units',
       'inventory_transactions', 'pair calendar historical opening closing stock low threshold negative delta islands longest depletion',
       'Cần dựng lịch đầy đủ, đưa tồn trước kỳ vào tích lũy, so sánh hai đầu tháng và gom đảo giảm liên tiếp. Tháng trống phải cắt chuỗi giảm.',
       'product_id tăng, warehouse_id tăng', edge='Không có giao dịch trước kỳ thì tồn đầu=0; không bỏ tháng trống; bỏ cặp không có tháng giảm.',
       time='transaction_date; kỳ [2025-03-01,2026-10-01).')
design(47, 'hard', 'S6', 'H', 'Quy mô cây nhân sự dưới trưởng phòng',
       'Với mỗi phòng ban, bắt đầu từ manager_employee_id được chỉ định và duyệt mọi hậu duệ qua employees.manager_id, không giới hạn phòng của hậu duệ. Trả số hậu duệ (không gồm gốc), độ sâu lớn nhất với con trực tiếp ở độ sâu 1, và tổng current_salary của hậu duệ. Không có gốc hoặc không có con thì các số bằng 0.',
       'Một phòng ban', 'department_id root_manager_id descendant_count max_depth descendant_payroll', 'departments employees',
       'designated manager recursive descendants depth payroll cycle guard',
       'Cần đệ quy nhiều cấp, chống lặp đường đi, loại gốc khỏi thống kê và giữ phòng chưa có cây. SELF JOIN một cấp không giải được.',
       'department_id tăng', edge='Không lọc status; đường đi dùng mảng ID chống chu trình; số liệu không gồm trưởng phòng gốc.')
design(48, 'hard', 'S6', 'F', 'Mức lương tháng bình quân có bằng chứng trong năm 2025',
       'Theo phòng hiện tại, xét từng nhân viên từ max(hire_date,2025-01-01) đến hết 2025-12-31; ngày trước tuyển không tính. Mỗi salary_history.salary áp dụng từ effective_date đến trước mốc kế tiếp. Tính số ngày-nhân viên có mức lương lịch sử xác định, số ngày-nhân viên chưa xác định, và tổng (salary * số ngày áp dụng trong 2025) / 365 làm mức lương tháng bình quân quy đổi trên phần có bằng chứng. Đây là chỉ số lập ngân sách, không phải lương đã trả; không dùng current_salary để lấp giai đoạn thiếu.',
       'Một phòng có ít nhất một nhân viên được tuyển trước hết 2025',
       'department_id eligible_employee_days known_salary_days unknown_salary_days evidenced_monthly_payroll',
       'employees salary_history', 'salary effective intervals clip employment year weighted salary days missing coverage',
       'Cần dựng khoảng hiệu lực, cắt theo ngày tuyển và năm, cộng mức lương nhân số ngày rồi đối chiếu độ phủ. Lương hiện tại không xác định được quá khứ bị thiếu.',
       'department_id tăng', edge='Không có lịch sử thì known=0 và unknown=mọi ngày eligible; chỉ số lương bằng 0 nếu không có phần được ghi nhận; ngày kết thúc loại trừ.',
       time='Năm 2025 có 365 ngày; hiệu lực [effective_date,next_effective_date).')
design(49, 'hard', 'S6', 'O', 'Nút thắt trạng thái phổ biến theo kho và quý',
       "Với đơn hiện tại delivered có warehouse_id không NULL, sắp history theo changed_at,history_id. Thời gian một trạng thái là từ sự kiện vào trạng thái đến sự kiện kế tiếp. Trong pending,processing,shipped, chọn trạng thái có thời gian dài nhất của mỗi đơn; hòa ưu tiên pending rồi processing rồi shipped. Nhóm theo warehouse_id và quý order_date; chọn trạng thái được nhiều đơn chọn nhất, hòa theo ưu tiên trên. Trả số đơn chọn trạng thái đó và số giờ trung bình của đoạn trạng thái trên những đơn đó.",
       'Một kho-quý có đơn delivered', 'warehouse_id quarter bottleneck_status selected_orders avg_stage_hours',
       'orders order_status_history', 'status lead intervals per order bottleneck then warehouse quarter modal bottleneck',
       'Phải tái dựng đoạn lịch sử, chọn cực đại từng đơn rồi chọn mode ở grain kho-quý. Hai tầng lựa chọn có tie riêng và không được trộn thời gian của trạng thái khác.',
       'warehouse_id tăng, quarter tăng', edge='Không tính thời gian delivered vì không có sự kiện kết thúc; trung bình giờ làm tròn 2 chữ số.', time='Độ dài bằng changed_at; nhóm quý theo order_date.')
design(50, 'hard', 'S6', 'H', 'Chuỗi tăng lương liên tiếp có mức tăng tổng cao nhất',
       'Theo từng nhân viên, sắp salary_history bằng effective_date,salary_history_id. Một chuỗi tăng là một đoạn tối đa gồm các mốc liên tiếp có salary sau > salary trước; mốc bằng hoặc giảm cắt chuỗi. Chỉ xét chuỗi có ít nhất 2 lần tăng. Chọn một chuỗi mỗi nhân viên theo tỷ lệ (lương cuối/lương đầu-1) giảm, số lần tăng giảm, ngày bắt đầu tăng. Trả ngày đầu (mốc trước lần tăng thứ nhất), ngày cuối, số lần tăng, lương đầu/cuối và tỷ lệ tăng phần trăm.',
       'Một nhân viên có chuỗi ít nhất hai lần tăng', 'employee_id start_date end_date raise_count start_salary end_salary growth_pct',
       'salary_history', 'adjacent salary raises maximal islands endpoint growth best streak',
       'Cần phát hiện các cạnh tăng, giữ mốc tiền nhiệm ở đầu chuỗi, gom đoạn tối đa rồi so sánh tỷ lệ hai đầu. Tính từng LAG riêng lẻ không xác định được chuỗi tốt nhất.',
       'employee_id tăng', edge='Mốc bằng/giảm cắt chuỗi; xếp bằng tỷ lệ chưa làm tròn, chỉ làm tròn growth_pct đầu ra 2 chữ số.', time='effective_date; salary_history_id phá hòa.')

SQL = {}

SQL.update({
1: """SELECT customer_id, full_name, email, registered_at
FROM customers WHERE status='active' AND registered_at < TIMESTAMP '2025-01-01'
ORDER BY registered_at, customer_id""",
2: "SELECT DISTINCT city FROM customer_addresses ORDER BY city",
3: """SELECT order_id, customer_id, warehouse_id, order_date, total_amount
FROM orders WHERE status='pending' ORDER BY order_date, order_id""",
4: """SELECT order_id, order_date, shipped_at, delivered_at, carrier_name FROM orders
WHERE status='delivered' AND order_date >= TIMESTAMP '2026-01-01'
  AND order_date < TIMESTAMP '2027-01-01' ORDER BY order_date, order_id""",
5: """SELECT product_id, product_name, sku, list_price, cost_price FROM products
WHERE is_active AND list_price >= 1000000 ORDER BY list_price DESC, product_id""",
6: """SELECT employee_id, full_name, department_id, job_title FROM employees
WHERE manager_id IS NULL ORDER BY employee_id""",
7: """SELECT refund_id, payment_id, refund_amount, requested_at FROM refunds
WHERE refund_status='pending' AND completed_at IS NULL ORDER BY requested_at, refund_id""",
8: "SELECT DISTINCT country FROM suppliers WHERE country IS NOT NULL ORDER BY country",
9: """SELECT c.customer_id, c.full_name, a.address_id, a.city, a.address_line
FROM customers c LEFT JOIN customer_addresses a ON a.customer_id=c.customer_id AND a.is_default
ORDER BY c.customer_id, a.address_id NULLS LAST""",
10: """SELECT i.order_item_id, i.order_id, p.product_name, i.quantity, i.line_total
FROM order_items i JOIN products p ON p.product_id=i.product_id ORDER BY i.order_item_id""",
11: """SELECT p.product_id, p.product_name, c.category_name, c.is_active AS category_active
FROM products p JOIN categories c ON c.category_id=p.category_id ORDER BY p.product_id""",
12: """SELECT p.product_id, p.sku, s.supplier_name, s.country, s.contact_email
FROM products p JOIN suppliers s ON s.supplier_id=p.supplier_id ORDER BY p.product_id""",
13: """SELECT e.employee_id, e.full_name AS employee_name, e.manager_id, m.full_name AS manager_name
FROM employees e LEFT JOIN employees m ON m.employee_id=e.manager_id ORDER BY e.employee_id""",
14: """SELECT d.department_id, d.department_name, d.manager_employee_id, e.full_name AS manager_name
FROM departments d LEFT JOIN employees e ON e.employee_id=d.manager_employee_id ORDER BY d.department_id""",
15: """SELECT x.expense_id, x.expense_category, x.amount, x.expense_date, e.full_name AS approver_name
FROM operating_expenses x LEFT JOIN employees e ON e.employee_id=x.approved_by_employee_id ORDER BY x.expense_id""",
16: "SELECT status, COUNT(*) AS customer_count FROM customers GROUP BY status ORDER BY status",
17: """SELECT status, COUNT(*) AS order_count, SUM(total_amount) AS order_value
FROM orders GROUP BY status ORDER BY status""",
18: """SELECT transaction_type, COUNT(*) AS transaction_count, SUM(quantity_change) AS net_units
FROM inventory_transactions GROUP BY transaction_type ORDER BY transaction_type""",
19: """SELECT department_id, COUNT(*) AS employee_count, SUM(current_salary) AS current_payroll
FROM employees GROUP BY department_id ORDER BY department_id""",
20: """SELECT COUNT(*) AS completed_refunds,
 ROUND(MIN(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS min_hours,
 ROUND(MAX(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS max_hours,
 ROUND(AVG(EXTRACT(EPOCH FROM completed_at-requested_at)/3600),2) AS avg_hours
FROM refunds WHERE refund_status='completed' AND completed_at IS NOT NULL""",
21: """SELECT o.order_id, o.customer_id, a.city AS shipping_city,
       d.address_id AS default_address_id, d.city AS default_city
FROM orders o JOIN customer_addresses a
  ON a.address_id=o.shipping_address_id AND a.customer_id=o.customer_id
JOIN customer_addresses d ON d.customer_id=o.customer_id AND d.is_default
WHERE a.city<>d.city ORDER BY o.order_id, d.address_id""",
22: """SELECT o.order_id, i.order_item_id, i.product_id, i.quantity, o.warehouse_id,
       w.warehouse_name, t.transaction_id IS NOT NULL AS has_sale, t.transaction_date AS sale_at
FROM orders o JOIN order_items i ON i.order_id=o.order_id
LEFT JOIN warehouses w ON w.warehouse_id=o.warehouse_id
LEFT JOIN inventory_transactions t ON t.order_item_id=i.order_item_id AND t.transaction_type='sale'
WHERE o.status='processing' ORDER BY o.order_id, i.order_item_id""",
23: """SELECT w.warehouse_id, e.employee_id AS warehouse_manager_id,
       e.full_name AS warehouse_manager_name, d.department_name,
       d.manager_employee_id AS department_manager_id,
       e.employee_id=d.manager_employee_id AS same_person
FROM warehouses w LEFT JOIN employees e ON e.employee_id=w.manager_employee_id
LEFT JOIN departments d ON d.department_id=e.department_id ORDER BY w.warehouse_id""",
24: """SELECT employee_id, COUNT(*) AS assigned_orders,
       COUNT(*) FILTER (WHERE status='delivered') AS delivered_orders,
       SUM(total_amount) FILTER (WHERE status='delivered') AS delivered_order_value
FROM orders WHERE employee_id IS NOT NULL GROUP BY employee_id
HAVING COUNT(*) FILTER (WHERE status='delivered')>=5 ORDER BY employee_id""",
25: """SELECT supplier_id, COUNT(*) AS active_products, COUNT(DISTINCT category_id) AS category_count,
       ROUND(AVG(list_price-cost_price),2) AS avg_unit_margin
FROM products WHERE is_active GROUP BY supplier_id
HAVING COUNT(*)>=5 AND COUNT(DISTINCT category_id)>=3 ORDER BY supplier_id""",
26: """SELECT customer_id, COUNT(*) AS address_count, COUNT(DISTINCT city) AS city_count,
       COUNT(*) FILTER (WHERE is_default) AS default_count
FROM customer_addresses GROUP BY customer_id HAVING COUNT(DISTINCT city)>=2 ORDER BY customer_id""",
27: """SELECT DATE_TRUNC('month',expense_date)::date AS month, department_id,
       COUNT(*) AS expense_count, SUM(amount) AS total_expense,
       COALESCE(SUM(amount) FILTER (WHERE approved_by_employee_id IS NOT NULL),0) AS approved_expense
FROM operating_expenses GROUP BY DATE_TRUNC('month',expense_date)::date, department_id
HAVING COUNT(*)>=2 ORDER BY month, department_id NULLS LAST""",
28: """SELECT w.warehouse_id, w.capacity, COALESCE(SUM(t.quantity_change),0) AS current_units,
       w.capacity-COALESCE(SUM(t.quantity_change),0) AS free_capacity,
       ROUND(100.0*COALESCE(SUM(t.quantity_change),0)/NULLIF(w.capacity,0),2) AS utilization_pct
FROM warehouses w LEFT JOIN inventory_transactions t ON t.warehouse_id=w.warehouse_id
GROUP BY w.warehouse_id, w.capacity ORDER BY w.warehouse_id""",
29: """SELECT c.customer_id, c.full_name, c.registered_at FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id) ORDER BY c.customer_id""",
30: """SELECT p.product_id, p.product_name FROM products p
WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.product_id=p.product_id)
  AND EXISTS (SELECT 1 FROM inventory_transactions t WHERE t.product_id=p.product_id
              GROUP BY t.warehouse_id HAVING SUM(t.quantity_change)>0) ORDER BY p.product_id""",
31: """SELECT e.employee_id, e.department_id, e.current_salary FROM employees e
WHERE e.current_salary>(SELECT AVG(p.current_salary) FROM employees p WHERE p.department_id=e.department_id)
ORDER BY e.employee_id""",
32: """SELECT s.order_id, s.payment_id AS success_payment_id, s.attempted_at AS success_at FROM payments s
WHERE s.payment_status='success' AND EXISTS (
  SELECT 1 FROM payments f WHERE f.order_id=s.order_id AND f.payment_status='failed'
  AND (f.attempted_at,f.payment_id)<(s.attempted_at,s.payment_id)) ORDER BY s.order_id""",
33: """SELECT s.supplier_id, s.supplier_name FROM suppliers s
WHERE s.status='active' AND EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id)
AND NOT EXISTS (SELECT 1 FROM products p WHERE p.supplier_id=s.supplier_id AND NOT p.is_active)
ORDER BY s.supplier_id""",
34: """SELECT o.order_id, o.customer_id, o.total_amount FROM orders o WHERE o.status='delivered'
AND EXISTS (SELECT 1 FROM order_items i JOIN inventory_transactions t ON t.order_item_id=i.order_item_id
            WHERE i.order_id=o.order_id AND t.transaction_type='return')
AND NOT EXISTS (SELECT 1 FROM payments p JOIN refunds r ON r.payment_id=p.payment_id
                WHERE p.order_id=o.order_id AND r.refund_status='completed') ORDER BY o.order_id""",
35: """WITH ranked AS (
 SELECT warehouse_id, ROW_NUMBER() OVER (PARTITION BY warehouse_id
        ORDER BY total_amount DESC,order_date,order_id) AS position, order_id,total_amount,order_date
 FROM orders WHERE warehouse_id IS NOT NULL)
SELECT warehouse_id,position,order_id,total_amount,order_date FROM ranked WHERE position<=2
ORDER BY warehouse_id,position""",
36: """WITH ranked AS (
 SELECT category_id,DENSE_RANK() OVER (PARTITION BY category_id ORDER BY list_price DESC) AS price_rank,
        product_id,list_price FROM products)
SELECT category_id,price_rank,product_id,list_price FROM ranked WHERE price_rank<=3
ORDER BY category_id,price_rank,product_id""",
37: """WITH previous AS (
 SELECT employee_id,effective_date,salary,
 LAG(salary) OVER (PARTITION BY employee_id ORDER BY effective_date,salary_history_id) AS previous_salary
 FROM salary_history)
SELECT employee_id,effective_date,previous_salary,salary,
       ROUND(100.0*(salary-previous_salary)/previous_salary,2) AS change_pct
FROM previous WHERE previous_salary IS NOT NULL ORDER BY employee_id,effective_date""",
38: """WITH monthly AS (
 SELECT DATE_TRUNC('month',order_date)::date AS month,SUM(total_amount) AS order_value
 FROM orders WHERE status='delivered' GROUP BY 1), compared AS (
 SELECT month,order_value,LAG(order_value) OVER (ORDER BY month) AS previous_value FROM monthly)
SELECT month,order_value,previous_value,
       ROUND(100.0*(order_value-previous_value)/NULLIF(previous_value,0),2) AS change_pct
FROM compared ORDER BY month""",
39: """WITH monthly AS (
 SELECT DATE_TRUNC('month',attempted_at)::date AS month,SUM(amount) AS collected_amount
 FROM payments WHERE payment_status='success' GROUP BY 1)
SELECT month,collected_amount,SUM(collected_amount) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS cumulative_collected
FROM monthly ORDER BY month""",
40: """WITH previous AS (
 SELECT customer_id,order_id,order_date,
 LAG(order_id) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_order_id,
 LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date,order_id) AS previous_date FROM orders)
SELECT customer_id,order_id,previous_order_id,
       ROUND(EXTRACT(EPOCH FROM order_date-previous_date)/86400,2) AS gap_days
FROM previous WHERE previous_order_id IS NOT NULL ORDER BY customer_id,order_date,order_id""",
})

SQL.update({
41: """SELECT s.supplier_id,s.supplier_name FROM suppliers s
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
ORDER BY s.supplier_id""",
42: """WITH totals AS (
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
SELECT employee_id,start_month,end_month,streak_months FROM picked WHERE pos=1 ORDER BY employee_id""",
43: """WITH events AS (
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
FROM rolling WHERE months_in_window=3 ORDER BY net_three_months DESC,month LIMIT 3""",
44: """WITH categories AS (
 SELECT department_id,expense_category,SUM(amount) AS category_amount FROM operating_expenses
 WHERE expense_date>=DATE '2025-01-01' AND expense_date<DATE '2026-01-01' GROUP BY 1,2), ranked AS (
 SELECT *,ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category) AS position,
 SUM(category_amount) OVER (PARTITION BY department_id) AS total,
 SUM(category_amount) OVER (PARTITION BY department_id ORDER BY category_amount DESC,expense_category
 ROWS UNBOUNDED PRECEDING) AS cumulative FROM categories)
SELECT department_id,position,expense_category,category_amount,ROUND(100.0*cumulative/total,2) AS cumulative_pct
FROM ranked WHERE cumulative-category_amount<0.8*total ORDER BY department_id NULLS LAST,position""",
45: """WITH products AS (
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
FROM leaders WHERE employee_rank<=3 ORDER BY quarter,employee_rank""",
46: """WITH pairs AS (
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
ORDER BY product_id,warehouse_id""",
47: """WITH RECURSIVE tree AS (
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
GROUP BY d.department_id,d.manager_employee_id ORDER BY d.department_id""",
48: """WITH intervals AS (
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
FROM eligible GROUP BY department_id ORDER BY department_id""",
49: """WITH episodes AS (
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
FROM picked WHERE pos=1 ORDER BY warehouse_id,quarter""",
50: """WITH previous AS (
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
FROM ranked WHERE pos=1 ORDER BY employee_id""",
})
