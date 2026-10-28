"""psql transport with existing read-only role and read-only transactions."""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import time
from decimal import Decimal
from pathlib import Path

TABLE_KEYS = {
    'customers': 'customer_id', 'customer_addresses': 'address_id', 'categories': 'category_id',
    'suppliers': 'supplier_id', 'products': 'product_id', 'departments': 'department_id',
    'employees': 'employee_id', 'warehouses': 'warehouse_id', 'orders': 'order_id',
    'order_items': 'order_item_id', 'order_status_history': 'history_id',
    'inventory_transactions': 'transaction_id', 'salary_history': 'salary_history_id',
    'payments': 'payment_id', 'refunds': 'refund_id', 'operating_expenses': 'expense_id',
}


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float, Decimal)):
        d = Decimal(str(value))
        return format(d.normalize(), 'f') if d else '0'
    raise TypeError(type(value))


def dump(value):
    return json.dumps(canonical(value), sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def check_sql(sql):
    # This deliberately narrow lexer accepts only our reviewed SELECT vocabulary.
    # PostgreSQL does the actual grammar/type checking through \gdesc and execution.
    pattern = re.compile(r"\s+|'(?:''|[^'])*'|[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?|::|<>|<=|>=|\|\||[-+*/%=<>,.();\[\]]")
    tokens, pos = [], 0
    for m in pattern.finditer(sql):
        if m.start() != pos:
            raise ValueError('SQL contains an unsupported token')
        pos = m.end()
        if not m.group().isspace():
            tokens.append(m.group())
    if pos != len(sql) or not tokens or tokens[0].upper() not in {'SELECT', 'WITH'}:
        raise ValueError('Only SELECT or WITH SELECT is accepted')
    if tokens[-1] == ';':
        tokens.pop()
    upper = [t.upper() if not t.startswith("'") else '<literal>' for t in tokens]
    forbidden = {'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE',
                 'COPY', 'CALL', 'DO', 'INTO', 'SET', 'RESET', 'FOR', 'LOCK', 'GRANT', 'REVOKE'}
    if ';' in tokens or forbidden.intersection(upper):
        raise ValueError('Multiple statements or a forbidden operation')
    if any(tuple(tokens[i:i+2]) in {('-','-'),('/','*'),('*','/')} for i in range(len(tokens)-1)):
        raise ValueError('SQL comments are not accepted by the curated-query guard')
    functions = {'ROUND', 'SUM', 'COUNT', 'AVG', 'COALESCE', 'NULLIF', 'DATE_TRUNC', 'LAG',
                 'ROW_NUMBER', 'DENSE_RANK', 'MIN', 'MAX', 'GENERATE_SERIES', 'EXTRACT',
                 'GREATEST', 'LEAST', 'LEAD', 'ANY'}
    grammar = {'AS', 'OVER', 'FILTER', 'EXISTS', 'IN', 'AND', 'OR', 'NOT', 'FROM', 'WHERE',
               'BY', 'SELECT', 'ON', 'HAVING', 'USING'}
    for i, token in enumerate(upper[:-1]):
        if re.fullmatch('[A-Z_][A-Z_0-9]*', token) and tokens[i + 1] == '(':
            if i and tokens[i-1] == '.':
                raise ValueError('Qualified function calls are not accepted')
            if token not in functions | grammar:
                raise ValueError(f'Unapproved function: {token}')
    return ' '.join(tokens)


class ReadOnlyDB:
    def __init__(self, timeout_ms=15000):
        configured = os.environ.get('PSQL_BIN')
        self.psql = configured or shutil.which('psql')
        if not self.psql:
            bins = sorted(Path('C:/Program Files/PostgreSQL').glob('*/bin/psql.exe'), reverse=True)
            self.psql = str(bins[0]) if bins else None
        if not self.psql:
            raise RuntimeError('psql not found; set PSQL_BIN')
        if os.environ.get('PGDATABASE', 'enterprise_db') != 'enterprise_db':
            raise RuntimeError('This validator is restricted to enterprise_db')
        self.timeout_ms = timeout_ms
        self.env = os.environ.copy()
        self.env.update({'PGCLIENTENCODING': 'UTF8', 'LC_MESSAGES': 'C',
                         'PGOPTIONS': f'-c default_transaction_read_only=on -c statement_timeout={timeout_ms}'})
        self.args = [self.psql, '-X', '-w', '-q', '-h', os.environ.get('PGHOST', 'localhost'),
                     '-p', os.environ.get('PGPORT', '5432'), '-U', os.environ.get('PGUSER', 'postgres'),
                     '-d', 'enterprise_db', '-v', 'ON_ERROR_STOP=1']

    def run(self, body, *, csv_mode=False, timing=False):
        prelude = ("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
                   "SET LOCAL ROLE pg_read_all_data;\n"
                   "SET LOCAL search_path=pg_catalog,public;\n"
                   "SET LOCAL TimeZone='UTC';\nSET LOCAL DateStyle='ISO, YMD';\n")
        command = self.args + (['--csv'] if csv_mode else ['-A', '-t'])
        script = prelude + ('\\timing on\n' if timing else '') + body
        script += ('\n\\timing off\n' if timing else '\n') + 'ROLLBACK;\n'
        start = time.perf_counter()
        result = subprocess.run(command, input=script, capture_output=True, encoding='utf-8',
                                env=self.env, timeout=max(30, self.timeout_ms / 1000 + 10))
        wall_ms = (time.perf_counter() - start) * 1000
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f'psql exited {result.returncode}')
        elapsed = None
        output = result.stdout
        if timing:
            match = re.search(r'^Time: ([0-9.]+) ms.*$', output, flags=re.M)
            if not match:
                raise RuntimeError('Server statement timing missing from psql output')
            elapsed = float(match.group(1))
            output = re.sub(r'^Time: .*\n?', '', output, flags=re.M)
        return output.strip(), elapsed, wall_ms

    def query(self, sql):
        bare = sql.strip().rstrip(';')
        wrapped = "SELECT COALESCE(jsonb_agg(to_jsonb(result_row)), '[]'::jsonb) FROM (\n" + bare + '\n) result_row;'
        output, elapsed, wall = self.run(wrapped, timing=True)
        return json.loads(output, parse_float=Decimal), elapsed, wall

    def describe(self, sql):
        output, _, _ = self.run(sql.strip().rstrip(';') + '\n\\gdesc\n', csv_mode=True)
        return [{'name': r['Column'], 'postgres_type': r['Type']}
                for r in csv.DictReader(io.StringIO(output))]

    def identity(self):
        rows, _, _ = self.query("""SELECT current_database() AS database,session_user AS login_role,
 current_user AS effective_role,current_setting('transaction_read_only') AS transaction_read_only,
 current_setting('statement_timeout') AS statement_timeout,version() AS server_version,
 (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) AS effective_superuser,
 has_schema_privilege(current_user,'public','CREATE') AS can_create_in_public,
 has_table_privilege(current_user,'public.orders','INSERT,UPDATE,DELETE,TRUNCATE') AS can_write_orders""")
        value = rows[0]
        if value['effective_role'] != 'pg_read_all_data' or value['transaction_read_only'] != 'on':
            raise RuntimeError('Read-only enforcement not active')
        if value['effective_superuser'] or value['can_create_in_public'] or value['can_write_orders']:
            raise RuntimeError('Effective role has write privileges')
        rights,_,_ = self.query("""SELECT table_name,
has_table_privilege(current_user,quote_ident(table_schema)||'.'||quote_ident(table_name),'SELECT') AS can_read,
has_table_privilege(current_user,quote_ident(table_schema)||'.'||quote_ident(table_name),'INSERT,UPDATE,DELETE,TRUNCATE') AS can_write
FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name""")
        if set(r['table_name'] for r in rights)!=set(TABLE_KEYS) or any(not r['can_read'] or r['can_write'] for r in rights):
            raise RuntimeError('Expected SELECT-only access to the 16 Dataset v1 tables')
        value['table_privileges'] = rights
        return value

    def snapshot(self):
        parts = []
        for table, key in TABLE_KEYS.items():
            parts += [f"'{table}'", f"(SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY {key}),'[]'::jsonb) FROM public.{table} t)"]
        output, _, _ = self.run('SELECT jsonb_build_object(' + ','.join(parts) + ');')
        return json.loads(output, parse_float=Decimal)

    def catalog(self):
        columns, _, _ = self.query("""SELECT table_name,column_name,data_type,is_nullable,ordinal_position
FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position""")
        constraints, _, _ = self.query("""SELECT c.relname AS table_name,p.conname AS name,p.contype AS kind,
pg_get_constraintdef(p.oid) AS definition FROM pg_constraint p
JOIN pg_class c ON c.oid=p.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' ORDER BY c.relname,p.conname""")
        indexes, _, _ = self.query("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname")
        return {'columns': columns, 'constraints': constraints, 'indexes': indexes}
