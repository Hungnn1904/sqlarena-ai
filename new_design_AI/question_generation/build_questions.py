"""Write blueprints before assembling unvalidated candidates; no database access."""
import argparse
import json
from collections import Counter
from pathlib import Path

from question_specs import SPECS, SQL

ROOT = Path(__file__).resolve().parent
DIFFICULTY = {'easy': 20, 'medium': 20, 'hard': 10}
SKILLS = {'easy': {'S1': 8, 'S2': 7, 'S3': 5},
          'medium': {'S2': 3, 'S3': 5, 'S4': 6, 'S5': 6},
          'hard': {'S4': 1, 'S5': 4, 'S6': 5}}
DOMAINS = {'Customer Management': 8, 'Sales & Orders': 13,
           'Product & Inventory': 12, 'Human Resources': 9, 'Finance': 8}
MEANINGS = {
    'full_name':'Họ tên được lưu', 'employee_name':'Tên nhân viên', 'email':'Email khách hàng',
    'city':'Thành phố của địa chỉ', 'country':'Quốc gia nhà cung cấp', 'address_line':'Địa chỉ chi tiết',
    'contact_email':'Email liên hệ nhà cung cấp, có thể NULL', 'product_name':'Tên sản phẩm',
    'category_name':'Tên danh mục trực tiếp', 'category_active':'Danh mục trực tiếp còn hoạt động',
    'supplier_name':'Tên nhà cung cấp', 'department_name':'Tên phòng ban', 'warehouse_name':'Tên kho',
    'manager_id':'Mã quản lý trực tiếp, có thể NULL', 'manager_name':'Tên quản lý ở vai trò được hỏi',
    'manager_employee_id':'Mã trưởng phòng được chỉ định', 'approver_name':'Tên người phê duyệt, có thể NULL',
    'warehouse_manager_id':'Mã người quản lý kho', 'warehouse_manager_name':'Tên người quản lý kho',
    'department_manager_id':'Mã trưởng phòng của người quản lý kho',
    'default_address_id':'Mã địa chỉ mặc định được so sánh', 'default_city':'Thành phố địa chỉ mặc định',
    'shipping_city':'Thành phố địa chỉ giao hàng của đơn', 'carrier_name':'Tên đơn vị vận chuyển được lưu',
    'job_title':'Chức danh công việc', 'sku':'Mã SKU của sản phẩm', 'quantity':'Số đơn vị trên dòng hàng',
    'expense_category':'Loại chi phí', 'status':'Trạng thái của đối tượng được nhóm hoặc lọc trong đề',
    'transaction_type':'Loại biến động kho', 'success_payment_id':'Mã payment success được xét',
    'top_product_id':'Mã sản phẩm đóng góp lớn nhất theo quy tắc chọn trong đề',
    'customer_count':'Số khách hàng', 'employee_count':'Số nhân viên', 'order_count':'Số đơn hàng',
    'transaction_count':'Số giao dịch kho', 'completed_refunds':'Số yêu cầu hoàn tiền completed có ngày hoàn tất',
    'assigned_orders':'Số đơn được gán nhân viên', 'delivered_orders':'Số đơn delivered được gán nhân viên',
    'active_products':'Số sản phẩm đang hoạt động', 'category_count':'Số danh mục trực tiếp khác nhau',
    'address_count':'Số địa chỉ của khách', 'city_count':'Số thành phố khác nhau của khách',
    'default_count':'Số địa chỉ được đánh dấu mặc định', 'expense_count':'Số khoản chi trong nhóm',
    'customer_id':'Mã khách hàng', 'employee_id':'Mã nhân viên', 'department_id':'Mã phòng hiện tại',
    'product_id':'Mã sản phẩm', 'supplier_id':'Mã nhà cung cấp', 'warehouse_id':'Mã kho',
    'order_id':'Mã đơn hàng', 'order_item_id':'Mã dòng hàng', 'refund_id':'Mã yêu cầu hoàn tiền',
    'payment_id':'Mã lần thử thanh toán', 'address_id':'Mã địa chỉ', 'expense_id':'Mã khoản chi',
    'category_id':'Mã danh mục trực tiếp', 'registered_at':'Thời điểm đăng ký', 'order_date':'Thời điểm đặt đơn',
    'shipped_at':'Thời điểm gửi hàng', 'delivered_at':'Thời điểm giao hàng',
    'requested_at':'Thời điểm yêu cầu hoàn tiền', 'expense_date':'Ngày phát sinh chi phí',
    'effective_date':'Ngày bắt đầu áp dụng mức lương', 'sale_at':'Thời điểm transaction_date của sale, có thể NULL',
    'success_at':'Thời điểm attempted_at của payment success', 'month':'Ngày đầu tháng', 'quarter':'Ngày đầu quý',
    'total_amount':'Giá trị đơn gồm phí giao hàng, VND', 'line_total':'Giá trị dòng sau chiết khấu, VND',
    'list_price':'Giá niêm yết một đơn vị, VND', 'cost_price':'Giá vốn được lưu hiện tại, VND',
    'amount':'Giá trị khoản chi, VND', 'refund_amount':'Giá trị yêu cầu hoàn tiền, VND',
    'current_salary':'Mức lương hiện tại, VND', 'salary':'Mức lương có hiệu lực ở mốc mới, VND',
    'previous_salary':'Mức lương tại mốc liền trước, VND', 'current_payroll':'Tổng lương hiện tại, VND',
    'descendant_payroll':'Tổng lương hiện tại của hậu duệ, không gồm gốc, VND',
    'order_value':'Tổng giá trị đơn, không phải tiền thực thu, VND',
    'delivered_order_value':'Tổng total_amount của đơn delivered, VND',
    'collected_amount':'Tiền payment success trong tháng, VND',
    'cumulative_collected':'Tiền payment success lũy kế, chưa trừ refund, VND',
    'net_three_months':'Tiền success trừ completed refund theo ngày sự kiện trong 3 tháng, VND',
    'merchandise_value':'Tổng line_total, không gồm shipping_fee hoặc trừ refund, VND',
    'top_product_value':'Tổng line_total của sản phẩm đứng đầu, VND',
    'top_share_pct':'Tỷ trọng phần trăm sản phẩm đứng đầu', 'avg_unit_margin':'Bình quân list_price-cost_price, VND',
    'total_expense':'Tổng amount của nhóm chi, VND', 'approved_expense':'Tổng chi có người phê duyệt, VND',
    'category_amount':'Tổng amount của loại chi trong phòng, VND', 'cumulative_pct':'Phần trăm đóng góp tích lũy',
    'current_units':'Số đơn vị tồn từ tổng biến động', 'net_units':'Tổng biến động số lượng có dấu',
    'capacity':'Sức chứa kho bằng đơn vị sản phẩm', 'free_capacity':'capacity trừ tồn hiện tại',
    'utilization_pct':'Phần trăm sức chứa đang dùng', 'has_sale':'Có sale liên kết dòng hàng hay không',
    'same_person':'Hai người giữ vai trò quản lý có trùng ID; NULL nếu thiếu ID',
    'position':'Vị trí theo thứ tự xác định trong đề', 'employee_rank':'Vị trí nhân viên trong quý',
    'price_rank':'Hạng mức giá khác nhau trong danh mục; đồng giá cùng hạng',
    'previous_order_id':'Mã đơn liền trước của cùng khách', 'gap_days':'Khoảng cách ngày có phần lẻ',
    'previous_value':'Giá trị của tháng có dữ liệu liền trước, VND', 'change_pct':'Phần trăm thay đổi so với mốc trước',
    'start_month':'Ngày đầu tháng bắt đầu đoạn', 'end_month':'Ngày đầu tháng kết thúc đoạn',
    'streak_months':'Số tháng lịch liên tiếp trong đoạn', 'depleted_units':'Tổng giảm đơn vị trong đoạn được chọn',
    'root_manager_id':'Mã trưởng phòng gốc của cây', 'descendant_count':'Số hậu duệ không gồm gốc',
    'max_depth':'Độ sâu lớn nhất, con trực tiếp có độ sâu 1',
    'eligible_employee_days':'Tổng ngày-nhân viên sau ngày tuyển trong năm',
    'known_salary_days':'Tổng ngày-nhân viên có mức lương lịch sử xác định',
    'unknown_salary_days':'Tổng ngày-nhân viên chưa biết mức lương lịch sử',
    'evidenced_monthly_payroll':'Tổng salary*ngày có bằng chứng chia 365; chỉ số ngân sách, VND',
    'bottleneck_status':'Trạng thái thắng hai tầng chọn theo đề', 'selected_orders':'Số đơn chọn trạng thái thắng',
    'avg_stage_hours':'Giờ trung bình đoạn trạng thái thắng của các đơn chọn nó',
    'start_date':'Ngày hiệu lực mốc lương đầu đoạn', 'end_date':'Ngày hiệu lực mốc lương cuối đoạn',
    'start_salary':'Mức lương đầu đoạn, VND', 'end_salary':'Mức lương cuối đoạn, VND',
    'raise_count':'Số cạnh tăng lương liên tiếp trong đoạn', 'growth_pct':'Phần trăm tăng giữa hai đầu đoạn',
    'min_hours':'Số giờ xử lý ngắn nhất', 'max_hours':'Số giờ xử lý dài nhất', 'avg_hours':'Số giờ xử lý trung bình',
}


def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def quotas(items):
    return {'difficulty': dict(Counter(q['difficulty'] for q in items)),
            'skills_by_difficulty': {d: dict(Counter(q['primary_skill_group'] for q in items
                                                    if q['difficulty'] == d)) for d in DIFFICULTY},
            'business_domains': dict(Counter(q['primary_business_domain'] for q in items))}


def assert_quota(items):
    actual = quotas(items)
    if actual != {'difficulty': DIFFICULTY, 'skills_by_difficulty': SKILLS, 'business_domains': DOMAINS}:
        raise ValueError(f'Quota mismatch: {actual}')
    if [q['question_id'] for q in items] != [f'ENT-{i:03d}' for i in range(1, 51)]:
        raise ValueError('Question IDs must be ENT-001 through ENT-050 in order')
    signatures = [json.dumps(q['logic_signature'], sort_keys=True) for q in items]
    if len(set(signatures))!=50:
        raise ValueError('Duplicate logic signatures')
    return actual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blueprints-only', action='store_true')
    args = parser.parse_args()
    distribution = assert_quota(SPECS)
    write_json('question_blueprints.json', SPECS)
    write_json('blueprint_distribution.json', distribution)
    if args.blueprints_only:
        print('50 blueprints; all quotas matched; no SQL executed.')
        return
    if set(SQL)!=set(range(1,51)):
        raise ValueError('Reference SQL definitions are incomplete')
    candidates = []
    for n, spec in enumerate(SPECS, 1):
        q = dict(spec)
        q['output_columns'] = [{'name': c, 'meaning': MEANINGS.get(c,c)} for c in q.pop('expected_output')]
        q['money_unit'] = 'VND'
        q['ordering_required'] = n != 20
        q['question_text'] = (q['business_goal'] + '\nCột kết quả theo thứ tự: ' +
                              ', '.join(c['name'] for c in q['output_columns']) +
                              '.\nSắp xếp: ' + q['order_by'] + '.\nQuy tắc biên: ' +
                              q['edge_cases'] + '\nThời gian: ' + q['time_basis'] +
                              '\nMọi số tiền giữ đơn vị tiền của dataset (VND), không đổi sang triệu đồng.')
        q['reference_sql'] = SQL[n].strip().rstrip(';') + ';'
        q['validation'] = {'status': 'NOT_EXECUTED', 'sql_executed': False,
                           'semantic_valid': False, 'row_count': None, 'runtime_ms': None,
                           'column_types': [], 'result_summary': None, 'error': None}
        q['secondary_skills'] = [s for s, tokens in {
            'conditional_aggregation': ['FILTER', 'CASE'], 'calendar': ['generate_series'],
            'window': [' OVER '], 'recursive_hierarchy': ['RECURSIVE'],
            'anti_existence': ['NOT EXISTS'], 'temporal_intervals': ['LEAD('],
        }.items() if any(t.upper() in q['reference_sql'].upper() for t in tokens)]
        candidates.append(q)
    write_json('questions_candidates.json', candidates)
    print('50 candidates written as NOT_EXECUTED. Run validate_questions.py separately.')


if __name__ == '__main__':
    main()
