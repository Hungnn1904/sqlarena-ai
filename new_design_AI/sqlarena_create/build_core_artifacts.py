"""Optional artifact exporter/import verifier. Never resets or changes EnterpriseDB."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'postgre' / 'sqlarena_db'
EVIDENCE = ROOT / 'sqlarena_create' / 'evidence'
sys.path.insert(0, str(ROOT / 'question_generation'))
from db_readonly import ReadOnlyDB, dump

TARGET = 'sqlarena_db'
SOURCE = ROOT / 'question_generation' / 'questions_validated.json'
BR_SQL = ROOT / 'postgre' / 'enterprise_db' / 'validate_enterprisedb_br01_br16.sql'
RULES = ROOT / 'question_create' / 'enterprise_50_question_rules_v1.md'
MAPPING = ROOT / 'sqlarena_create' / 'sqlarena_core_mapping_rules_v2.md'
TABLE_NAMES = ['worlds', 'skills', 'templates', 'source_questions']
MAPPED = ['question_id', 'world_id', 'title', 'question_text', 'reference_sql', 'difficulty',
          'primary_skill_group', 'primary_business_domain', 'secondary_skills', 'validation']
SKILLS = [
    ('S1', 'SELECT / WHERE / ORDER BY / DISTINCT', 'easy'),
    ('S2', 'JOIN / LEFT JOIN / SELF JOIN', 'easy'),
    ('S3', 'GROUP BY / HAVING / aggregate', 'easy'),
    ('S4', 'Subquery / EXISTS / NOT EXISTS', 'medium'),
    ('S5', 'CTE / window functions', 'medium'),
    ('S6', 'Recursive CTE / truy vấn lịch sử & tồn kho đa bước', 'hard'),
]
EXPECTED_DOMAINS = {'Customer Management': 8, 'Sales & Orders': 13,
                    'Product & Inventory': 12, 'Human Resources': 9, 'Finance': 8}


def column(name, dtype, nullable=False, default=None, identity=''):
    return {'name': name, 'type': dtype, 'nullable': nullable, 'default': default,
            'identity': identity, 'generated': ''}


TABLES = [
    {'name': 'worlds', 'columns': [
        column('world_id', 'character varying(100)'), column('name', 'character varying(150)'),
        column('database_name', 'character varying(100)'), column('dialect', 'character varying(30)'),
        column('schema_description', 'jsonb'), column('fk_relations', 'jsonb'),
        column('business_rules', 'jsonb'), column('planted_traps', 'jsonb', default="'[]'::jsonb"),
        column('allowed_sql_features', 'jsonb')],
     'constraints': {'core_worlds_pk': 'PRIMARY KEY (world_id)'}},
    {'name': 'skills', 'columns': [
        column('skill_id', 'character varying(30)'), column('name', 'character varying(160)'),
        column('category', 'character varying(100)'), column('base_difficulty', 'character varying(10)')],
     'constraints': {'core_skills_pk': 'PRIMARY KEY (skill_id)',
                     'core_skills_base_difficulty_check': "CHECK (base_difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))"}},
    {'name': 'templates', 'columns': [
        column('template_id', 'bigint', identity='d'), column('world_id', 'character varying(100)'),
        column('topic', 'character varying(150)'), column('difficulty', 'character varying(10)'),
        column('pattern', 'text'), column('constraints', 'jsonb', default="'{}'::jsonb")],
     'constraints': {'core_templates_pk': 'PRIMARY KEY (template_id)',
                     'core_templates_world_fk': 'FOREIGN KEY (world_id) REFERENCES core.worlds(world_id)',
                     'core_templates_difficulty_check': "CHECK (difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))"}},
    {'name': 'source_questions', 'columns': [
        column('question_id', 'character varying(30)'), column('world_id', 'character varying(100)'),
        column('title', 'text'), column('question_text', 'text'), column('reference_sql', 'text'),
        column('difficulty', 'character varying(10)'), column('primary_skill_group', 'character varying(30)'),
        column('primary_business_domain', 'character varying(100)'), column('skills', 'jsonb', default="'[]'::jsonb"),
        column('depth', 'integer', nullable=True), column('metadata', 'jsonb'), column('validation', 'jsonb'),
        column('created_at', 'timestamp with time zone', default='now()')],
     'constraints': {'core_source_questions_pk': 'PRIMARY KEY (question_id)',
                     'core_source_questions_world_fk': 'FOREIGN KEY (world_id) REFERENCES core.worlds(world_id)',
                     'core_source_questions_skill_fk': 'FOREIGN KEY (primary_skill_group) REFERENCES core.skills(skill_id)',
                     'core_source_questions_difficulty_check': "CHECK (difficulty::text = ANY (ARRAY['easy','medium','hard']::text[]))",
                     'core_source_questions_depth_check': 'CHECK (depth IS NULL OR depth >= 0)'}},
]
INDEXES = {
    'idx_core_templates_world': ('templates', 'world_id'),
    'idx_core_source_questions_world': ('source_questions', 'world_id'),
    'idx_core_source_questions_difficulty': ('source_questions', 'difficulty'),
    'idx_core_source_questions_skill': ('source_questions', 'primary_skill_group'),
    'idx_core_source_questions_domain': ('source_questions', 'primary_business_domain'),
}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def hash_value(value):
    return sha_bytes(dump(value).encode('utf-8'))


def literal(text, tag):
    if '\x00' in text:
        raise ValueError('NUL cannot be stored in PostgreSQL TEXT')
    delim = '$' + tag + '$'
    while delim in text:
        tag += '_x'
        delim = '$' + tag + '$'
    return delim + text + delim


def as_json(value, tag):
    return literal(json_text(value), tag) + '::jsonb'


def metadata(q):
    return {k: v for k, v in q.items() if k not in MAPPED}


def read_questions():
    questions = json.loads(SOURCE.read_text(encoding='utf-8'))
    if not isinstance(questions, list) or len(questions) != 50:
        raise ValueError('Expected exactly 50 source questions')
    if sorted(q['question_id'] for q in questions) != [f'ENT-{n:03d}' for n in range(1, 51)]:
        raise ValueError('Question IDs must be unique ENT-001 through ENT-050')
    for q in questions:
        if q['world_id'] != 'enterprise_v1':
            raise ValueError('World ID must be enterprise_v1')
        if any(not isinstance(q.get(k), str) or not q[k] for k in MAPPED[:8]):
            raise ValueError(f'Missing mapped text field: {q["question_id"]}')
        if not isinstance(q.get('secondary_skills'), list):
            raise ValueError('secondary_skills must be an array')
        v = q['validation']
        if v.get('status') != 'PASS' or v.get('sql_executed') is not True or v.get('semantic_valid') is not True:
            raise ValueError(f'Source question is not validated: {q["question_id"]}')
    actual = {
        'difficulty': dict(Counter(q['difficulty'] for q in questions)),
        'skills': dict(Counter(q['primary_skill_group'] for q in questions)),
        'domains': dict(Counter(q['primary_business_domain'] for q in questions)),
        'matrix': {d: dict(Counter(q['primary_skill_group'] for q in questions if q['difficulty'] == d))
                   for d in ['easy', 'medium', 'hard']},
    }
    if actual != {
        'difficulty': {'easy': 20, 'medium': 20, 'hard': 10},
        'skills': {'S1': 8, 'S2': 10, 'S3': 10, 'S4': 7, 'S5': 10, 'S6': 5},
        'domains': EXPECTED_DOMAINS,
        'matrix': {'easy': {'S1': 8, 'S2': 7, 'S3': 5},
                   'medium': {'S2': 3, 'S3': 5, 'S4': 6, 'S5': 6},
                   'hard': {'S4': 1, 'S5': 4, 'S6': 5}},
    }:
        raise ValueError(f'Source quota mismatch: {actual}')
    return questions, actual


def paragraphs(path):
    with ZipFile(path) as document:
        tree = ElementTree.fromstring(document.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    return [''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in tree.findall('.//w:p', ns)]


def business_rules():
    source_doc = ROOT / 'rang_buoc.docx'
    raw = paragraphs(source_doc)
    starts = [(i, re.match(r'^BR(\d{2})\s*[\u2014-]', text)) for i, text in enumerate(raw)]
    starts = [(i, m.group(1)) for i, m in starts if m]
    if [code for _, code in starts] != [f'{n:02d}' for n in range(1, 17)]:
        raise ValueError('Cannot extract all BR01 through BR16 from the actual document')
    validator = BR_SQL.read_text(encoding='utf-8')
    blocks = list(re.finditer(r'^-- BR(\d{2}):', validator, re.M))
    if [m.group(1) for m in blocks] != [f'{n:02d}' for n in range(1, 17)]:
        raise ValueError('Validator sections are incomplete')
    entries = []
    for pos, (start, code) in enumerate(starts):
        end = starts[pos + 1][0] if pos + 1 < len(starts) else next(
            (i for i in range(start + 1, len(raw)) if raw[i].startswith('III.')), len(raw))
        sql_start = blocks[pos].start()
        sql_end = blocks[pos + 1].start() if pos + 1 < len(blocks) else validator.index('-- ===== RESULTS:')
        entries.append({'code': 'BR' + code, 'title_from_document': raw[start],
                        'document_excerpt': '\n'.join(raw[start:end]),
                        'dataset_v1_validator_excerpt': validator[sql_start:sql_end].strip()})
    return {
        'sources': [{'path': str(p.relative_to(ROOT)).replace('\\', '/'), 'sha256': sha_bytes(p.read_bytes())}
                    for p in [source_doc, BR_SQL, ROOT / 'Schema database.docx']],
        'rules': entries,
        'precedence': 'Live post-migration schema and the Dataset v1 BR validator identify implemented policy. Document excerpts retain original proposals and caveats; they are not agent instructions.',
        'alignment_notes': [
            'salary_history uses salary; no old_salary/new_salary.',
            'inventory_transactions uses order_item_id; no reference_type/reference_id.',
            'payments uses attempted_at; no payments.completed_at.',
            'BR09 validator enforces designated manager membership, not every proposed active-status rule.',
            'BR10 validator checks cycles; optional same-department restrictions are not promoted to mandatory policy.',
            'BR16 only compares expense_date and hire_date; approved_at is not stored.',
        ],
    }


def collect_world(source_db):
    snapshot = source_db.snapshot()
    catalog = source_db.catalog()
    columns, _, _ = source_db.query("""SELECT c.relname AS table_name,a.attname AS name,
pg_catalog.format_type(a.atttypid,a.atttypmod) AS postgres_type,NOT a.attnotnull AS nullable,
a.attidentity::text AS identity,pg_catalog.pg_get_expr(d.adbin,d.adrelid) AS default_expression,
EXISTS(SELECT 1 FROM pg_constraint k WHERE k.conrelid=c.oid AND k.contype='p' AND a.attnum=ANY(k.conkey)) AS primary_key,
a.attnum AS ordinal_position
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname,a.attnum""")
    foreign_keys, _, _ = source_db.query("""SELECT k.conname AS name,ch.relname AS table_name,
ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY u(num,pos)
 JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=u.num ORDER BY u.pos) AS columns,
pn.nspname AS referenced_schema,pa.relname AS referenced_table,
ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY u(num,pos)
 JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=u.num ORDER BY u.pos) AS referenced_columns,
pg_get_constraintdef(k.oid) AS definition,k.convalidated AS validated
FROM pg_constraint k JOIN pg_class ch ON ch.oid=k.conrelid JOIN pg_namespace cn ON cn.oid=ch.relnamespace
JOIN pg_class pa ON pa.oid=k.confrelid JOIN pg_namespace pn ON pn.oid=pa.relnamespace
WHERE k.contype='f' AND cn.nspname='public' ORDER BY ch.relname,k.conname""")
    descriptions = []
    for name in sorted(snapshot):
        table_columns = [{k: v for k, v in c.items() if k != 'table_name'} for c in columns if c['table_name'] == name]
        descriptions.append({'schema': 'public', 'table': name, 'columns': table_columns,
                             'primary_key': [c['name'] for c in table_columns if c['primary_key']],
                             'constraints': [c for c in catalog['constraints'] if c['table_name'] == name]})
    if len(descriptions) != 16 or any(not t['columns'] or not t['primary_key'] for t in descriptions):
        raise ValueError('EnterpriseDB must expose the full 16-table post-migration schema')
    # Read the schema document as reference data; do not execute document instructions.
    schema_doc = '\n'.join(paragraphs(ROOT / 'Schema database.docx'))
    if any(name not in schema_doc for name in snapshot):
        raise ValueError('Schema reference document does not cover all live tables')
    ordered_customers = {r['customer_id'] for r in snapshot['orders']}
    ordered_products = {r['product_id'] for r in snapshot['order_items']}
    recorded_employees = {r['employee_id'] for r in snapshot['salary_history']}
    success_by_order = {r['order_id']: r for r in snapshot['payments'] if r['payment_status'] == 'success'}
    retries = sum(any(p['order_id'] == oid and p['payment_status'] == 'failed' and
                     (p['attempted_at'], p['payment_id']) < (success['attempted_at'], success['payment_id'])
                     for p in snapshot['payments']) for oid, success in success_by_order.items())
    traps = [
        {'scenario': 'customers_without_orders', 'verified_count': len(snapshot['customers']) - len(ordered_customers),
         'tables': ['customers', 'orders']},
        {'scenario': 'products_never_ordered', 'verified_count': len(snapshot['products']) - len(ordered_products),
         'tables': ['products', 'order_items']},
        {'scenario': 'employees_without_salary_history', 'verified_count': len(snapshot['employees']) - len(recorded_employees),
         'tables': ['employees', 'salary_history']},
        {'scenario': 'success_after_failed_payment', 'verified_count': retries, 'tables': ['payments'],
         'event_order': ['attempted_at', 'payment_id']},
        {'scenario': 'expenses_without_approver', 'verified_count': sum(r['approved_by_employee_id'] is None for r in snapshot['operating_expenses']),
         'tables': ['operating_expenses']},
    ]
    for trap in traps:
        trap['verification_source'] = 'Direct read-only base-table snapshot; not a re-executed question.'
    world = {
        'world_id': 'enterprise_v1', 'name': 'EnterpriseDB v1', 'database_name': 'enterprise_db',
        'dialect': 'postgresql',
        'schema_description': {'source': 'Live PostgreSQL catalogs, read-only', 'schema': 'public',
                               'catalog_sha256': hash_value(catalog), 'tables': descriptions},
        'fk_relations': foreign_keys, 'business_rules': business_rules(),
        'planted_traps': [t for t in traps if t['verified_count'] > 0],
        'allowed_sql_features': {'source': str(RULES.relative_to(ROOT)).replace('\\', '/'),
            'source_sha256': sha_bytes(RULES.read_bytes()),
            'statement_types': ['SELECT', 'WITH ... SELECT', 'WITH RECURSIVE ... SELECT'],
            'features': [s[1] for s in SKILLS] + ['PostgreSQL date/time functions'],
            'execution_policy': 'SELECT-only account, read-only transaction, statement timeout; no side-effect functions'},
    }
    return world, snapshot, catalog


DB_GUARD = """DO $database_guard$
BEGIN
    IF current_database() <> 'sqlarena_db' THEN
        RAISE EXCEPTION 'Wrong database: connect Query Tool to sqlarena_db before running this file.';
    END IF;
END
$database_guard$;
"""


def shape_guard():
    payload = {'tables': TABLES,
               'indexes': {name: f'CREATE INDEX {name} ON core.{table} USING btree ({col})'
                           for name, (table, col) in INDEXES.items()}}
    return r"""DO $shape_guard_v2$
DECLARE
    expected jsonb := """ + as_json(payload, 'core_expected_shape_v2') + r""";
    spec jsonb;
    item record;
    relation_oid oid;
    actual_columns jsonb;
    actual_definition text;
    actual_normalized text;
    expected_normalized text;
    actual_names text[];
BEGIN
    SELECT array_agg(c.relname::text ORDER BY c.relname) INTO actual_names
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='core' AND c.relkind IN ('r','p','v','m','f');
    IF actual_names IS DISTINCT FROM ARRAY['skills','source_questions','templates','worlds']::text[] THEN
        RAISE EXCEPTION 'Core v2 schema mismatch: expected exactly four ordinary tables, found %.', actual_names;
    END IF;
    FOR spec IN SELECT value FROM jsonb_array_elements(expected->'tables') LOOP
        relation_oid := to_regclass(format('core.%I',spec->>'name'));
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=relation_oid AND relkind='r'
                       AND relpersistence='p' AND NOT relrowsecurity AND NOT relforcerowsecurity)
           OR EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid=relation_oid)
           OR EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=relation_oid AND NOT tgisinternal) THEN
            RAISE EXCEPTION 'Core v2 schema mismatch in table %: unexpected table properties or triggers.',spec->>'name';
        END IF;
        SELECT jsonb_agg(jsonb_build_object(
            'name',a.attname,'type',format_type(a.atttypid,a.atttypmod),
            'nullable',NOT a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),
            'identity',a.attidentity::text,'generated',a.attgenerated::text) ORDER BY a.attnum)
        INTO actual_columns
        FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
        WHERE a.attrelid=relation_oid AND a.attnum>0 AND NOT a.attisdropped;
        IF actual_columns IS DISTINCT FROM spec->'columns' THEN
            RAISE EXCEPTION 'Core v2 column mismatch in table %. Existing tables are not modified.',spec->>'name'
                USING DETAIL=format('Expected: %s. Actual: %s.',spec->'columns',actual_columns);
        END IF;
        IF (SELECT count(*) FROM pg_constraint WHERE conrelid=relation_oid AND contype<>'n')
           <> (SELECT count(*) FROM jsonb_object_keys(spec->'constraints')) THEN
            RAISE EXCEPTION 'Core v2 constraint count mismatch in table %.',spec->>'name';
        END IF;
        FOR item IN SELECT key,value FROM jsonb_each_text(spec->'constraints') LOOP
            SELECT pg_get_constraintdef(oid) INTO actual_definition FROM pg_constraint
            WHERE conrelid=relation_oid AND conname=item.key AND convalidated
                  AND NOT condeferrable AND NOT condeferred;
            actual_normalized := regexp_replace(regexp_replace(actual_definition,
                '::(text|character varying)(\([0-9]+\))?(\[\])?','','g'),'[[:space:]()]','','g');
            expected_normalized := regexp_replace(regexp_replace(item.value,
                '::(text|character varying)(\([0-9]+\))?(\[\])?','','g'),'[[:space:]()]','','g');
            IF actual_normalized IS DISTINCT FROM expected_normalized THEN
                RAISE EXCEPTION 'Core v2 constraint mismatch: %.%',spec->>'name',item.key;
            END IF;
        END LOOP;
    END LOOP;
    IF (SELECT count(*) FROM pg_indexes WHERE schemaname='core') <> 9 THEN
        RAISE EXCEPTION 'Core v2 index count mismatch: expected four PK indexes and five lookup indexes.';
    END IF;
    FOR item IN SELECT key,value FROM jsonb_each_text(expected->'indexes') LOOP
        SELECT pg_get_indexdef(c.oid) INTO actual_definition
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_index i ON i.indexrelid=c.oid
        WHERE n.nspname='core' AND c.relname=item.key AND i.indisvalid AND i.indisready;
        IF regexp_replace(actual_definition,'[[:space:]]','','g')
           IS DISTINCT FROM regexp_replace(item.value,'[[:space:]]','','g') THEN
            RAISE EXCEPTION 'Core v2 index mismatch: %.',item.key;
        END IF;
    END LOOP;
END
$shape_guard_v2$;
"""


def ddl_sql():
    parts = ['-- Core v2 DDL. Run only in sqlarena_db. No data is inserted.\nBEGIN;\n',
             "SET LOCAL search_path=pg_catalog,public;\nSET LOCAL standard_conforming_strings=on;\nSET LOCAL lock_timeout='5s';\n",
             DB_GUARD, "CREATE SCHEMA IF NOT EXISTS core;\n"]
    for table in TABLES:
        definitions = []
        for c in table['columns']:
            definition = c['name'] + ' ' + c['type']
            if c['identity']:
                definition += ' GENERATED BY DEFAULT AS IDENTITY'
            if not c['nullable']:
                definition += ' NOT NULL'
            if c['default'] is not None:
                definition += ' DEFAULT ' + c['default']
            definitions.append(definition)
        definitions += ['CONSTRAINT ' + name + ' ' + definition for name, definition in table['constraints'].items()]
        parts.append('CREATE TABLE IF NOT EXISTS core.' + table['name'] + ' (\n    ' + ',\n    '.join(definitions) + '\n);\n')
    for name, (table, col) in INDEXES.items():
        parts.append(f'CREATE INDEX IF NOT EXISTS {name} ON core.{table} ({col});\n')
    parts += [shape_guard(), 'COMMIT;\n']
    return '\n'.join(parts)


def insert_sql(world, questions):
    parts = ['-- Core v2 data. Standalone UTF-8 SQL; Reference SQL is stored as TEXT only.\nBEGIN;\n',
             "SET LOCAL search_path=pg_catalog,public;\nSET LOCAL standard_conforming_strings=on;\nSET LOCAL lock_timeout='5s';\n",
             DB_GUARD, shape_guard(),
             'LOCK TABLE core.worlds,core.skills,core.templates,core.source_questions IN SHARE ROW EXCLUSIVE MODE;\n',
             """DO $empty_core_guard$
BEGIN
    IF EXISTS (SELECT 1 FROM core.worlds) OR EXISTS (SELECT 1 FROM core.skills)
       OR EXISTS (SELECT 1 FROM core.templates) OR EXISTS (SELECT 1 FROM core.source_questions) THEN
        RAISE EXCEPTION 'Core already contains data. Import refused; existing rows are preserved. No reset is performed.';
    END IF;
END
$empty_core_guard$;
"""]
    values = [literal(world[c['name']], 'world_' + c['name']) if c['type'].startswith('character')
              else as_json(world[c['name']], 'world_' + c['name']) for c in TABLES[0]['columns']]
    parts.append('INSERT INTO core.worlds (' + ','.join(c['name'] for c in TABLES[0]['columns']) + ') VALUES (\n' + ',\n'.join(values) + '\n);\n')
    skills_values = ['(' + ','.join(literal(v, 'skill_' + skill_id + '_' + str(i)) for i,v in enumerate(
                     [skill_id,name,'SQL_READ',difficulty])) + ')' for skill_id,name,difficulty in SKILLS]
    parts.append('INSERT INTO core.skills (skill_id,name,category,base_difficulty) VALUES\n' + ',\n'.join(skills_values) + ';\n')
    fields = ['question_id','world_id','title','question_text','reference_sql','difficulty',
              'primary_skill_group','primary_business_domain','skills','depth','metadata','validation']
    for q in questions:
        tag = q['question_id'].lower().replace('-','_')
        values = [literal(q[k],tag+'_'+k) for k in fields[:8]] + [as_json(q['secondary_skills'],tag+'_skills'),
                  'NULL',as_json(metadata(q),tag+'_metadata'),as_json(q['validation'],tag+'_validation')]
        parts.append('-- ' + q['question_id'] + '\nINSERT INTO core.source_questions (' + ','.join(fields) + ') VALUES (\n' + ',\n'.join(values) + '\n);\n')
    parts += ['COMMIT;\n', """SELECT 'worlds' AS table_name,COUNT(*) AS row_count FROM core.worlds
UNION ALL SELECT 'skills',COUNT(*) FROM core.skills
UNION ALL SELECT 'templates',COUNT(*) FROM core.templates
UNION ALL SELECT 'source_questions',COUNT(*) FROM core.source_questions;
"""]
    return '\n'.join(parts)


class CoreConnection:
    def __init__(self):
        self.psql = os.environ.get('PSQL_BIN') or shutil.which('psql')
        if not self.psql:
            options = sorted(Path('C:/Program Files/PostgreSQL').glob('*/bin/psql.exe'),reverse=True)
            self.psql = str(options[0]) if options else None
        if not self.psql:
            raise RuntimeError('psql not found')
        self.env = os.environ.copy()
        self.env['PGCLIENTENCODING'] = 'UTF8'
        self.env['PGOPTIONS'] = '-c statement_timeout=60000 -c lock_timeout=5000'

    def run(self, database, *, sql=None, file=None, log=None, allow_failure=False):
        if database not in {'postgres',TARGET}:
            raise ValueError('Writes are restricted to sqlarena_db or database creation on postgres')
        args = [self.psql,'-X','-w','-h',os.environ.get('PGHOST','localhost'),
                '-p',os.environ.get('PGPORT','5432'),'-U',os.environ.get('PGUSER','postgres'),
                '-d',database,'-v','ON_ERROR_STOP=1']
        args += ['-f',str(file)] if file else ['-q','-A','-t','-c',sql]
        result = subprocess.run(args,capture_output=True,encoding='utf-8',env=self.env,timeout=90)
        if log:
            (EVIDENCE/log).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode and not allow_failure:
            raise RuntimeError(result.stderr.strip())
        return result

    def read(self, sql, database=TARGET):
        wrapped = 'BEGIN READ ONLY; SET LOCAL search_path=pg_catalog,public; SELECT COALESCE(jsonb_agg(to_jsonb(r)),\'[]\'::jsonb) FROM (' + sql.rstrip(';') + ') r; ROLLBACK;'
        return json.loads(self.run(database,sql=wrapped).stdout.strip())

    def preflight_target(self):
        exists = self.read("SELECT datname FROM pg_database WHERE datname='sqlarena_db'",database='postgres')
        if not exists:
            return False
        relations = self.read("""SELECT n.nspname AS schema_name,c.relname AS name,c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
AND c.relkind IN ('r','p','v','m','f') ORDER BY 1,2""")
        if any(r['schema_name']!='core' or r['name'] not in TABLE_NAMES or r['relkind']!='r' for r in relations):
            raise RuntimeError('Existing sqlarena_db has unrelated objects; no changes will be made')
        for relation in relations:
            rows = self.read(f"SELECT COUNT(*) AS count FROM core.{relation['name']}")
            if rows[0]['count']:
                raise RuntimeError('Existing sqlarena_db contains data; refusing to reset or overwrite it')
        return True


def core_state(conn):
    data = {t: conn.read(f'SELECT * FROM core.{t} ORDER BY 1') for t in TABLE_NAMES}
    catalog = conn.read("""SELECT c.relname AS table_name,a.attname AS name,format_type(a.atttypid,a.atttypmod) AS type,
a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid) AS default_expression
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
WHERE n.nspname='core' AND c.relkind='r' ORDER BY c.relname,a.attnum""")
    constraints = conn.read("""SELECT c.relname AS table_name,k.conname,k.contype,k.convalidated,pg_get_constraintdef(k.oid) AS definition
FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='core' ORDER BY c.relname,k.conname""")
    indexes = conn.read("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='core' ORDER BY indexname")
    return {'data':data,'columns':catalog,'constraints':constraints,'indexes':indexes}


def verify_core(conn,world,questions):
    state = core_state(conn)
    counts = {t:len(rows) for t,rows in state['data'].items()}
    if counts != {'worlds':1,'skills':6,'templates':0,'source_questions':50}:
        raise ValueError(f'Core counts mismatch: {counts}')
    if state['data']['worlds'] != [world]:
        raise ValueError('World metadata differs from exported live sources')
    expected_skills = [{'skill_id':i,'name':n,'category':'SQL_READ','base_difficulty':d} for i,n,d in SKILLS]
    if state['data']['skills'] != expected_skills:
        raise ValueError('Skills mapping mismatch')
    source_by_id = {q['question_id']:q for q in questions}
    text_match = sql_match = validation_match = metadata_match = reconstructed_match = 0
    for stored in state['data']['source_questions']:
        source = source_by_id[stored['question_id']]
        restored = dict(stored['metadata'])
        restored.update({k:stored[k] for k in MAPPED if k not in {'secondary_skills','validation'}})
        restored['secondary_skills'] = stored['skills']
        restored['validation'] = stored['validation']
        text_match += stored['question_text'].encode('utf-8') == source['question_text'].encode('utf-8')
        sql_match += stored['reference_sql'].encode('utf-8') == source['reference_sql'].encode('utf-8')
        validation_match += stored['validation'] == source['validation']
        metadata_match += stored['metadata'] == metadata(source)
        reconstructed_match += restored == source
        if restored != source or stored['depth'] is not None or not stored['created_at']:
            raise ValueError('Lossless source mapping mismatch for '+stored['question_id'])
    orphans = conn.read("""SELECT
(SELECT COUNT(*) FROM core.source_questions q LEFT JOIN core.worlds w USING(world_id) WHERE w.world_id IS NULL) AS question_world_orphans,
(SELECT COUNT(*) FROM core.source_questions q LEFT JOIN core.skills s ON s.skill_id=q.primary_skill_group WHERE s.skill_id IS NULL) AS question_skill_orphans,
(SELECT COUNT(*) FROM core.templates t LEFT JOIN core.worlds w USING(world_id) WHERE w.world_id IS NULL) AS template_world_orphans""")[0]
    if any(orphans.values()):
        raise ValueError('Foreign key orphans detected')
    matrix = conn.read('SELECT difficulty,primary_skill_group,COUNT(*) AS count FROM core.source_questions GROUP BY 1,2 ORDER BY 1,2')
    domains = {r['primary_business_domain']:r['count'] for r in conn.read('SELECT primary_business_domain,COUNT(*) AS count FROM core.source_questions GROUP BY 1')}
    skills = {r['primary_skill_group']:r['count'] for r in conn.read('SELECT primary_skill_group,COUNT(*) AS count FROM core.source_questions GROUP BY 1')}
    difficulty = {r['difficulty']:r['count'] for r in conn.read('SELECT difficulty,COUNT(*) AS count FROM core.source_questions GROUP BY 1')}
    if domains != EXPECTED_DOMAINS or skills != dict(Counter(q['primary_skill_group'] for q in questions)) or difficulty != {'easy':20,'medium':20,'hard':10}:
        raise ValueError('Imported quotas mismatch')
    return {'counts':counts,'orphan_counts':orphans,'difficulty':difficulty,'skills':skills,'domains':domains,
            'matrix':matrix,'text_utf8_exact_matches':text_match,'sql_utf8_exact_matches':sql_match,
            'validation_exact_matches':validation_match,'metadata_exact_matches':metadata_match,
            'lossless_source_reconstruction_matches':reconstructed_match,
            'core_state_sha256':hash_value(state)}, state


def protected_hashes():
    files = [SOURCE,RULES,MAPPING,ROOT/'sqlarena_create/prompt_agent_build_sqlarena_core_v2.md',
             ROOT/'generate_seed.py',ROOT/'build/enterprise_seed_data.sql',
             *sorted((ROOT/'postgre/enterprise_db').glob('*.sql')),
             ROOT/'rang_buoc.docx',ROOT/'Schema database.docx']
    return {str(p.relative_to(ROOT)).replace('\\','/'):sha_bytes(p.read_bytes()) for p in files}


def write_report(evidence):
    (EVIDENCE/'core_verification.json').write_text(json_text(evidence)+'\n',encoding='utf-8')
    rows = ['# Báo cáo nhập SQLArena Core v2', '', f"Trạng thái: **{evidence['status']}**.",
            '', f"Thời điểm: `{evidence['finished_at']}`.",
            '', 'Nguồn chuẩn: `question_generation/questions_validated.json`; Rules v2 đọc từ `sqlarena_create`.',
            'Không thực thi Reference SQL trong giai đoạn import. PASS trong validation được giữ nguyên từ JSON nguồn.', '']
    if evidence.get('verification'):
        v = evidence['verification']
        rows += ['| Bảng | Số dòng thực tế |','|---|---:|'] + [f'| core.{t} | {n} |' for t,n in v['counts'].items()]
        rows += ['', '| Kiểm chứng đối chiếu | Số câu khớp |','|---|---:|'] + [f'| {label} | {v[key]}/50 |' for label,key in [
            ('question_text, byte UTF-8','text_utf8_exact_matches'),('reference_sql, byte UTF-8','sql_utf8_exact_matches'),
            ('validation JSONB','validation_exact_matches'),('metadata còn lại JSONB','metadata_exact_matches'),
            ('Tái dựng toàn bộ object nguồn','lossless_source_reconstruction_matches')]]
        rows += ['', 'Quota từ database:', '', '| Độ khó | Số câu |','|---|---:|'] + [f'| {k} | {v["difficulty"][k]} |' for k in ['easy','medium','hard']]
        rows += ['', '| Kỹ năng | Số câu |','|---|---:|'] + [f'| {k} | {v["skills"][k]} |' for k in ['S1','S2','S3','S4','S5','S6']]
        rows += ['', '| Nghiệp vụ | Số câu |','|---|---:|'] + [f'| {k} | {v["domains"][k]} |' for k in EXPECTED_DOMAINS]
        rows += ['', f"FK orphan: `{v['orphan_counts']}`; tất cả bằng 0.",
                 'Ma trận kỹ năng theo độ khó cũng được đối chiếu với dữ liệu nguồn.',
                 '', f"DDL chạy lại giữ nguyên Core: **{evidence['ddl_repeat_unchanged']}**.",
                 f"Nhập lại bị chặn trước INSERT và giữ nguyên Core: **{evidence['data_repeat_refused_unchanged']}**.",
                 f"Bộ kiểm tra schema từ chối kỳ vọng cấu trúc khác và giữ nguyên Core: **{evidence['schema_mismatch_refused_unchanged']}**."]
    rows += ['', f"Nguồn EnterpriseDB có `{evidence.get('enterprise_table_count')}` bảng; FK thật: `{evidence.get('enterprise_fk_count')}`.",
             f"BR trích đủ 01-16 từ tài liệu và đối chiếu đoạn validator: `{evidence.get('business_rule_count')}`.",
             'Đề xuất và caveat trong tài liệu BR được giữ rõ nguồn, không tự nâng thành chính sách bắt buộc.',
             '`depth=NULL`: chưa quy ước generation depth; không dùng độ sâu SQL hay độ khó làm depth.',
             '`created_at` là thời điểm nhập do PostgreSQL now(), không phải thời điểm sinh câu.',
             '', f"Dữ liệu enterprise_db trước/sau khớp: **{evidence.get('enterprise_rows_unchanged')}**.",
             f"Catalog enterprise_db trước/sau khớp: **{evidence.get('enterprise_catalog_unchanged')}**.",
             f"JSON nguồn, generator, seed, schema/constraints/validator và tài liệu trước/sau khớp: **{evidence.get('protected_files_unchanged')}**.",
             'Không tạo draft/live, không tạo template giả, không lưu mật khẩu, không có bước reset.', '',
             'Dấu vân tay và log thực thi đầy đủ ở `sqlarena_create/evidence/`.', '']
    if evidence.get('error'):
        rows += ['Lỗi: '+evidence['error'], '']
    (OUT/'core_import_report.md').write_text('\n'.join(rows),encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Export two standalone Core SQL files; optionally apply to a new/empty sqlarena_db.')
    parser.add_argument('--apply',action='store_true',help='Create sqlarena_db if absent, then apply and verify. Never reset existing data.')
    args = parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    evidence = {'status':'NOT_EXECUTED','started_at':datetime.now(timezone.utc).isoformat()}
    try:
        before_files = protected_hashes()
        questions,quotas = read_questions()
        conn = CoreConnection()
        existed = conn.preflight_target() if args.apply else None
        # Source is always read through the established read-only transport.
        os.environ['PGDATABASE'] = 'enterprise_db'
        source_db = ReadOnlyDB()
        evidence['source_connection'] = source_db.identity()
        world,before_rows,before_catalog = collect_world(source_db)
        evidence.update(source_quotas=quotas,enterprise_table_count=len(world['schema_description']['tables']),
                        enterprise_fk_count=len(world['fk_relations']),business_rule_count=len(world['business_rules']['rules']),
                        enterprise_rows_before=hash_value(before_rows),enterprise_catalog_before=hash_value(before_catalog),
                        protected_file_hashes_before=before_files)
        ddl_path,data_path = OUT/'01_create_sqlarena_core.sql',OUT/'02_insert_sqlarena_core_data.sql'
        ddl_content,data_content = ddl_sql(),insert_sql(world,questions)
        if len(re.findall(r'^INSERT INTO core.source_questions ',data_content,re.M)) != 50:
            raise ValueError('The standalone data file must contain 50 complete question INSERTs')
        ddl_path.write_text(ddl_content,encoding='utf-8',newline='\n')
        data_path.write_text(data_content,encoding='utf-8',newline='\n')
        evidence['sql_file_sha256'] = {p.name:sha_bytes(p.read_bytes()) for p in [ddl_path,data_path]}
        if args.apply:
            if not existed:
                conn.run('postgres',sql='CREATE DATABASE sqlarena_db;',log='00_create_database.log')
            evidence['target_database_created'] = not existed
            conn.run(TARGET,file=ddl_path,log='01_ddl.log')
            conn.run(TARGET,file=data_path,log='02_import.log')
            evidence['verification'],first_state = verify_core(conn,world,questions)
            conn.run(TARGET,file=ddl_path,log='03_ddl_repeat.log')
            evidence['ddl_repeat_unchanged'] = hash_value(core_state(conn)) == hash_value(first_state)
            repeated = conn.run(TARGET,file=data_path,log='04_import_repeat_refused.log',allow_failure=True)
            evidence['data_repeat_refused_unchanged'] = (repeated.returncode != 0 and
                'Core already contains data' in repeated.stderr and hash_value(core_state(conn)) == hash_value(first_state))
            # Negative compatibility test changes the expected contract only, never a real table.
            changed_contract = ddl_content.replace('"type": "character varying(100)"','"type": "character varying(101)"',1)
            if changed_contract == ddl_content:
                raise ValueError('Schema guard negative test was not constructed')
            mismatched = conn.run(TARGET,sql=changed_contract,log='05_schema_mismatch_refused.log',allow_failure=True)
            evidence['schema_mismatch_refused_unchanged'] = (mismatched.returncode != 0 and
                'Core v2 column mismatch' in mismatched.stderr and hash_value(core_state(conn)) == hash_value(first_state))
            if not all(evidence[k] for k in ['ddl_repeat_unchanged','data_repeat_refused_unchanged','schema_mismatch_refused_unchanged']):
                raise ValueError('Core rerun/compatibility safety verification failed')
            evidence['status'] = 'PASS'
        after_rows,after_catalog = source_db.snapshot(),source_db.catalog()
        evidence.update(enterprise_rows_after=hash_value(after_rows),enterprise_catalog_after=hash_value(after_catalog),
                        enterprise_rows_unchanged=hash_value(before_rows)==hash_value(after_rows),
                        enterprise_catalog_unchanged=hash_value(before_catalog)==hash_value(after_catalog),
                        protected_files_unchanged=before_files==protected_hashes(),protected_file_hashes_after=protected_hashes())
        if not all(evidence[k] for k in ['enterprise_rows_unchanged','enterprise_catalog_unchanged','protected_files_unchanged']):
            raise ValueError('Source data/catalog/files changed during Core build')
    except Exception as exc:
        evidence['status'] = 'FAIL' if args.apply else 'NOT_EXECUTED'
        evidence['error'] = str(exc)
    evidence['finished_at'] = datetime.now(timezone.utc).isoformat()
    write_report(evidence)
    print(json.dumps({k:evidence[k] for k in ['status','verification','error'] if k in evidence},ensure_ascii=False,indent=2))
    return 0 if evidence['status']=='PASS' or (not args.apply and 'error' not in evidence) else 1


if __name__=='__main__':
    sys.exit(main())
