"""Bounded discovery, evidence-based ranking and registrable-domain diversity."""
import re
from html import unescape
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import tldextract

_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)
TOPICS = {
    'Travel': ['travel', 'hotel booking', 'tours activities', 'car rental', 'travel insurance', 'eSIM travel'],
    'WordPress': ['WordPress', 'WordPress plugins', 'WordPress themes', 'WordPress hosting'],
    'AI': ['AI software', 'AI writing', 'AI video', 'AI productivity'],
    'Marketing': ['marketing software', 'email marketing', 'SEO tools', 'social media software'],
    'Edu LMS': ['learning management system', 'online courses', 'LMS software'],
    'Game': ['gaming', 'game hosting', 'gaming accessories'],
    'Bitcoin': ['bitcoin', 'crypto exchange', 'crypto wallet'],
    'finance app': ['personal finance app', 'budgeting software', 'accounting software'],
    'E-commerce': ['ecommerce', 'online store software', 'ecommerce tools'],
    'Digital Tools & Services': ['digital tools', 'productivity software', 'online services'],
    'Hosting': ['web hosting', 'VPS hosting', 'cloud hosting'],
    'Online Education': ['online education', 'online courses', 'language learning'],
    'Software': ['software', 'SaaS', 'business software'],
    'Baby Products': ['baby products', 'baby clothing', 'strollers'],
    'Remote Work Tools': ['remote work software', 'team collaboration', 'video conferencing'],
    'Hosting & Website Building': ['web hosting', 'website builder', 'domain registration'],
    'Pet Products': ['pet products', 'pet food', 'pet insurance'],
}
AFFILIATE = re.compile(r'\b(?:affiliate|referral)\s+(?:program(?:me)?s?|partners?|network)|chương trình (?:affiliate|tiếp thị liên kết)', re.I)
ROUNDUP = re.compile(r'\b(?:top|best)\s+\d*.*\b(?:affiliate|referral)\s+programs?\b|\b\d+\s+.*affiliate programs\b|\baffiliate programs\s+(?:for|to join)\b', re.I)
CTA = re.compile(r'\b(?:join|apply|become|sign up)\b.{0,65}\b(?:affiliate|partner|program)|\b(?:earn|commission|payout|revenue share)\b', re.I)


def root_domain(url):
    host = (urlsplit(url if '://' in url else 'https://' + url).hostname or '').lower().rstrip('.')
    result = _extract(host)
    return '.'.join(part for part in (result.domain, result.suffix) if part) or host


def canonical_url(url):
    parsed = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in ('gclid', 'fbclid')]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), urlencode(sorted(query)), ''))


def build_queries(industry, keyword='', hosts=()):
    topics = TOPICS.get(industry, [industry])
    intents = ['"affiliate program"', '"partner program" commission', '"referral program"']
    queries = []
    for i in range(6):
        topic = topics[i % len(topics)]
        intent = intents[0] if i < len(topics) else intents[(i - len(topics) + 1) % len(intents)]
        query = f'{topic} {keyword.strip()} {intent}'.strip()
        if hosts:
            query += ' (' + ' OR '.join('site:' + host for host in hosts) + ')'
        queries.append(query)
    return list(dict.fromkeys(queries))


def rank_candidate(item, keyword=''):
    title = str(item.get('title', ''))
    snippet = str(item.get('snippet', ''))
    parsed = urlsplit(item['link'])
    path = parsed.path.lower()
    text = title + ' ' + snippet
    score, reasons = 0, []
    if AFFILIATE.search(text):
        score += 40
        reasons.append('Tiêu đề/mô tả đề cập chương trình affiliate')
    if re.search(r'(?:affiliate|partner|referral)', path) or re.match(r'(?:partners?|affiliates?)\.', parsed.hostname or ''):
        score += 25
        reasons.append('URL chương trình đối tác')
    if CTA.search(text):
        score += 20
        reasons.append('Có thông tin tham gia/hoa hồng')
    roundup = bool(ROUNDUP.search(title)) or bool(re.search(r'/(?:blog|guides?|articles?)/', path))
    if roundup:
        score -= 55
        reasons.append('Có dấu hiệu bài tổng hợp/hướng dẫn')
    if root_domain(item['link']) in {'youtube.com', 'facebook.com', 'reddit.com', 'pinterest.com', 'linkedin.com'}:
        score -= 50
        reasons.append('Trang mạng xã hội')
    words = re.findall(r'\w+', keyword.lower())
    if words:
        matched = sum(word in text.lower() + ' ' + path for word in words)
        score += round(15 * matched / len(words)) if matched else -20
        if matched:
            reasons.append('Khớp từ khóa bổ sung')
    return dict(item, rank_score=max(0, min(100, score)), reasons=reasons,
                roundup=roundup, root_domain=root_domain(item['link']))


def discover(search, industry, keyword, hosts, count, include_roundups=False, candidate_filter=None, recent_after=None):
    queries = build_queries(industry, keyword, hosts)
    if recent_after:
        queries = [query + ' after:' + recent_after for query in queries]
    # One page per query, then round-robin second/third pages by increasing
    # requested count. Keep all calls bounded, including calls made by adapter.
    per_query = 10 if count <= 30 else 20 if count <= 50 else 30
    candidates = {}
    for query in queries:
        for item in search(query, per_query):
            url = item.get('link', '')
            parsed = urlsplit(url)
            host = (parsed.hostname or '').lower()
            if parsed.scheme not in ('http', 'https') or not host:
                continue
            if hosts and not any(host == allowed or host.endswith('.' + allowed) for allowed in hosts):
                continue
            ranked = rank_candidate(item, keyword)
            key = canonical_url(url)
            ranked['source_query'] = query
            if key not in candidates or ranked['rank_score'] > candidates[key]['rank_score']:
                candidates[key] = ranked
    ranked = sorted(candidates.values(), key=lambda row: row['rank_score'], reverse=True)
    result, domains = [], set()
    for item in ranked:
        if item['rank_score'] < (20 if include_roundups else 50) or (item['roundup'] and not include_roundups):
            continue
        if candidate_filter and not candidate_filter(item):
            continue
        if item['root_domain'] in domains:
            continue
        domains.add(item['root_domain'])
        result.append(item)
        if len(result) >= count:
            break
    return result, {'queries': len(queries), 'candidates': len(candidates), 'max_requests': len(queries) * (per_query // 10)}


def inspect_html(html):
    # Generic tracking, affiliate text and Facebook pixels are not Google Ads.
    raw = html.lower()
    ads = []
    if re.search(r'\baw-\d{6,}\b', raw):
        ads.append('Google Ads conversion ID (AW-)')
    if 'googleadservices.com/pagead/conversion' in raw or 'google.com/pagead/1p-conversion' in raw:
        ads.append('Google Ads conversion tag')
    text = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', ' ', html, flags=re.I | re.S)
    text = unescape(re.sub(r'<[^>]+>', ' ', text))
    affiliate = bool(AFFILIATE.search(text) and CTA.search(text))
    return {'affiliate': affiliate, 'ads': ads, 'checked': True}
