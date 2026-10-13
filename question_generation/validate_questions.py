"""Execute and independently verify the curated 50 questions, without DB writes."""
import argparse
import hashlib
import itertools
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_questions import ROOT, assert_quota, quotas
from db_readonly import ReadOnlyDB, TABLE_KEYS, canonical, check_sql, dump
from semantic_oracles import expected

WORKSPACE = ROOT.parent
PROTECTED = ['generate_seed.py', 'postgre/schema_code.sql', 'postgre/constraint.sql',
             'postgre/validate_enterprisedb_br01_br16.sql', 'build/enterprise_seed_data.sql',
             'validate_scenario_coverage.sql']

# Agent design review: the following similar families were compared by actual
# business purpose, grain and simplest solution, rather than signature inequality.
REVIEWED_PAIRS = [
    (7,20,'Danh sách pending để xử lý khác thống kê thời gian xử lý của completed; trạng thái, grain và phép tính đều khác.'),
    (9,21,'Danh bạ LEFT JOIN giữ khách thiếu địa chỉ khác đối chiếu hai vai trò địa chỉ trên đơn và lọc khác city.'),
    (10,45,'Tra tên ở grain dòng hàng khác tổng hợp quý rồi ranking sản phẩm và nhân viên ở hai grain.'),
    (10,11,'Một dòng order_items và lượng hàng đã đặt khác một sản phẩm trong catalog với danh mục trực tiếp; quan hệ và grain khác.'),
    (10,12,'Dòng đơn cần nhãn sản phẩm và thành tiền khác catalog sản phẩm cần liên hệ nguồn cung; không cùng quan hệ hay grain.'),
    (11,12,'Phân loại sản phẩm và trạng thái danh mục phục vụ catalog khác nguồn cung, quốc gia và email phục vụ liên hệ mua hàng; quan hệ category và supplier có mục tiêu khác nhau dù cùng grain sản phẩm.'),
    (11,36,'Tra danh mục trực tiếp khác chọn các mức giá với DENSE_RANK giữ đồng giá.'),
    (12,25,'Tra nguồn cung của từng sản phẩm khác đánh giá độ đa dạng và margin ở nhóm nhà cung cấp.'),
    (13,47,'Quản lý trực tiếp một cấp khác toàn bộ hậu duệ của gốc chỉ định, độ sâu và tổng quỹ lương.'),
    (14,23,'Trưởng phòng ở grain phòng khác đối chiếu quản lý kho với trưởng phòng qua phòng của nhân viên ở grain kho, có so sánh ID và xử lý NULL.'),
    (17,38,'Tổng theo trạng thái khác chuỗi tháng đặt của đơn delivered và thay đổi so với tháng trước.'),
    (18,28,'Tổng biến động theo loại giao dịch khác số tồn cuối theo kho và tỷ lệ sức chứa.'),
    (19,48,'Quỹ lương hiện tại khác bình quân phần lịch sử có bằng chứng theo ngày và đo độ phủ thiếu.'),
    (22,34,'Tiến độ sale từng dòng processing khác đối soát return vật lý với thiếu refund completed ở grain đơn.'),
    (25,33,'Độ đa dạng sản phẩm active theo nhóm khác phép mọi sản phẩm của nhà cung cấp đều active.'),
    (28,46,'Tồn cuối toàn bộ kho khác chuỗi tháng giảm tồn dưới ngưỡng của từng sản phẩm-kho có xét tồn trước kỳ.'),
    (33,41,'Không có sản phẩm inactive khác lượng hóa hai tầng mọi hàng active đã giao và mọi kho đã giao có tồn dương.'),
    (35,36,'Top số đơn cố định, phá hòa theo ngày/ID khác top mức giá khác nhau giữ mọi đồng giá.'),
    (35,42,'Top đơn trong kho khác chọn người thắng tháng rồi phát hiện chuỗi tháng lịch liên tiếp.'),
    (37,50,'Từng mốc LAG khác tìm đoạn tăng tối đa, giữ tiền nhiệm, so tỷ lệ hai đầu và chọn đoạn tốt nhất.'),
    (39,43,'Tổng tiền success lũy kế khác dòng tiền ròng hai nguồn, lịch đầy đủ và top cửa sổ đủ ba tháng.'),
    (42,46,'Chuỗi chiến thắng theo người khác tồn kho tích lũy có ngưỡng và tổng drawdown theo sản phẩm-kho.'),
    (42,50,'Chuỗi tháng lịch thắng xếp hạng khác các cạnh tăng lương liên tiếp và tỷ lệ tăng hai đầu.'),
    (37,48,'Tỷ lệ thay đổi từng mốc khác mức lương áp dụng từng ngày và các khoảng không biết lương.'),
    (38,39,'Biến động giá trị đơn theo order_date khác thực thu thành công lũy kế theo attempted_at.'),
    (46,50,'Đảo tháng giảm tồn lịch đầy đủ khác đoạn mốc lương tăng, tỷ lệ tăng và tiền nhiệm đầu chuỗi.'),
]


def sha(value):
    return hashlib.sha256(dump(value).encode('utf-8')).hexdigest()


def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


def protected_hashes():
    return {name:hashlib.sha256((WORKSPACE/name).read_bytes()).hexdigest() for name in PROTECTED}


def duplicate_review(items):
    pairs = []
    exact = []
    review = {(f'ENT-{a:03d}',f'ENT-{b:03d}'):note for a,b,note in REVIEWED_PAIRS}
    for a,b in itertools.combinations(items,2):
        a_sql,b_sql = check_sql(a['reference_sql']),check_sql(b['reference_sql'])
        same_sql = a_sql==b_sql
        same_signature = a['logic_signature']==b['logic_signature']
        if same_sql or same_signature:
            exact.append([a['question_id'],b['question_id']])
        key = (a['question_id'],b['question_id'])
        common = sorted(set(a['tables_used']) & set(b['tables_used']))
        ta,tb = (set(q['logic_signature']['transformation'].split()) for q in (a,b))
        similarity = len(ta&tb)/len(ta|tb)
        pairs.append({'pair':list(key),'shared_tables':common,
                      'same_grain':a['output_grain']==b['output_grain'],
                      'transformation_token_similarity':round(similarity,4),
                      'exact_sql_match':same_sql,'exact_signature_match':same_signature,
                      'agent_review_note':review.get(key)})
    suspected = [p for p in pairs if p['shared_tables'] and p['transformation_token_similarity']>=0.3]
    unresolved = [p['pair'] for p in suspected if not p['agent_review_note']]
    return {'pair_count':len(pairs),'exact_duplicates':exact,
            'similarity_screen':'Shared table and transformation-token Jaccard >=0.30 flags a pair for agent review; not a proof of duplication.',
            'suspected_pairs':[p['pair'] for p in suspected], 'unresolved_suspected_pairs':unresolved,
            'reviewed_similar_families':[{'pair':[f'ENT-{a:03d}',f'ENT-{b:03d}'],'decision':'DISTINCT','reason':note}
                                        for a,b,note in REVIEWED_PAIRS],
            'review_scope':'Agent design review of all 50 purposes and grains; quantitative scan of all 1225 pairs. No external human review claimed.',
            'pairs':pairs}


def plan_tables(plan):
    found = set()
    def visit(value):
        if isinstance(value,dict):
            if value.get('Schema')=='public' and 'Relation Name' in value:
                found.add(value['Relation Name'])
            for child in value.values():
                visit(child)
        elif isinstance(value,list):
            for child in value:
                visit(child)
    visit(plan)
    return sorted(found)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout-ms',type=int,default=15000)
    args = parser.parse_args()
    if not 100<=args.timeout_ms<=60000:
        parser.error('timeout-ms must be between 100 and 60000')
    candidates = json.loads((ROOT/'questions_candidates.json').read_text(encoding='utf-8'))
    report = {'run_started_at':datetime.now(timezone.utc).isoformat(),'world_id':'enterprise_v1',
              'taxonomy_version':'v1','status':'NOT_EXECUTED','validated_count':0,'rejected_count':0,
              'statement_timeout_ms':args.timeout_ms,'questions':[],
              'runtime_definition':'PostgreSQL statement duration from psql timing; includes JSON result envelope. process_wall_ms also includes process startup and transport.',
              'numeric_samples':'Exact NUMERIC values serialized as decimal strings; counts are JSON integers.',
              'semantic_method':'All result rows, values, NULLs and order compared with independent Python base-table evaluators; not merely a successful SQL execution.',
              'design_review':'Agent review against v1 taxonomy and actual business goals, with independent result evidence. Baseline difficulty is not an empirical learner rating.'}
    report['design_revisions'] = [
        {'question_id':'ENT-046','stage':'blueprint refinement before SQL execution',
         'reason':'Thêm điều kiện tồn cuối <=50 để phải xét tồn tích lũy và tồn trước kỳ; chỉ net movement theo tháng không giải được. Giữ Hard/S6 và Product & Inventory.'},
        {'question_id':'ENT-020','stage':'diversity review after first validation pass',
         'reason':'Thay thống kê số tiền theo refund_status bằng thời gian xử lý completed để giảm lặp hình dạng tổng hợp trạng thái. Giữ Easy/S3 và Finance; chạy kiểm chứng lại.'},
    ]
    history_path = ROOT/'execution_history.json'
    history = json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else []
    previous_report = ROOT/'validation_report.json'
    if not history and previous_report.exists():
        previous = json.loads(previous_report.read_text(encoding='utf-8'))
        history.append({k:previous.get(k) for k in ['run_started_at','run_finished_at','status',
                        'validated_count','rejected_count','candidates_sha256','dataset_fingerprint_before','dataset_fingerprint_after']})
    validated,rejected = [],[]
    try:
        report['quotas_candidates'] = assert_quota(candidates)
        before_files = protected_hashes()
        report['protected_file_hashes_before'] = before_files
        report['rules_sha256'] = hashlib.sha256((WORKSPACE/'question_create/enterprise_50_question_rules_v1.md').read_bytes()).hexdigest()
        report['candidates_sha256'] = hashlib.sha256((ROOT/'questions_candidates.json').read_bytes()).hexdigest()
        duplicates = duplicate_review(candidates)
        write_json('logic_duplicate_review.json',duplicates)
        report['logic_duplicate_review'] = {k:v for k,v in duplicates.items() if k!='pairs'}
        if duplicates['exact_duplicates'] or duplicates['unresolved_suspected_pairs']:
            raise RuntimeError('Duplicate or suspected pairs require review')
        db = ReadOnlyDB(args.timeout_ms)
        report['connection'] = db.identity()
        snapshot = db.snapshot()
        catalog = db.catalog()
        write_json('schema_snapshot.json',catalog)
        report['dataset_fingerprint_before'] = sha(snapshot)
        report['catalog_fingerprint_before'] = sha(catalog)
        report['table_counts'] = {t:len(rows) for t,rows in snapshot.items()}
        summary = json.loads((WORKSPACE/'build/seed_summary.json').read_text(encoding='utf-8'))
        report['counts_match_previous_seed_summary'] = report['table_counts']==summary['table_counts']
        if not report['counts_match_previous_seed_summary']:
            raise RuntimeError('Existing data counts differ from Dataset v1 summary')
        for q in candidates:
            v = {'status':'NOT_EXECUTED','sql_executed':False,'semantic_valid':False,
                 'row_count':None,'runtime_ms':None,'column_types':[], 'result_summary':None,'error':None}
            q = dict(q)
            try:
                check_sql(q['reference_sql'])
                v['column_types'] = db.describe(q['reference_sql'])
                if [col['name'] for col in v['column_types']] != [col['name'] for col in q['output_columns']]:
                    raise ValueError('Output aliases/order differ from question metadata')
                plan,_,_ = db.run('EXPLAIN (FORMAT JSON, VERBOSE) '+q['reference_sql'])
                relations = plan_tables(json.loads(plan,parse_float=float))
                v['plan_relations'] = relations
                if set(relations)!=set(q['tables_used']):
                    raise ValueError(f'Actual plan relations {relations} differ from tables_used {q["tables_used"]}')
                rows,elapsed,wall = db.query(q['reference_sql'])
                v.update(sql_executed=True,row_count=len(rows),runtime_ms=elapsed,process_wall_ms=round(wall,3))
                answer = expected(int(q['question_id'][-3:]),snapshot)
                v['oracle_row_count'] = len(answer)
                v['result_sha256'] = sha(rows)
                v['oracle_sha256'] = sha(answer)
                v['result_summary'] = {'sample_rows':rows[:3],'sample_limit':3}
                if canonical(rows)!=canonical(answer):
                    mismatch = next((i for i,(a,b) in enumerate(zip(rows,answer)) if canonical(a)!=canonical(b)),None)
                    v['first_mismatch'] = {'index':mismatch,
                        'sql_row':rows[mismatch] if mismatch is not None else None,
                        'oracle_row':answer[mismatch] if mismatch is not None else None}
                    raise ValueError('Independent semantic answer does not match SQL result')
                rerun,second_ms,_ = db.query(q['reference_sql'])
                v['repeat_runtime_ms'] = second_ms
                v['repeat_result_sha256'] = sha(rerun)
                v['stable_on_repeat'] = canonical(rows)==canonical(rerun)
                if not v['stable_on_repeat']:
                    raise ValueError('Result/order changed on repeat execution')
                if not rows:
                    raise ValueError('Empty output requires explicit business justification and design review')
                v['semantic_valid'] = True
                v['semantic_evidence'] = 'Complete ordered result equals independent Python evaluator on actual base rows.'
                v['taxonomy_review'] = {'decision':'MATCHES_BASELINE_V1','reason':q['difficulty_reason'],
                                        'primary_skill_group':q['primary_skill_group']}
                v['status'] = 'PASS'
            except Exception as exc:
                v['status'] = 'FAIL' if v['sql_executed'] else 'NOT_EXECUTED'
                v['error'] = str(exc)
            q['validation'] = v
            report['questions'].append({'question_id':q['question_id'],**v})
            (validated if v['status']=='PASS' else rejected).append(q)
            print(f"{q['question_id']} {v['status']} rows={v['row_count']} error={v['error']}",flush=True)
        after_snapshot,after_catalog = db.snapshot(),db.catalog()
        report['dataset_fingerprint_after'] = sha(after_snapshot)
        report['catalog_fingerprint_after'] = sha(after_catalog)
        report['protected_file_hashes_after'] = protected_hashes()
        report['database_rows_unchanged'] = sha(snapshot)==sha(after_snapshot)
        report['database_catalog_unchanged'] = sha(catalog)==sha(after_catalog)
        report['protected_files_unchanged'] = before_files==report['protected_file_hashes_after']
        if not all(report[k] for k in ['database_rows_unchanged','database_catalog_unchanged','protected_files_unchanged']):
            raise RuntimeError('Dataset, schema or protected file changed during validation')
        report['validated_count'],report['rejected_count'] = len(validated),len(rejected)
        report['tables_covered'] = sorted({t for q in validated for t in q['tables_used']})
        report['unused_tables'] = sorted(set(TABLE_KEYS)-set(report['tables_covered']))
        report['zero_row_questions'] = [q['question_id'] for q in validated if q['validation']['row_count']==0]
        if len(validated)==50:
            report['quotas_validated'] = assert_quota(validated)
            report['status'] = 'PASS'
        else:
            report['quotas_validated'] = quotas(validated)
            report['status'] = 'INCOMPLETE'
    except Exception as exc:
        report['status'] = 'NOT_EXECUTED' if not report['questions'] else 'INCOMPLETE'
        report['error'] = str(exc)
        # Preserve honest NOT_EXECUTED entries even on a preflight connection failure.
        recorded = {q['question_id'] for q in validated+rejected}
        for q in candidates:
            if q['question_id'] not in recorded:
                q = dict(q)
                q['validation'] = {**q['validation'],'status':'NOT_EXECUTED','error':str(exc)}
                rejected.append(q)
        if report.get('database_rows_unchanged') is False or report.get('database_catalog_unchanged') is False:
            for q in validated:
                q['validation'].update(status='FAIL',semantic_valid=False,error='Dataset changed during verification')
            rejected.extend(validated)
            validated = []
    report['validated_count'],report['rejected_count'] = len(validated),len(rejected)
    report['run_finished_at'] = datetime.now(timezone.utc).isoformat()
    write_json('questions_validated.json',validated)
    write_json('questions_rejected.json',rejected)
    write_json('validation_report.json',report)
    history.append({k:report.get(k) for k in ['run_started_at','run_finished_at','status',
                    'validated_count','rejected_count','candidates_sha256','dataset_fingerprint_before','dataset_fingerprint_after']})
    write_json('execution_history.json',history)
    print(f"Final: {report['status']} {len(validated)}/50 validated; {len(rejected)} rejected")
    if report.get('error'):
        print(report['error'])
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
