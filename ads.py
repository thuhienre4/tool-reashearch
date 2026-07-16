import hashlib
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def load_local_env(path=Path(".env")):
    """Load simple KEY=VALUE pairs without adding another dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


st.set_page_config(
    page_title="AffiScout — Affiliate Marketplace",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_KEY = os.getenv("GOOGLE_API_KEY", "")
CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")
SEEN_LINKS_FILE = Path(".seen_links.json")
DATE_PATTERN = re.compile(r"(\w+\s\d{1,2},\s\d{4})|(\d{4}-\d{2}-\d{2})")
ADS_SIGNALS = {"googleads", "gclid", "utm_source", "fbclid", "affiliate", "pixel"}
TRACKING_PARAMS = {
    "fbclid", "gclid", "msclkid", "ref", "ref_src", "utm_campaign",
    "utm_content", "utm_medium", "utm_source", "utm_term",
}
INDUSTRIES = [
    "AI", "Marketing", "E-commerce", "Software", "WordPress", "Hosting",
    "Finance", "Online Education", "Travel", "Game", "Remote Work Tools",
    "Digital Tools & Services", "Pet Products", "Baby Products",
]


def clean_and_normalize_url(raw):
    if not raw:
        return ""
    value = str(raw).strip()
    match = re.search(r'href=["\']([^"\']+)["\']', value)
    value = match.group(1) if match else re.sub(r"<.*?>", "", value).strip()
    if not value:
        return ""
    if value.startswith("//"):
        return "https:" + value
    if not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


def canonical_url(raw_url):
    url = clean_and_normalize_url(raw_url)
    if not url:
        return ""
    parsed = urlparse(url)
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in TRACKING_PARAMS
        )
    )
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))


def link_id(raw_url):
    canonical = canonical_url(raw_url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16] if canonical else ""


def load_seen_links():
    if not SEEN_LINKS_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_LINKS_FILE.read_text(encoding="utf-8"))
        links = data.get("links", {}) if isinstance(data, dict) else {}
        return links if isinstance(links, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen_links(seen_links):
    SEEN_LINKS_FILE.write_text(
        json.dumps({"links": seen_links}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def result_link_ids(info):
    urls = [info.get("Link thông tin dự án", ""), info.get("Link đăng ký", "")]
    return {current_id for url in urls if (current_id := link_id(url))}


def is_seen_result(info, seen_links):
    ids = result_link_ids(info)
    return bool(ids and ids.intersection(seen_links))


def mark_result_seen(info, seen_links):
    seen_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for label, raw_url in (
        ("project", info.get("Link thông tin dự án", "")),
        ("signup", info.get("Link đăng ký", "")),
    ):
        current_id = link_id(raw_url)
        if current_id:
            seen_links[current_id] = {
                "url": canonical_url(raw_url),
                "title": info.get("Tiêu đề", ""),
                "type": label,
                "seen_at": seen_at,
            }
    save_seen_links(seen_links)


@st.cache_resource
def get_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def extract_domain(url):
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


@st.cache_data(ttl=7200)
def get_pagespeed_metrics(url):
    if not PAGESPEED_API_KEY or not url:
        return None
    try:
        response = get_session().get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={
                "url": url,
                "key": PAGESPEED_API_KEY,
                "category": ["performance", "seo", "best-practices"],
            },
            timeout=12,
        )
        response.raise_for_status()
        categories = response.json().get("lighthouseResult", {}).get("categories", {})
        return {
            "Performance": categories.get("performance", {}).get("score", 0),
            "SEO": categories.get("seo", {}).get("score", 0),
            "Best Practices": categories.get("best-practices", {}).get("score", 0),
        }
    except requests.RequestException:
        return None


def google_search(query, num_results):
    items = []
    for start in range(1, num_results + 1, 10):
        try:
            response = get_session().get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": API_KEY, "cx": CSE_ID, "q": query, "start": start},
                timeout=12,
            )
            response.raise_for_status()
            items.extend(response.json().get("items", []))
        except requests.RequestException as exc:
            st.error(f"Không thể truy vấn Google ở trang {start // 10 + 1}: {exc}")
            break
    return items[:num_results]


@st.cache_data(ttl=3600)
def has_ads_signals(url):
    try:
        response = get_session().get(
            url,
            timeout=6,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AffiScout/1.0)"},
            allow_redirects=True,
        )
        response.raise_for_status()
        source = response.text.lower()
        return any(signal in source for signal in ADS_SIGNALS)
    except requests.RequestException:
        return False


def extract_project_date(item):
    for tag in item.get("pagemap", {}).get("metatags", []):
        for key in (
            "article:published_time", "datepublished", "datecreated",
            "og:published_time", "og:release_date",
        ):
            if tag.get(key):
                parsed = pd.to_datetime(tag[key], errors="coerce")
                return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else str(tag[key])
    match = DATE_PATTERN.search(item.get("snippet", ""))
    if match:
        parsed = pd.to_datetime(match.group(0), errors="coerce")
        return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else match.group(0)
    return "Chưa xác định"


def get_project_info(item):
    link = item.get("link", "").strip()
    signup_link = link
    for tag in item.get("pagemap", {}).get("metatags", []):
        for key in ("affiliate_link", "registration_url", "signup_url"):
            if tag.get(key):
                signup_link = clean_and_normalize_url(tag[key])
                break
    return {
        "Tiêu đề": item.get("title", "Dự án chưa có tên").strip(),
        "Mô tả": item.get("snippet", "").strip(),
        "Domain": extract_domain(link),
        "Link thông tin dự án": link,
        "Link đăng ký": signup_link,
        "Thời gian ra mắt": extract_project_date(item),
        "PageSpeed Metrics": get_pagespeed_metrics(link),
    }


def logo_style(domain):
    palette = [
        ("#eef2ff", "#4f46e5"), ("#ecfdf5", "#059669"),
        ("#fff7ed", "#ea580c"), ("#fdf2f8", "#db2777"),
        ("#eff6ff", "#2563eb"), ("#f5f3ff", "#7c3aed"),
    ]
    return palette[sum(ord(char) for char in domain) % len(palette)]


def score_from_metrics(info):
    metrics = info.get("PageSpeed Metrics") or {}
    scores = [float(value or 0) * 100 for value in metrics.values()]
    return round(sum(scores) / len(scores)) if scores else None


def render_card(info, index):
    title = html.escape(info.get("Tiêu đề") or "Dự án chưa có tên")
    domain = html.escape(info.get("Domain") or "unknown")
    description = html.escape(info.get("Mô tả") or "Chưa có mô tả cho dự án này.")
    if len(description) > 150:
        description = description[:147].rstrip() + "…"
    launch_date = html.escape(info.get("Thời gian ra mắt") or "Chưa xác định")
    bg, fg = logo_style(domain)
    initial = html.escape((domain[:1] or title[:1]).upper())
    score = score_from_metrics(info)
    score_html = f'<span class="quality-badge">{score}/100</span>' if score is not None else '<span class="quality-badge neutral">Đã xác minh</span>'

    st.markdown(
        f"""
        <article class="program-card">
          <div class="program-head">
            <div class="program-logo" style="background:{bg};color:{fg}">{initial}</div>
            {score_html}
          </div>
          <div class="program-domain">{domain}</div>
          <h3>{title}</h3>
          <p class="program-description">{description}</p>
          <div class="program-meta">
            <div><span>Loại chương trình</span><strong>Affiliate · CPS</strong></div>
            <div><span>Phát hiện</span><strong>{launch_date}</strong></div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )
    action_a, action_b = st.columns([1, 1])
    project_link = clean_and_normalize_url(info.get("Link thông tin dự án", ""))
    signup_link = clean_and_normalize_url(info.get("Link đăng ký", ""))
    with action_a:
        st.link_button("Xem dự án", project_link or "https://google.com", use_container_width=True)
    with action_b:
        st.link_button("Đăng ký ↗", signup_link or project_link or "https://google.com", use_container_width=True)


st.markdown(
    """
    <style>
      :root { color-scheme: light; }
      .stApp { background: #f7f8fa; color: #171a21; }
      header[data-testid="stHeader"] { background: rgba(247,248,250,.88); backdrop-filter: blur(12px); }
      #MainMenu, footer { visibility: hidden; }
      .block-container { max-width: 1480px; padding: 2.25rem 2.6rem 4rem; }
      section[data-testid="stSidebar"] { width: 310px !important; background: #ffffff; border-right: 1px solid #e8eaee; }
      section[data-testid="stSidebar"] > div { padding: 1.25rem 1.15rem; }
      section[data-testid="stSidebar"] .stMarkdown h2 { color: #111318; font-size: 1.08rem; margin: 0; }
      section[data-testid="stSidebar"] label { color: #4b515d !important; font-size: .82rem !important; font-weight: 650 !important; }
      section[data-testid="stSidebar"] [data-baseweb="select"] > div,
      section[data-testid="stSidebar"] input { background: #f8f9fb; border-color: #e2e5ea; border-radius: 10px; }
      section[data-testid="stSidebar"] hr { border-color: #eceef1; margin: 1rem 0; }
      .brand { display:flex; gap:11px; align-items:center; padding: 3px 1px 18px; }
      .brand-mark { width:36px; height:36px; display:grid; place-items:center; border-radius:11px; background:#111318; color:white; font-weight:850; }
      .brand-name { font-weight:800; color:#111318; line-height:1.05; }
      .brand-sub { color:#8b9099; font-size:.72rem; margin-top:4px; }
      .sidebar-kicker { color:#a0a5ae; font-size:.68rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:10px 0 4px; }
      .api-ready, .api-missing { display:flex; align-items:center; gap:8px; font-size:.76rem; border-radius:9px; padding:9px 11px; }
      .api-ready { background:#ecfdf3; color:#087443; }
      .api-missing { background:#fff7ed; color:#9a4d08; }
      .api-dot { width:7px; height:7px; border-radius:50%; background:currentColor; }
      .eyebrow { color:#717782; font-size:.72rem; font-weight:800; letter-spacing:.13em; text-transform:uppercase; margin-bottom:11px; }
      .hero { display:flex; justify-content:space-between; align-items:flex-end; gap:30px; border-bottom:1px solid #e4e6ea; padding: 2px 0 26px; margin-bottom:25px; }
      .hero h1 { color:#111318; font-size:clamp(2rem,4vw,3.35rem); line-height:1.02; letter-spacing:-.055em; margin:0; font-weight:830; }
      .hero p { max-width:620px; color:#6d737e; font-size:.98rem; margin:13px 0 0; line-height:1.65; }
      .hero-stat { min-width:170px; background:#111318; color:#fff; border-radius:16px; padding:17px 19px; box-shadow:0 12px 30px rgba(17,19,24,.12); }
      .hero-stat span { display:block; color:#aeb3bc; font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; }
      .hero-stat strong { display:block; font-size:1.7rem; margin-top:3px; }
      .toolbar { display:flex; align-items:center; justify-content:space-between; margin:4px 0 18px; }
      .toolbar h2 { color:#171a21; font-size:1.05rem; margin:0; }
      .toolbar span { color:#858b95; font-size:.82rem; }
      .program-card { height:290px; box-sizing:border-box; background:#fff; border:1px solid #e4e6ea; border-bottom:0; border-radius:16px 16px 0 0; padding:21px 21px 16px; transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease; }
      .program-card:hover { transform:translateY(-2px); box-shadow:0 14px 36px rgba(27,32,44,.08); border-color:#d5d8de; }
      .program-head { display:flex; justify-content:space-between; align-items:flex-start; }
      .program-logo { width:48px; height:48px; display:grid; place-items:center; border-radius:14px; font-size:1.12rem; font-weight:850; }
      .quality-badge { color:#087443; background:#ecfdf3; border:1px solid #d4f6e2; border-radius:999px; padding:5px 8px; font-size:.67rem; font-weight:750; }
      .quality-badge.neutral { color:#616874; background:#f4f5f7; border-color:#e9eaed; }
      .program-domain { color:#8b909a; font-size:.7rem; margin-top:16px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .program-card h3 { color:#171a21 !important; font-size:1rem; line-height:1.35; margin:5px 0 7px; height:2.7em; overflow:hidden; }
      .program-description { color:#727883; font-size:.79rem; line-height:1.55; height:3.7em; overflow:hidden; margin:0 0 17px; }
      .program-meta { display:grid; grid-template-columns:1fr 1fr; gap:12px; border-top:1px solid #eff0f2; padding-top:13px; }
      .program-meta span { display:block; color:#a0a5ae; font-size:.63rem; margin-bottom:4px; }
      .program-meta strong { color:#424751; display:block; font-size:.72rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      div[data-testid="stVerticalBlock"]:has(> div .program-card) { gap:0 !important; margin-bottom:20px; }
      div[data-testid="stVerticalBlock"]:has(> div .program-card) > div:has(.stLinkButton) { background:#fff; border:1px solid #e4e6ea; border-top:1px solid #eff0f2; padding:12px; }
      .stLinkButton a { border-radius:9px; border-color:#dfe2e7; color:#343942; font-size:.76rem; font-weight:700; min-height:37px; background:#fff; }
      .stLinkButton a:hover { border-color:#171a21; color:#171a21; background:#f8f9fa; }
      .stButton > button[kind="primary"] { background:#171a21; color:white; border:1px solid #171a21; border-radius:10px; min-height:43px; font-weight:750; }
      .stButton > button[kind="primary"]:hover { background:#30343b; border-color:#30343b; }
      section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) { border-radius:10px; border-color:#e1e4e8; font-size:.78rem; }
      .empty-state { text-align:center; background:#fff; border:1px dashed #d9dce1; border-radius:18px; padding:65px 25px; }
      .empty-icon { margin:auto; width:54px; height:54px; display:grid; place-items:center; border-radius:16px; background:#f1f3f5; color:#555c67; font-size:1.25rem; }
      .empty-state h3 { color:#272b32 !important; margin:16px 0 7px; font-size:1rem; }
      .empty-state p { color:#858b95; font-size:.82rem; margin:0; }
      [data-testid="stAlert"] { border-radius:12px; font-size:.85rem; }
      @media (max-width: 900px) { .block-container{padding:1.5rem 1rem 3rem}.hero{align-items:flex-start;flex-direction:column}.hero-stat{width:100%;box-sizing:border-box}.program-card{height:auto;min-height:280px} }
    </style>
    """,
    unsafe_allow_html=True,
)


if "ket_qua_loc" not in st.session_state:
    st.session_state.ket_qua_loc = []
if "seen_links" not in st.session_state:
    st.session_state.seen_links = load_seen_links()


with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-mark">A</div>
          <div><div class="brand-name">AffiScout</div><div class="brand-sub">Affiliate intelligence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-kicker">Bộ lọc khám phá</div>', unsafe_allow_html=True)
    with st.form("search_form"):
        industry = st.selectbox("Ngành hàng", INDUSTRIES)
        domain_filter = st.text_input("Tên miền", placeholder="Ví dụ: canva.com")
        keyword = st.text_input("Từ khóa bổ sung", placeholder="Ví dụ: plugin, creator")
        result_count = st.slider("Số kết quả Google", 10, 50, 20, step=10)
        submitted = st.form_submit_button("Tìm chương trình", type="primary", use_container_width=True)

    st.divider()
    hide_seen = st.checkbox("Ẩn chương trình đã xem", value=True)
    if st.button("Xóa lịch sử đã xem", use_container_width=True):
        st.session_state.seen_links = {}
        save_seen_links({})
        st.rerun()
    st.caption(f"Đã lưu {len(st.session_state.seen_links)} liên kết.")
    api_class = "api-ready" if API_KEY and CSE_ID else "api-missing"
    api_text = "Google Search đã kết nối" if API_KEY and CSE_ID else "Chưa cấu hình Google API"
    st.markdown(
        f'<div class="{api_class}"><span class="api-dot"></span>{api_text}</div>',
        unsafe_allow_html=True,
    )


if submitted:
    domain_filter = domain_filter.strip().lower()
    keyword = keyword.strip()
    if not API_KEY or not CSE_ID:
        st.error("Thiếu GOOGLE_API_KEY hoặc GOOGLE_CSE_ID. Hãy cấu hình trong tệp .env hoặc biến môi trường.")
    else:
        query_parts = [industry, "affiliate program"]
        if keyword:
            query_parts.append(keyword)
        if domain_filter:
            query_parts.append(f"site:{domain_filter}")
        with st.spinner("Đang quét và phân tích các chương trình phù hợp…"):
            results = google_search(" ".join(query_parts), result_count)
            filtered_results = []
            progress = st.progress(0, text="Đang kiểm tra tín hiệu affiliate")
            total = max(len(results), 1)
            for index, item in enumerate(results):
                link = item.get("link", "").strip()
                if (not domain_filter or domain_filter in link.lower()) and has_ads_signals(link):
                    filtered_results.append(get_project_info(item))
                progress.progress((index + 1) / total, text=f"Đã phân tích {index + 1}/{len(results)} kết quả")
            progress.empty()
            filtered_results.sort(
                key=lambda row: pd.to_datetime(row["Thời gian ra mắt"], errors="coerce")
                if row["Thời gian ra mắt"] != "Chưa xác định" else pd.Timestamp.min,
                reverse=True,
            )
            st.session_state.ket_qua_loc = filtered_results


all_results = st.session_state.ket_qua_loc
visible_results = [
    info for info in all_results
    if not (hide_seen and is_seen_result(info, st.session_state.seen_links))
]

st.markdown(
    f"""
    <div class="eyebrow">Program marketplace</div>
    <section class="hero">
      <div>
        <h1>Khám phá chương trình<br>affiliate tiềm năng.</h1>
        <p>Tìm kiếm, sàng lọc và đánh giá các dự án đang có tín hiệu quảng cáo — trong một workspace rõ ràng, tập trung.</p>
      </div>
      <div class="hero-stat"><span>Chương trình phù hợp</span><strong>{len(visible_results):02d}</strong></div>
    </section>
    <div class="toolbar"><h2>Chương trình dành cho bạn</h2><span>Hiển thị {len(visible_results)} / {len(all_results)} kết quả</span></div>
    """,
    unsafe_allow_html=True,
)

if visible_results:
    for row_start in range(0, len(visible_results), 3):
        columns = st.columns(3, gap="medium")
        for offset, info in enumerate(visible_results[row_start:row_start + 3]):
            with columns[offset]:
                render_card(info, row_start + offset)
                if st.button("Đánh dấu đã xem", key=f"seen-{row_start + offset}-{link_id(info.get('Link thông tin dự án', ''))}", use_container_width=True):
                    mark_result_seen(info, st.session_state.seen_links)
                    st.rerun()

    export_rows = [
        {
            "Tiêu đề": info["Tiêu đề"],
            "Domain": info["Domain"],
            "Mô tả": info["Mô tả"],
            "Link thông tin": info["Link thông tin dự án"],
            "Link đăng ký": info["Link đăng ký"],
            "Thời gian ra mắt": info["Thời gian ra mắt"],
        }
        for info in visible_results
    ]
    st.download_button(
        "Tải danh sách CSV",
        pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8-sig"),
        "affiscout_programs.csv",
        "text/csv",
        use_container_width=False,
    )
else:
    st.markdown(
        """
        <div class="empty-state">
          <div class="empty-icon">⌕</div>
          <h3>Chưa có chương trình để hiển thị</h3>
          <p>Chọn ngành hoặc nhập tên miền ở bộ lọc bên trái, sau đó bắt đầu tìm kiếm.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
