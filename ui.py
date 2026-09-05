"""AffiScan's light dashboard, rendered with native Streamlit controls."""
from pathlib import Path
from time import perf_counter
import json
from search_api import SearchError


def render(st, pd, search, detect, project_info, extract_domain):
    st.set_page_config(page_title="AffiScan · Affiliate Research", page_icon="🔎", layout="wide")
    st.markdown('<style>' + Path(__file__).with_name('style.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)
    st.markdown('''<nav class="nav"><a class="brand" href="#"><span class="brand-icon">⌕</span>Affi<span>Scan</span><small>Beta</small></a><div class="nav-links"><a class="active" href="#">⌂ &nbsp; Trang chủ</a><a href="#huong-dan">ⓘ &nbsp; Hướng dẫn</a><a href="#ket-qua">▤ &nbsp; Kết quả</a></div><a class="docs" href="#huong-dan">▣ &nbsp; Tài liệu hướng dẫn</a></nav>
<section class="hero"><div class="hero-copy"><span class="eyebrow">✧ Công cụ SEO & Affiliate Marketing</span><h1>AffiScan - Bộ Lọc Dự Án <em>Affiliate</em><br>Có Quảng Cáo <em>Google</em></h1><p>Tìm kiếm, phân tích và lọc các dự án/website affiliate có dấu hiệu quảng cáo Google<br>để khám phá từ khóa, ngách tiềm năng và cơ hội kinh doanh.</p></div><div class="hero-art"><div class="orbit"></div><div class="analytics"><div class="window-dots">● ● ●</div><div class="ad-logo">A</div><b>Google Ads</b><div class="search-line">⌕</div><div class="bars"><i></i><i></i><i></i><i></i></div></div><div class="float-card data">▥ <span>Dữ liệu thực tế<br><b>Cập nhật liên tục</b></span></div><div class="float-card growth">↗ <span>Tìm cơ hội<br><b>Nhanh hơn</b></span></div><div class="float-card shield">◆ <span>Phân tích đối thủ<br><b>dễ dàng</b></span></div></div></section>''', unsafe_allow_html=True)
    industries = ['WordPress', 'AI', 'Marketing', 'Edu LMS', 'Travel', 'Game', 'Bitcoin', 'finance app', 'E-commerce', 'Digital Tools & Services', 'Hosting', 'Online Education', 'Software', 'Baby Products', 'Remote Work Tools', 'Hosting & Website Building', 'Pet Products']
    for key, value in dict(ket_qua_loc=[], elapsed=0, searched=False, keywords='', count=20).items():
        st.session_state.setdefault(key, value)

    def reset():
        st.session_state.update(industry='WordPress', domains='', keyword='', count=20, ket_qua_loc=[], elapsed=0, searched=False, keywords='')

    left, right = st.columns([1.55, 1], gap='small')
    with left, st.container(border=True):
        heading, reset_col = st.columns([4, 1])
        with heading:
            st.markdown('<div class="section-heading">▾ &nbsp; Bộ lọc dự án</div><div class="subtitle">Thiết lập tiêu chí để tìm kiếm các dự án affiliate phù hợp với nhu cầu của bạn.</div>', unsafe_allow_html=True)
        with reset_col:
            st.button('↻ Đặt lại', on_click=reset, use_container_width=True)
        with st.form('filters', border=False):
            a, b = st.columns(2)
            with a:
                industry = st.selectbox('♙ Chọn ngành', industries, key='industry')
            with b:
                domains = st.text_input('◎ Tên miền (domain)', placeholder='Ví dụ: wordpress.com, barn2.com', key='domains')
            a, b = st.columns(2)
            with a:
                keyword = st.text_input('⌕ Từ khóa bổ sung (tùy chọn)', placeholder='Ví dụ: plugin, theme, hosting, 2026...', key='keyword')
                st.caption('Thêm từ khóa liên quan đến ngách hoặc sản phẩm.')
            with b:
                count = st.selectbox('☷ Số kết quả', [10, 20, 30, 50, 100], key='count')
                st.caption('Tối đa 100 kết quả. Các domain cách nhau bằng dấu phẩy.')
            submitted = st.form_submit_button('⌕  Bắt đầu lọc dự án  →', type='primary', use_container_width=True)
    with right:
        benefits = [('green', '◎', 'Tiết kiệm thời gian', 'Tìm nhanh các dự án có tín hiệu quảng cáo thay vì tìm thủ công.'), ('blue', '▥', 'Dữ liệu đáng tin cậy', 'Tra cứu từ Google, phân tích tín hiệu trên website.'), ('orange', '♧', 'Tìm cơ hội dễ dàng', 'Phát hiện ngách tiềm năng, đối thủ và từ khóa cho chiến lược affiliate.'), ('purple', '◈', 'Hỗ trợ SEO & Marketing', 'Phù hợp cho blogger, affiliate marketer, SEOer và website review.')]
        st.markdown('<div class="benefits">' + ''.join(f'<div class="benefit {color}"><span>{icon}</span><div><b>{title}</b><p>{copy}</p></div></div>' for color, icon, title, copy in benefits) + '</div>', unsafe_allow_html=True)
        stats = st.empty()
    if submitted:
        started = perf_counter()
        with st.spinner('Đang truy vấn Google và phân tích website...'):
            try:
                hosts = [extract_domain('https://' + d.strip().removeprefix('https://').removeprefix('http://')).lower() for d in domains.split(',') if d.strip()]
                query = industry + ' affiliate project ' + keyword.strip()
                if hosts:
                    query += ' (' + ' OR '.join('site:' + d for d in hosts) + ')'
                results = search(query, count)[:count]
                rows = []
                progress = st.progress(0)
                for idx, item in enumerate(results):
                    link = item.get('link', '').strip()
                    host = extract_domain(link).lower()
                    if (not hosts or any(host == d or host.endswith('.' + d) for d in hosts)) and detect(link):
                        row = project_info(item)
                        row.update({'Ngành': industry, 'Từ khóa liên quan': keyword.strip() or industry})
                        rows.append(row)
                    progress.progress((idx + 1) / len(results))
                progress.empty()
                def date_key(row):
                    value = pd.to_datetime(row.get('Thời gian ra mắt'), errors='coerce', utc=True)
                    return value.value if pd.notna(value) else -9223372036854775808
                rows.sort(key=date_key, reverse=True)
                st.session_state.update(ket_qua_loc=rows, elapsed=round(perf_counter() - started, 1), searched=True, keywords=keyword.strip() or industry)
            except SearchError as exc:
                st.error(str(exc))
                st.info('Lượt tìm kiếm chưa hoàn tất. Kết quả của lần tìm trước (nếu có) được giữ lại.')
            except Exception as exc:
                st.error(f'Không thể hoàn tất tìm kiếm: {type(exc).__name__}')
    rows = st.session_state.ket_qua_loc
    counts = [('▣', len(rows), 'Dự án tìm thấy'), ('◎', len({r['Domain'] for r in rows}), 'Domain có tín hiệu'), ('⌕', len(st.session_state.keywords.split()) if rows else 0, 'Từ khóa tìm kiếm'), ('ϟ', f'{st.session_state.elapsed}s', 'Thời gian quét')]
    stats.markdown('<div class="stats">' + ''.join(f'<div><strong><i>{icon}</i> {value}</strong><small>{label}</small></div>' for icon, value, label in counts) + '</div>', unsafe_allow_html=True)
    with st.container(border=True):
        title, csv_col, save_col = st.columns([5, 1, 1.2])
        with title:
            st.markdown('<div id="ket-qua" class="section-heading">▦ &nbsp; Kết quả lọc dự án</div><div class="subtitle">Danh sách các dự án/website phù hợp với tiêu chí của bạn.</div>', unsafe_allow_html=True)
        export = [{k: v for k, v in r.items() if k != 'PageSpeed Metrics'} for r in rows]
        with csv_col:
            st.download_button('⇩ Xuất CSV', pd.DataFrame(export).to_csv(index=False).encode('utf-8-sig'), 'affiscan.csv', 'text/csv', disabled=not rows, use_container_width=True)
        with save_col:
            st.download_button('♧ Lưu kết quả', json.dumps(rows, ensure_ascii=False, indent=2), 'affiscan.json', 'application/json', disabled=not rows, use_container_width=True)
        if rows:
            table = [{'#': i, 'Domain': r['Domain'], 'Tên dự án': r['Tiêu đề'], 'Ngành': r.get('Ngành', ''), 'Từ khóa liên quan': r.get('Từ khóa liên quan', ''), 'Quảng cáo': 'Có tín hiệu', 'Hành động': r['Link thông tin dự án']} for i, r in enumerate(rows, 1)]
            st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True, column_config={'Hành động': st.column_config.LinkColumn('Hành động', display_text='Xem dự án ↗')})
            st.caption('Tín hiệu trên website không xác nhận dự án đang chạy Google Ads.')
            with st.expander('Chi tiết dự án & PageSpeed'):
                for row in rows:
                    st.write('**' + row['Tiêu đề'] + '**')
                    st.write(row['Mô tả'])
                    st.write('Thời gian ra mắt: ' + row['Thời gian ra mắt'])
                    st.link_button('Đăng ký / xem dự án ↗', row['Link đăng ký'])
                    if row.get('PageSpeed Metrics'):
                        st.json(row['PageSpeed Metrics'])
        else:
            message = 'Không tìm thấy kết quả phù hợp' if st.session_state.searched else 'Chưa có kết quả'
            st.markdown(f'<div class="empty-table"><div class="table-head"><span>#</span><span>Domain</span><span>Tên dự án</span><span>Ngành</span><span>Từ khóa liên quan</span><span>Quảng cáo</span><span>Hành động</span></div><div class="empty"><div class="empty-icon">⌕</div><b>{message}</b><p>Vui lòng thiết lập bộ lọc và nhấn “Bắt đầu lọc dự án” để xem kết quả.</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div id="huong-dan"></div>', unsafe_allow_html=True)
    with st.expander('ⓘ Hướng dẫn sử dụng'):
        st.write('Chọn ngành, nhập tên miền hoặc từ khóa tùy chọn, rồi nhấn Bắt đầu lọc dự án. Xuất CSV để mở kết quả trong Excel hoặc Lưu kết quả để tải dữ liệu JSON.')
        st.caption('Kết quả lấy qua Google Custom Search. Phát hiện quảng cáo dựa trên tín hiệu trong mã HTML của website.')
