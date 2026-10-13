"""Independent Python answers computed from actual base-table rows, without SQL."""
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP


def groups(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out


def rounded(x):
    return Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def dt(value):
    return datetime.fromisoformat(value)


def month(value):
    return value[:7] + '-01'


def quarter(value):
    return f'{value[:4]}-{((int(value[5:7])-1)//3)*3+1:02d}-01'


def month_number(value):
    return int(value[:4]) * 12 + int(value[5:7]) - 1


def month_string(n):
    return f'{n//12:04d}-{n%12+1:02d}-01'


def consecutive(values):
    """Group sorted unique calendar month numbers by adjacency."""
    runs = []
    for value in sorted(values):
        if not runs or value != runs[-1][-1] + 1:
            runs.append([])
        runs[-1].append(value)
    return runs


def project(row, names):
    return {name: row[name] for name in names.split()}


def expected(n, db):
    c, a, p, e, o = (db[t] for t in ['customers', 'customer_addresses', 'products', 'employees', 'orders'])
    i, t, pay, refund = (db[k] for k in ['order_items', 'inventory_transactions', 'payments', 'refunds'])
    exp, sal, dep, sup, wh, cat, hist = (db[k] for k in ['operating_expenses', 'salary_history',
        'departments', 'suppliers', 'warehouses', 'categories', 'order_status_history'])
    pm = {r['product_id']: r for r in p}
    em = {r['employee_id']: r for r in e}
    om = {r['order_id']: r for r in o}
    sm = {r['supplier_id']: r for r in sup}
    dm = {r['department_id']: r for r in dep}
    wm = {r['warehouse_id']: r for r in wh}
    cm = {r['category_id']: r for r in cat}
    am = {r['address_id']: r for r in a}
    out = []

    if n == 1:
        rows = sorted((r for r in c if r['status']=='active' and r['registered_at']<'2025-01-01'),
                      key=lambda r: (r['registered_at'], r['customer_id']))
        return [project(r, 'customer_id full_name email registered_at') for r in rows]
    if n == 2:
        return [{'city': city} for city in sorted({r['city'] for r in a})]
    if n == 3:
        rows = sorted((r for r in o if r['status']=='pending'), key=lambda r: (r['order_date'],r['order_id']))
        return [project(r,'order_id customer_id warehouse_id order_date total_amount') for r in rows]
    if n == 4:
        rows = sorted((r for r in o if r['status']=='delivered' and '2026-01-01'<=r['order_date']<'2027-01-01'),
                      key=lambda r: (r['order_date'],r['order_id']))
        return [project(r,'order_id order_date shipped_at delivered_at carrier_name') for r in rows]
    if n == 5:
        rows = sorted((r for r in p if r['is_active'] and r['list_price']>=1000000),
                      key=lambda r: (-r['list_price'],r['product_id']))
        return [project(r,'product_id product_name sku list_price cost_price') for r in rows]
    if n == 6:
        return [project(r,'employee_id full_name department_id job_title') for r in sorted(e,key=lambda r:r['employee_id']) if r['manager_id'] is None]
    if n == 7:
        rows = sorted((r for r in refund if r['refund_status']=='pending' and r['completed_at'] is None),
                      key=lambda r:(r['requested_at'],r['refund_id']))
        return [project(r,'refund_id payment_id refund_amount requested_at') for r in rows]
    if n == 8:
        return [{'country': x} for x in sorted({r['country'] for r in sup if r['country'] is not None})]
    if n == 9:
        defaults = groups([r for r in a if r['is_default']],lambda r:r['customer_id'])
        for r in sorted(c,key=lambda r:r['customer_id']):
            for addr in sorted(defaults[r['customer_id']],key=lambda x:x['address_id']) or [None]:
                out.append({'customer_id':r['customer_id'],'full_name':r['full_name'],
                            **{k:addr[k] if addr else None for k in ['address_id','city','address_line']}})
        return out
    if n == 10:
        return [{**project(r,'order_item_id order_id quantity line_total'),'product_name':pm[r['product_id']]['product_name']}
                for r in sorted(i,key=lambda r:r['order_item_id'])]
    if n == 11:
        return [{**project(r,'product_id product_name'),'category_name':cm[r['category_id']]['category_name'],
                 'category_active':cm[r['category_id']]['is_active']} for r in sorted(p,key=lambda r:r['product_id'])]
    if n == 12:
        return [{**project(r,'product_id sku'),**project(sm[r['supplier_id']],'supplier_name country contact_email')}
                for r in sorted(p,key=lambda r:r['product_id'])]
    if n == 13:
        return [{'employee_id':r['employee_id'],'employee_name':r['full_name'],'manager_id':r['manager_id'],
                 'manager_name':em[r['manager_id']]['full_name'] if r['manager_id'] is not None else None}
                for r in sorted(e,key=lambda r:r['employee_id'])]
    if n == 14:
        return [{**project(r,'department_id department_name manager_employee_id'),
                 'manager_name':em[r['manager_employee_id']]['full_name'] if r['manager_employee_id'] else None}
                for r in sorted(dep,key=lambda r:r['department_id'])]
    if n == 15:
        return [{**project(r,'expense_id expense_category amount expense_date'),
                 'approver_name':em[r['approved_by_employee_id']]['full_name'] if r['approved_by_employee_id'] else None}
                for r in sorted(exp,key=lambda r:r['expense_id'])]
    if n == 16:
        return [{'status':k,'customer_count':len(v)} for k,v in sorted(groups(c,lambda r:r['status']).items())]
    if n == 17:
        return [{'status':k,'order_count':len(v),'order_value':sum(r['total_amount'] for r in v)}
                for k,v in sorted(groups(o,lambda r:r['status']).items())]
    if n == 18:
        return [{'transaction_type':k,'transaction_count':len(v),'net_units':sum(r['quantity_change'] for r in v)}
                for k,v in sorted(groups(t,lambda r:r['transaction_type']).items())]
    if n == 19:
        return [{'department_id':k,'employee_count':len(v),'current_payroll':sum(r['current_salary'] for r in v)}
                for k,v in sorted(groups(e,lambda r:r['department_id']).items())]
    if n == 20:
        hours = [Decimal(str((dt(r['completed_at'])-dt(r['requested_at'])).total_seconds()))/3600
                 for r in refund if r['refund_status']=='completed' and r['completed_at'] is not None]
        return [{'completed_refunds':len(hours),'min_hours':rounded(min(hours)) if hours else None,
                 'max_hours':rounded(max(hours)) if hours else None,
                 'avg_hours':rounded(sum(hours)/len(hours)) if hours else None}]
    if n == 21:
        defaults = groups([r for r in a if r['is_default']],lambda r:r['customer_id'])
        for r in sorted(o,key=lambda r:r['order_id']):
            shipping = am[r['shipping_address_id']]
            for addr in sorted(defaults[r['customer_id']],key=lambda r:r['address_id']):
                if shipping['city'] != addr['city']:
                    out.append({'order_id':r['order_id'],'customer_id':r['customer_id'],
                                'shipping_city':shipping['city'],'default_address_id':addr['address_id'],'default_city':addr['city']})
        return out
    if n == 22:
        sale = {r['order_item_id']:r for r in t if r['transaction_type']=='sale'}
        for r in sorted(i,key=lambda r:(r['order_id'],r['order_item_id'])):
            order = om[r['order_id']]
            if order['status']=='processing':
                tx = sale.get(r['order_item_id'])
                warehouse = wm.get(order['warehouse_id'])
                out.append({**project(r,'order_id order_item_id product_id quantity'),'warehouse_id':order['warehouse_id'],
                            'warehouse_name':warehouse['warehouse_name'] if warehouse else None,
                            'has_sale':tx is not None,'sale_at':tx['transaction_date'] if tx else None})
        return out
    if n == 23:
        for r in sorted(wh,key=lambda r:r['warehouse_id']):
            emp = em.get(r['manager_employee_id'])
            dept = dm.get(emp['department_id']) if emp else None
            manager_id = dept['manager_employee_id'] if dept else None
            out.append({'warehouse_id':r['warehouse_id'],'warehouse_manager_id':emp['employee_id'] if emp else None,
                        'warehouse_manager_name':emp['full_name'] if emp else None,
                        'department_name':dept['department_name'] if dept else None,'department_manager_id':manager_id,
                        'same_person':emp['employee_id']==manager_id if emp and manager_id is not None else None})
        return out
    if n == 24:
        for key, rows in sorted(groups([r for r in o if r['employee_id'] is not None],lambda r:r['employee_id']).items()):
            delivered = [r for r in rows if r['status']=='delivered']
            if len(delivered)>=5:
                out.append({'employee_id':key,'assigned_orders':len(rows),'delivered_orders':len(delivered),
                            'delivered_order_value':sum(r['total_amount'] for r in delivered)})
        return out
    if n == 25:
        for key, rows in sorted(groups([r for r in p if r['is_active']],lambda r:r['supplier_id']).items()):
            diversity = len({r['category_id'] for r in rows})
            if len(rows)>=5 and diversity>=3:
                out.append({'supplier_id':key,'active_products':len(rows),'category_count':diversity,
                            'avg_unit_margin':rounded(sum(r['list_price']-r['cost_price'] for r in rows)/len(rows))})
        return out
    if n == 26:
        for key, rows in sorted(groups(a,lambda r:r['customer_id']).items()):
            cities = len({r['city'] for r in rows})
            if cities>=2:
                out.append({'customer_id':key,'address_count':len(rows),'city_count':cities,
                            'default_count':sum(r['is_default'] for r in rows)})
        return out
    if n == 27:
        g = groups(exp,lambda r:(month(r['expense_date']),r['department_id']))
        for (m,d), rows in sorted(g.items(),key=lambda kv:(kv[0][0],kv[0][1] is None,kv[0][1] or 0)):
            if len(rows)>=2:
                out.append({'month':m,'department_id':d,'expense_count':len(rows),'total_expense':sum(r['amount'] for r in rows),
                            'approved_expense':sum(r['amount'] for r in rows if r['approved_by_employee_id'] is not None)})
        return out
    if n == 28:
        balances = {k:sum(r['quantity_change'] for r in v) for k,v in groups(t,lambda r:r['warehouse_id']).items()}
        for r in sorted(wh,key=lambda r:r['warehouse_id']):
            balance = balances.get(r['warehouse_id'],0)
            out.append({'warehouse_id':r['warehouse_id'],'capacity':r['capacity'],'current_units':balance,
                        'free_capacity':r['capacity']-balance,
                        'utilization_pct':rounded(Decimal(100)*balance/r['capacity']) if r['capacity'] else None})
        return out
    if n == 29:
        seen = {r['customer_id'] for r in o}
        return [project(r,'customer_id full_name registered_at') for r in sorted(c,key=lambda r:r['customer_id']) if r['customer_id'] not in seen]
    if n == 30:
        ordered = {r['product_id'] for r in i}
        positive = {k[0] for k,v in groups(t,lambda r:(r['product_id'],r['warehouse_id'])).items() if sum(r['quantity_change'] for r in v)>0}
        return [project(r,'product_id product_name') for r in sorted(p,key=lambda r:r['product_id']) if r['product_id'] not in ordered and r['product_id'] in positive]
    if n == 31:
        averages = {k:sum(r['current_salary'] for r in v)/len(v) for k,v in groups(e,lambda r:r['department_id']).items()}
        return [project(r,'employee_id department_id current_salary') for r in sorted(e,key=lambda r:r['employee_id']) if r['current_salary']>averages[r['department_id']]]
    if n == 32:
        by_order = groups(pay,lambda r:r['order_id'])
        for r in sorted(pay,key=lambda r:r['order_id']):
            if r['payment_status']=='success' and any(f['payment_status']=='failed' and
                (f['attempted_at'],f['payment_id'])<(r['attempted_at'],r['payment_id']) for f in by_order[r['order_id']]):
                out.append({'order_id':r['order_id'],'success_payment_id':r['payment_id'],'success_at':r['attempted_at']})
        return out
    if n == 33:
        by_supplier = groups(p,lambda r:r['supplier_id'])
        return [project(r,'supplier_id supplier_name') for r in sorted(sup,key=lambda r:r['supplier_id'])
                if r['status']=='active' and by_supplier[r['supplier_id']] and all(x['is_active'] for x in by_supplier[r['supplier_id']])]
    if n == 34:
        im = {r['order_item_id']:r for r in i}
        physically_returned = {im[r['order_item_id']]['order_id'] for r in t if r['transaction_type']=='return'}
        payment_orders = {r['payment_id']:r['order_id'] for r in pay}
        refunded = {payment_orders[r['payment_id']] for r in refund if r['refund_status']=='completed'}
        return [project(r,'order_id customer_id total_amount') for r in sorted(o,key=lambda r:r['order_id'])
                if r['status']=='delivered' and r['order_id'] in physically_returned-refunded]
    if n == 35:
        for warehouse, rows in sorted(groups([r for r in o if r['warehouse_id'] is not None],lambda r:r['warehouse_id']).items()):
            for pos,r in enumerate(sorted(rows,key=lambda r:(-r['total_amount'],r['order_date'],r['order_id']))[:2],1):
                out.append({**project(r,'warehouse_id order_id total_amount order_date'),'position':pos})
        return out
    if n == 36:
        for category, rows in sorted(groups(p,lambda r:r['category_id']).items()):
            prices = sorted({r['list_price'] for r in rows},reverse=True)
            ranks = {price:rank for rank,price in enumerate(prices,1)}
            for r in sorted(rows,key=lambda r:(ranks[r['list_price']],r['product_id'])):
                rank = ranks[r['list_price']]
                if rank<=3:
                    out.append({'category_id':category,'price_rank':rank,'product_id':r['product_id'],'list_price':r['list_price']})
        return out
    if n == 37:
        for emp,rows in sorted(groups(sal,lambda r:r['employee_id']).items()):
            rows = sorted(rows,key=lambda r:(r['effective_date'],r['salary_history_id']))
            for prev,r in zip(rows,rows[1:]):
                out.append({**project(r,'employee_id effective_date salary'),'previous_salary':prev['salary'],
                            'change_pct':rounded(100*(r['salary']-prev['salary'])/prev['salary'])})
        return out
    if n == 38:
        monthly = groups([r for r in o if r['status']=='delivered'],lambda r:month(r['order_date']))
        previous = None
        for m,rows in sorted(monthly.items()):
            value = sum(r['total_amount'] for r in rows)
            out.append({'month':m,'order_value':value,'previous_value':previous,
                        'change_pct':rounded(100*(value-previous)/previous) if previous else None})
            previous = value
        return out
    if n == 39:
        running = 0
        for m,rows in sorted(groups([r for r in pay if r['payment_status']=='success'],lambda r:month(r['attempted_at'])).items()):
            total = sum(r['amount'] for r in rows)
            running += total
            out.append({'month':m,'collected_amount':total,'cumulative_collected':running})
        return out
    if n == 40:
        for customer,rows in sorted(groups(o,lambda r:r['customer_id']).items()):
            rows = sorted(rows,key=lambda r:(r['order_date'],r['order_id']))
            for prev,r in zip(rows,rows[1:]):
                gap = Decimal(str((dt(r['order_date'])-dt(prev['order_date'])).total_seconds()))/86400
                out.append({'customer_id':customer,'order_id':r['order_id'],'previous_order_id':prev['order_id'],'gap_days':rounded(gap)})
        return out
    if n == 41:
        exposure = defaultdict(set)
        for r in i:
            order = om[r['order_id']]
            if order['status']=='delivered':
                exposure[r['product_id']].add(order['warehouse_id'])
        balances = {key:sum(r['quantity_change'] for r in rows) for key,rows in groups(t,lambda r:(r['product_id'],r['warehouse_id'])).items()}
        supplier_products = groups([r for r in p if r['is_active']],lambda r:r['supplier_id'])
        for supplier in sorted(sup,key=lambda r:r['supplier_id']):
            products = supplier_products[supplier['supplier_id']]
            if len(products)>=2 and all(exposure[r['product_id']] and all(balances.get((r['product_id'],w),0)>0
                for w in exposure[r['product_id']]) for r in products):
                out.append(project(supplier,'supplier_id supplier_name'))
        return out
    if n == 42:
        totals = defaultdict(lambda:defaultdict(Decimal))
        for r in o:
            if r['status']=='delivered' and r['employee_id'] is not None:
                totals[month_number(r['order_date'])][r['employee_id']] += r['total_amount']
        victories = defaultdict(list)
        for m,values in totals.items():
            winner = min(values,key=lambda emp:(-values[emp],emp))
            victories[winner].append(m)
        for emp,months in sorted(victories.items()):
            best = min(consecutive(months),key=lambda run:(-len(run),run[0]))
            out.append({'employee_id':emp,'start_month':month_string(best[0]),'end_month':month_string(best[-1]),'streak_months':len(best)})
        return out
    if n == 43:
        monthly = defaultdict(Decimal)
        for r in pay:
            if r['payment_status']=='success':
                monthly[month_number(r['attempted_at'])] += r['amount']
        for r in refund:
            if r['refund_status']=='completed':
                monthly[month_number(r['completed_at'])] -= r['refund_amount']
        if not monthly:
            return []
        for end in range(min(monthly)+2,max(monthly)+1):
            out.append({'start_month':month_string(end-2),'end_month':month_string(end),
                        'net_three_months':sum(monthly.get(m,0) for m in range(end-2,end+1))})
        return sorted(out,key=lambda r:(-r['net_three_months'],r['end_month']))[:3]
    if n == 44:
        by_department = groups([r for r in exp if '2025-01-01'<=r['expense_date']<'2026-01-01'],lambda r:r['department_id'])
        for department,rows in sorted(by_department.items(),key=lambda kv:(kv[0] is None,kv[0] or 0)):
            totals = {key:sum(r['amount'] for r in values) for key,values in groups(rows,lambda r:r['expense_category']).items()}
            total,acc = sum(totals.values()),0
            for rank,(category,value) in enumerate(sorted(totals.items(),key=lambda kv:(-kv[1],kv[0])),1):
                if acc>=Decimal('0.8')*total:
                    break
                acc += value
                out.append({'department_id':department,'position':rank,'expense_category':category,
                            'category_amount':value,'cumulative_pct':rounded(100*acc/total)})
        return out
    if n == 45:
        values = defaultdict(lambda:defaultdict(lambda:defaultdict(Decimal)))
        for r in i:
            order = om[r['order_id']]
            if order['status']=='delivered' and order['employee_id'] is not None:
                values[quarter(order['order_date'])][order['employee_id']][r['product_id']] += r['line_total']
        for q,employees in sorted(values.items()):
            totals = {emp:sum(products.values()) for emp,products in employees.items()}
            for rank,emp in enumerate(sorted(employees,key=lambda emp:(-totals[emp],emp))[:3],1):
                products = employees[emp]
                best = min(products,key=lambda product:(-products[product],product))
                out.append({'quarter':q,'employee_rank':rank,'employee_id':emp,'merchandise_value':totals[emp],
                            'top_product_id':best,'top_product_value':products[best],
                            'top_share_pct':rounded(100*products[best]/totals[emp]) if totals[emp] else None})
        return out
    if n == 46:
        first,last = month_number('2025-03'),month_number('2026-09')
        for (product,warehouse),rows in sorted(groups(t,lambda r:(r['product_id'],r['warehouse_id'])).items()):
            balance = sum(r['quantity_change'] for r in rows if r['transaction_date']<'2025-03-01')
            changes = defaultdict(int)
            for r in rows:
                if '2025-03-01'<=r['transaction_date']<'2026-10-01':
                    changes[month_number(r['transaction_date'])] += r['quantity_change']
            eligible = []
            for m in range(first,last+1):
                before = balance
                balance += changes[m]
                if balance<before and balance<=50:
                    eligible.append(m)
            runs = consecutive(eligible)
            if runs:
                best = min(runs,key=lambda run:(-len(run),run[0]))
                out.append({'product_id':product,'warehouse_id':warehouse,'start_month':month_string(best[0]),
                            'end_month':month_string(best[-1]),'streak_months':len(best),
                            'depleted_units':-sum(changes[m] for m in best)})
        return out
    if n == 47:
        children = groups(e,lambda r:r['manager_id'])
        for department in sorted(dep,key=lambda r:r['department_id']):
            root = department['manager_employee_id']
            stack = [(root,0,{root})] if root in em else []
            count,depth,payroll = 0,0,0
            while stack:
                employee,level,path = stack.pop()
                if level:
                    count += 1
                    payroll += em[employee]['current_salary']
                    depth = max(depth,level)
                for child in children[employee]:
                    cid = child['employee_id']
                    if cid not in path:
                        stack.append((cid,level+1,path|{cid}))
            out.append({'department_id':department['department_id'],'root_manager_id':root,
                        'descendant_count':count,'max_depth':depth,'descendant_payroll':payroll})
        return out
    if n == 48:
        # A daily sweep intentionally differs from SQL's interval clipping.
        history = groups(sal,lambda r:r['employee_id'])
        results = {}
        for employee in e:
            hire = date.fromisoformat(employee['hire_date'])
            if hire>=date(2026,1,1):
                continue
            department = employee['department_id']
            result = results.setdefault(department,{'eligible':0,'known':0,'weighted':Decimal(0)})
            records = sorted(history[employee['employee_id']],key=lambda r:(r['effective_date'],r['salary_history_id']))
            dates = [date.fromisoformat(r['effective_date']) for r in records]
            day = max(hire,date(2025,1,1))
            while day<date(2026,1,1):
                result['eligible'] += 1
                pos = bisect_right(dates,day)-1
                if pos>=0:
                    result['known'] += 1
                    result['weighted'] += records[pos]['salary']
                day += timedelta(days=1)
        return [{'department_id':department,'eligible_employee_days':r['eligible'],
                 'known_salary_days':r['known'],'unknown_salary_days':r['eligible']-r['known'],
                 'evidenced_monthly_payroll':rounded(r['weighted']/365)} for department,r in sorted(results.items())]
    if n == 49:
        events = groups(hist,lambda r:r['order_id'])
        stage_order = {'pending':1,'processing':2,'shipped':3}
        winners = defaultdict(lambda:defaultdict(list))
        for order in o:
            if order['status']!='delivered' or order['warehouse_id'] is None:
                continue
            rows = sorted(events[order['order_id']],key=lambda r:(r['changed_at'],r['history_id']))
            options = []
            for r,next_event in zip(rows,rows[1:]):
                if r['new_status'] in stage_order:
                    hours = Decimal(str((dt(next_event['changed_at'])-dt(r['changed_at'])).total_seconds()))/3600
                    options.append((r['new_status'],hours))
            if options:
                status,hours = min(options,key=lambda item:(-item[1],stage_order[item[0]]))
                winners[(order['warehouse_id'],quarter(order['order_date']))][status].append(hours)
        for (warehouse,q),stages in sorted(winners.items()):
            winner = min(stages,key=lambda status:(-len(stages[status]),stage_order[status]))
            hours = stages[winner]
            out.append({'warehouse_id':warehouse,'quarter':q,'bottleneck_status':winner,
                        'selected_orders':len(hours),'avg_stage_hours':rounded(sum(hours)/len(hours))})
        return out
    if n == 50:
        for employee,rows in sorted(groups(sal,lambda r:r['employee_id']).items()):
            rows = sorted(rows,key=lambda r:(r['effective_date'],r['salary_history_id']))
            runs,current = [],[]
            for before,after in zip(rows,rows[1:]):
                if after['salary']>before['salary']:
                    if not current:
                        current = [before]
                    current.append(after)
                else:
                    if current:
                        runs.append(current)
                    current = []
            if current:
                runs.append(current)
            runs = [run for run in runs if len(run)>=3]
            if runs:
                run = min(runs,key=lambda run:(-(run[-1]['salary']/run[0]['salary']-1),-(len(run)-1),run[0]['effective_date']))
                out.append({'employee_id':employee,'start_date':run[0]['effective_date'],'end_date':run[-1]['effective_date'],
                            'raise_count':len(run)-1,'start_salary':run[0]['salary'],'end_salary':run[-1]['salary'],
                            'growth_pct':rounded(100*(run[-1]['salary']/run[0]['salary']-1))})
        return out
    raise ValueError(f'No independent oracle for question {n}')
