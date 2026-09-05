"""Source-labelled project dates and monthly visits; unknown is never zero."""
import csv
import io
import math
import re
from datetime import date, timedelta
from urllib.parse import urlsplit
from discovery import root_domain


def months_ago(today, months):
    import calendar
    year, month = divmod(today.year * 12 + today.month - 1 - months, 12)
    return date(year, month + 1, min(today.day, calendar.monthrange(year, month + 1)[1]))


def content_date(value, today=None):
    today = today or date.today()
    if not value:
        return None
    raw = str(value).strip()
    relative = re.fullmatch(r'(\d+)\s+(day|week|month|year)s?\s+ago', raw.lower())
    if relative:
        amount, unit = int(relative[1]), relative[2]
        return months_ago(today, amount * (12 if unit == 'year' else 1)) if unit in ('month', 'year') else today - timedelta(days=amount * (7 if unit == 'week' else 1))
    import pandas as pd
    try:
        parsed = pd.to_datetime(raw, errors='coerce')
        return parsed.date() if pd.notna(parsed) else None
    except (ValueError, OverflowError, TypeError):
        return None


def read_metrics(raw, today=None):
    """One domain per row, traffic for a completed month, explicit provenance."""
    today = today or date.today()
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not reader.fieldnames or 'domain' not in reader.fieldnames:
            raise ValueError('File CSV cần cột domain.')
        records = {}
        for line, row in enumerate(reader, 2):
            if line > 5001:
                raise ValueError('Tối đa 5.000 dòng dữ liệu.')
            domain = (row.get('domain') or '').strip()
            host = urlsplit(domain if '://' in domain else 'https://' + domain).hostname or ''
            if not re.fullmatch(r'[a-zA-Z0-9.-]+', host) or '.' not in host:
                raise ValueError(f'Dòng {line}: domain không hợp lệ.')
            domain = root_domain(domain)
            if domain in records:
                raise ValueError(f'Dòng {line}: trùng tên miền gốc; chỉ giữ một dòng mới nhất cho mỗi domain.')
            visits = (row.get('monthly_visits') or '').strip()
            month = (row.get('traffic_month') or '').strip()
            source = (row.get('traffic_source') or '').strip()
            if visits:
                try:
                    number = float(visits)
                except ValueError:
                    raise ValueError(f'Dòng {line}: monthly_visits phải là số nguyên, không có dấu phân cách.') from None
                if not math.isfinite(number) or number < 0 or not number.is_integer():
                    raise ValueError(f'Dòng {line}: monthly_visits phải là số nguyên không âm.')
                if not re.fullmatch(r'\d{4}-\d{2}', month) or not source:
                    raise ValueError(f'Dòng {line}: traffic cần traffic_month (YYYY-MM) và traffic_source.')
                try:
                    period = date.fromisoformat(month + '-01')
                except ValueError:
                    raise ValueError(f'Dòng {line}: tháng traffic không hợp lệ.') from None
                if period >= today.replace(day=1):
                    raise ValueError(f'Dòng {line}: dùng traffic của tháng đã hoàn tất.')
                visits = int(number)
            else:
                visits = None
            launched = (row.get('launched_at') or '').strip()
            launch_source = (row.get('launch_source') or '').strip()
            if launched:
                try:
                    launch_date = date.fromisoformat(launched)
                except ValueError:
                    raise ValueError(f'Dòng {line}: launched_at cần định dạng YYYY-MM-DD.') from None
                if launch_date > today or not launch_source:
                    raise ValueError(f'Dòng {line}: ngày ra mắt không được ở tương lai và cần launch_source.')
            records[domain] = {'monthly_visits': visits, 'traffic_month': month if visits is not None else '',
                               'traffic_source': source if visits is not None else '',
                               'launched_at': launched, 'launch_source': launch_source}
        return records
    except UnicodeDecodeError:
        raise ValueError('Vui lòng dùng CSV mã hóa UTF-8.') from None


def passes_filters(item, metrics, age_months=0, date_basis='content', min_visits=0, min_score=0, today=None):
    today = today or date.today()
    if item['rank_score'] < min_score:
        return False
    if age_months:
        value = metrics.get('launched_at') if date_basis == 'launch' else item.get('date')
        parsed = content_date(value, today)
        if parsed is None or not months_ago(today, age_months) <= parsed <= today:
            return False
    if min_visits:
        visits = metrics.get('monthly_visits')
        month = metrics.get('traffic_month', '')
        # Expired or unknown data must not silently satisfy a high-traffic filter.
        oldest = months_ago(today.replace(day=1), 3).strftime('%Y-%m')
        if visits is None or visits < min_visits or not oldest <= month < today.strftime('%Y-%m'):
            return False
    return True


METRICS_TEMPLATE = 'domain,monthly_visits,traffic_month,traffic_source,launched_at,launch_source\n'
