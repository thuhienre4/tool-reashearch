import streamlit as st
import requests
import pandas as pd
import os
import re
from functools import lru_cache
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load API credentials from .env locally or environment variables in production
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY", "")
CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")  # Optional: PageSpeed Insights API key

# Pre-compiled regex for better performance
DATE_PATTERN = re.compile(r'(\w+\s\d{1,2},\s\d{4})|(\d{4}-\d{2}-\d{2})')
ADS_SIGNALS = {'googleads', 'gclid', 'utm_source', 'fbclid', 'affiliate', 'pixel'}

# Session with connection pooling and retries
@st.cache_resource
def get_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def extract_domain(url):
    """Extract domain from URL (e.g., wordpress.com from https://wordpress.com/path)"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except:
        return ""


def clean_and_normalize_url(raw):
    """Clean a raw value that may contain HTML anchor tags and normalize to a proper href string."""
    if not raw:
        return ""
    raw = str(raw).strip()
    # Try to extract href from embedded anchor tag
    m = re.search(r'href=["\']([^"\']+)["\']', raw)
    if m:
        href = m.group(1)
    else:
        # Remove any HTML tags and use remaining text
        href = re.sub(r'<.*?>', '', raw).strip()

    if not href:
        return ""
    if href.startswith('//'):
        href = 'https:' + href
    if not href.startswith('http://') and not href.startswith('https://'):
        href = 'http://' + href
    return href


@st.cache_data(ttl=7200)
def get_pagespeed_metrics(url):
    """Get PageSpeed Insights metrics (performance, SEO, accessibility)"""
    if not PAGESPEED_API_KEY:
        return None
    
    try:
        # Use Google's public PageSpeed API (doesn't require key for basic usage)
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            "url": url,
            "key": PAGESPEED_API_KEY,
            "category": ["performance", "seo", "best-practices"]
        }
        session = get_session()
        response = session.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract scores
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        
        metrics = {
            "Performance": categories.get("performance", {}).get("score", 0),
            "SEO": categories.get("seo", {}).get("score", 0),
            "Best Practices": categories.get("best-practices", {}).get("score", 0),
        }
        return metrics
    except Exception as e:
        return None


def google_search(query, num_results):
    """Search Google Custom Search API with error handling"""
    url = "https://www.googleapis.com/customsearch/v1"
    all_items = []
    session = get_session()
    
    for i in range(0, num_results, 10):
        params = {
            "key": API_KEY,
            "cx": CSE_ID,
            "q": query,
            "start": i + 1,
        }
        try:
            res = session.get(url, params=params, timeout=10)
            res.raise_for_status()
            all_items.extend(res.json().get("items", []))
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Lỗi API Google (lần thử {i//10 + 1}): {str(e)}")
            break
    
    return all_items


@st.cache_data(ttl=3600)
def has_ads_signals(url):
    """Check for advertising signals in HTML (cached for 1 hour)"""
    try:
        session = get_session()
        response = session.get(
            url, 
            timeout=5, 
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        response.raise_for_status()
        html_lower = response.text.lower()
        return any(sig in html_lower for sig in ADS_SIGNALS)
    except requests.exceptions.Timeout:
        st.warning(f"⚠️ Timeout khi kiểm tra: {url}")
        return False
    except requests.exceptions.RequestException:
        return False
    except Exception as e:
        st.error(f"❌ Lỗi khi phân tích {url}: {type(e).__name__}")
        return False


def extract_project_date(item):
    """Extract and standardize project date from item metadata"""
    pagemap = item.get("pagemap", {})
    date = None
    
    # Priority 1: Check metatags
    if "metatags" in pagemap:
        for tag in pagemap["metatags"]:
            for key in ["article:published_time", "datepublished", "datecreated", "og:published_time", "og:release_date"]:
                if key in tag:
                    date = tag[key]
                    break
            if date:
                break
    
    # Priority 2: Extract from snippet using regex
    if not date:
        snippet = item.get("snippet", "")
        match = DATE_PATTERN.search(snippet)
        if match:
            date = match.group(0)
    
    # Priority 3: Convert to standardized format
    if date:
        try:
            date_obj = pd.to_datetime(date, errors='coerce')
            if pd.notna(date_obj):
                return date_obj.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
        return str(date)
    
    return "Không rõ"


def get_project_info(item):
    """Extract project information with domain name and performance metrics"""
    title = item.get("title", "Không có tiêu đề").strip()
    link = item.get("link", "").strip()
    snippet = item.get("snippet", "").strip()
    link_dang_ky = link
    
    # Extract domain name
    domain_name = extract_domain(link)
    
    # Try to find registration URL in metatags
    pagemap = item.get("pagemap", {})
    if "metatags" in pagemap:
        for tag in pagemap["metatags"]:
            for key in ["affiliate_link", "registration_url", "signup_url"]:
                if key in tag:
                    link_dang_ky = tag[key].strip()
                    # Clean possible embedded HTML
                    link_dang_ky = clean_and_normalize_url(link_dang_ky)
                    break
    
    date_ra_mat = extract_project_date(item)
    
    # Get PageSpeed metrics (optional, can be None)
    pagespeed_metrics = get_pagespeed_metrics(link)
    
    return {
        "Tiêu đề": title,
        "Mô tả": snippet,
        "Domain": domain_name,
        "Link thông tin dự án": link,
        "Link đăng ký": link_dang_ky,
        "Thời gian ra mắt": date_ra_mat,
        "PageSpeed Metrics": pagespeed_metrics
    }


st.markdown("""
    <style>
    body, .main, .stApp { background-color: #171A1C !important; color: #EAEAEA !important; }
    .stApp { background-color: #171A1C !important; }
    .title-h1 { color: #3A86FF !important; text-align:center !important; font-size: 2.5rem; font-weight: bold; margin-top:30px; margin-bottom:25px;}
    .section-title { color: #3A86FF !important; font-size:1.5rem; text-align:left; font-weight:bold; margin-bottom:16px;}
    .section-title-result { color: #3A86FF !important; font-size:1.5rem; text-align:left; font-weight:bold; margin:32px 0 20px 0; }
    .stSuccess { background: #133c2c !important; color: #EAEAEA !important; border-radius: 8px; padding: 8px; font-weight: bold;}
    .card-affi { background: #1e2124 !important; border: 1px solid #3A86FF !important; border-radius: 8px; padding: 16px; margin-bottom: 15px; box-shadow: 0px 2px 8px 0px #00000022; }
    .card-affi a { color: #66aaff !important; text-decoration: none; font-weight: bold; }
    .card-affi .title { font-size: 18px; color: #3A86FF; }
    .card-affi .desc { color: #EAEAEA; font-style: italic; }
    .card-affi .date { color: #ffd700; font-size: 14px; font-weight: bold;}
    .stButton>button { color: #3A86FF; border-color: #3A86FF; background: #171A1C; border-radius: 8px; padding: 8px 24px; font-weight: bold; }
    .stSlider .st-dq { color: #3A86FF; }
    .stSelectbox label, .stSlider label { color: #EAEAEA !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)


st.markdown("<div class='title-h1'>AffiScan - Bộ Lọc Dự Án Affiliate Có Quảng Cáo Google</div>", unsafe_allow_html=True)
st.markdown("---")


col_spacer_left, col_filter, col_spacer_right = st.columns([1, 2, 1])
with col_filter:
    st.markdown("<div class='section-title'>Bộ lọc</div>", unsafe_allow_html=True)
    nganh = st.selectbox("🔎 Chọn ngành", [
        "Wordpress", "AI", "Marketing", "Edu LMS", "Travel", "Game",
        "Bitcoin", "finance app", "E-commerce", "Digital Tools & Services",
        "Hosting", "Online Education", "Software", "Baby Products",
        "Remote Work Tools", "Hosting & Website Building", "Pet Products"
    ])
    domain = st.text_input("🌐 Tên miền (domain, ví dụ: wordpress.com, barn2.com)", "").strip().lower()
    keyword = st.text_input("🔑 Từ khóa bổ sung (keyword, ví dụ: plugin, 2024...)", "").strip()
    so_ket_qua = st.slider("📊 Số kết quả Google", 10, 50, 20)
    bat_dau = st.button("🚀 Bắt đầu lọc", use_container_width=True)


st.markdown("<div class='section-title-result'>Kết quả lọc dự án</div>", unsafe_allow_html=True)

if 'ket_qua_loc' not in st.session_state:
    st.session_state['ket_qua_loc'] = []


if bat_dau:
    # Input validation
    if not API_KEY or not CSE_ID:
        st.error("❌ Lỗi: Thiếu API credentials. Đặt GOOGLE_API_KEY và GOOGLE_CSE_ID trong environment variables.")
    else:
        with st.spinner("🔍 Đang truy vấn Google và phân tích..."):
            try:
                # Build optimized search query
                query_parts = [nganh, "affiliate project"]
                if keyword:
                    query_parts.append(keyword)
                if domain:
                    query_parts.append(f"site:{domain}")
                query = " ".join(query_parts)
                
                # Get search results
                results = google_search(query, so_ket_qua)
                ket_qua_loc = []
                
                # Process results with progress
                progress_bar = st.progress(0)
                for idx, item in enumerate(results):
                    link = item.get("link", "").strip()
                    
                    # Apply domain filter
                    if domain and domain not in link.lower():
                        continue
                    
                    # Check for ads signals
                    if has_ads_signals(link):
                        info = get_project_info(item)
                        ket_qua_loc.append(info)
                    
                    # Update progress
                    progress_bar.progress(min((idx + 1) / len(results), 1.0))
                
                # Sort by date (newest first)
                ket_qua_loc = sorted(
                    ket_qua_loc, 
                    key=lambda x: pd.to_datetime(x["Thời gian ra mắt"], errors='coerce') 
                                  if x["Thời gian ra mắt"] != "Không rõ" 
                                  else pd.Timestamp.min,
                    reverse=True
                )
                
                st.session_state['ket_qua_loc'] = ket_qua_loc
                
            except Exception as e:
                st.error(f"❌ Lỗi xảy ra: {type(e).__name__}: {str(e)}")


if st.session_state['ket_qua_loc']:
    st.success(f"✅ Tìm thấy {len(st.session_state['ket_qua_loc'])} dự án có dấu hiệu quảng cáo!")
    
    # Display results
    for info in st.session_state['ket_qua_loc']:
        try:
            # Escape HTML in user content
            import html
            title = html.escape(info["Tiêu đề"])
            domain = html.escape(info["Domain"])
            desc = html.escape(info["Mô tả"][:150])  # Limit description length
            link_raw = info.get("Link thông tin dự án", "")
            reg_link_raw = info.get("Link đăng ký", "")
            # Clean and normalize registration link if present
            reg_href = clean_and_normalize_url(reg_link_raw)
            link_href = clean_and_normalize_url(link_raw) or link_raw

            link = html.escape(link_href)
            reg_link = html.escape(reg_href)
            date = html.escape(info["Thời gian ra mắt"])
            
            pagespeed = info.get("PageSpeed Metrics")
            reg_text = f"👉 **Link đăng ký:** [Đăng ký]({reg_link})" if reg_link else "👉 **Link đăng ký:** Không có"
            details_text = f"🔗 **Xem thông tin:** [Chi tiết dự án]({link})"
            metrics_text = ""
            if pagespeed:
                perf_score = int(pagespeed.get("Performance", 0) * 100)
                seo_score = int(pagespeed.get("SEO", 0) * 100)
                bp_score = int(pagespeed.get("Best Practices", 0) * 100)
                perf_color = "🟢" if perf_score >= 80 else "🟡" if perf_score >= 50 else "🔴"
                seo_color = "🟢" if seo_score >= 80 else "🟡" if seo_score >= 50 else "🔴"
                bp_color = "🟢" if bp_score >= 80 else "🟡" if bp_score >= 50 else "🔴"
                metrics_text = f"\n\n📊 Website Performance: {perf_color} Performance {perf_score}/100 | {seo_color} SEO {seo_score}/100 | {bp_color} Best Practices {bp_score}/100"

            st.markdown(f"---\n\n### 📝 {domain} - [{title}]({link})\n\n{desc}{'...' if len(info['Mô tả']) > 150 else ''}\n\n{reg_text}\n\n{details_text}\n\n⏰ Thời gian ra mắt: {date}{metrics_text}")
        except Exception as e:
            st.warning(f"⚠️ Lỗi hiển thị kết quả: {type(e).__name__}")
            continue

    # Export results
    try:
        # Prepare data for CSV (remove PageSpeed Metrics for cleaner export)
        export_data = []
        for info in st.session_state['ket_qua_loc']:
            row = {
                "Tiêu đề": info["Tiêu đề"],
                "Domain": info["Domain"],
                "Mô tả": info["Mô tả"],
                "Link thông tin": info["Link thông tin dự án"],
                "Link đăng ký": info["Link đăng ký"],
                "Thời gian ra mắt": info["Thời gian ra mắt"]
            }
            export_data.append(row)
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            "⬇️ Tải kết quả CSV", 
            csv, 
            "ket_qua_affiscan.csv", 
            "text/csv",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"❌ Lỗi khi xuất CSV: {str(e)}")
else:
    st.info("Không tìm thấy trang nào có dấu hiệu quảng cáo.")

