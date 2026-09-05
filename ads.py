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
from pathlib import Path
from search_api import search_serper
from discovery import inspect_html

load_dotenv(Path(__file__).with_name('.env'))

def setting(name):
    value = os.getenv(name)
    if value is None:
        try:
            value = st.secrets.get(name, '')
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            value = ''
    return str(value).strip()

SERPER_API_KEY = setting('SERPER_API_KEY')
PAGESPEED_API_KEY = setting('PAGESPEED_API_KEY')

# Pre-compiled regex for better performance
DATE_PATTERN = re.compile(r'(\w+\s\d{1,2},\s\d{4})|(\d{4}-\d{2}-\d{2})')

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


def search_projects(query, num_results):
    return search_serper(get_session(), query, num_results, SERPER_API_KEY)


@st.cache_data(ttl=3600)
def has_ads_signals(url):
    """Separate affiliate evidence from specific Ads conversion tags."""
    try:
        session = get_session()
        response = session.get(
            url, 
            timeout=5, 
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )
        response.raise_for_status()
        evidence = inspect_html(response.text)
        evidence['final_url'] = response.url
        return evidence
    except requests.exceptions.RequestException:
        return {'affiliate': False, 'ads': [], 'checked': False}


def extract_project_date(item):
    """Extract and standardize project date from item metadata"""
    pagemap = item.get("pagemap", {})
    date = item.get('date')
    
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
        "Ngày nội dung": date_ra_mat,
        "PageSpeed Metrics": pagespeed_metrics
    }


from ui import render

render(st, pd, search_projects, has_ads_signals, get_project_info, extract_domain)
