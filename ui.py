"""AffiScan's light dashboard, rendered with native Streamlit controls."""
from pathlib import Path
from time import perf_counter
import json
from search_api import SearchError
from discovery import discover, root_domain, matches_suffix
from datetime import date
from project_filters import read_metrics, passes_filters, months_ago, METRICS_TEMPLATE


def render(st, pd, search, detect, project_info, extract_domain):
    st.set_page_config(page_title="AffiScan · Affiliate Research", page_icon="🔎", layout="wide")
    st.markdown('<style>' + Path(__file__).with_name('style.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)
    st.markdown('''<nav class="nav"><a class="brand" href="#"><span class="brand-icon">⌕</span>Affi<span>Scan</span><small>Beta</small></a><div class="nav-links"><a class="active" href="#">⌂ &nbsp; Trang chủ</a><a href="#huong-dan">ⓘ &nbsp; Hướng dẫn</a><a href="#ket-qua">▤ &nbsp; Kết quả</a></div><a class="docs" href="#huong-dan">▣ &nbsp; Tài liệu hướng dẫn</a></nav>
<section class="hero"><div class="hero-copy"><span class="eyebrow">✧ Công cụ SEO & Affiliate Marketing</span><h1>AffiScan - Bộ Lọc Dự Án <em>Affiliate</em><br>Có Quảng Cáo <em>Google</em></h1><p>Tìm kiếm, phân tích và lọc các dự án/website affiliate có dấu hiệu quảng cáo Google<br>để khám phá từ khóa, ngách tiềm năng và cơ hội kinh doanh.</p></div><div class="hero-art"><div class="orbit"></div><div class="analytics"><div class="window-dots">● ● ●</div><div class="ad-logo">A</div><b>Google Ads</b><div class="search-line">⌕</div><div class="bars"><i></i><i></i><i></i><i></i></div></div><div class="float-card data">▥ <span>Dữ liệu thực tế<br><b>Cập nhật liên tục</b></span></div><div class="float-card growth">↗ <span>Tìm cơ hội<br><b>Nhanh hơn</b></span></div><div class="float-card shield">◆ <span>Phân tích đối thủ<br><b>dễ dàng</b></span></div></div></section>''', unsafe_allow_html=True)
    industries = ['WordPress', 'AI', 'Marketing', 'Edu LMS', 'Travel', 'Game', 'Bitcoin', 'finance app', 'E-commerce', 'Digital Tools & Services', 'Hosting', 'Online Education', 'Software', 'Baby Products', 'Remote Work Tools', 'Hosting & Website Building', 'Pet Products']
    for key, value in dict(ket_qua_loc=[], elapsed=0, searched=False, keywords='', count=20, discovery_stats={}, include_roundups=False, require_ads=False, new_basis='Không lọc', new_months=6, min_visits=0, min_score=50, suffixes=[]).items():
        st.session_state.setdefault(key, value)

    def reset():
        st.session_state.update(industry='WordPress', domains='', keyword='', count=20, ket_qua_loc=[], elapsed=0, searched=False, keywords='', discovery_stats={}, include_roundups=False, require_ads=False, new_basis='Không lọc', new_months=6, min_visits=0, min_score=50, suffixes=[])

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
            st.multiselect('Đuôi tên miền', ['.com', '.io', '.ai', '.net', '.org', '.co', '.app', '.dev', '.tech', '.store', '.xyz', '.me', '.info', '.biz', '.vn', '.com.vn', '.uk', '.co.uk', '.us', '.de', '.fr', '.ca', '.au', '.com.au'], key='suffixes', placeholder='Tất cả đuôi tên miền')
            st.caption('Chọn nhiều đuôi để tìm kết quả thuộc bất kỳ đuôi nào đã chọn. Để trống = tất cả; bộ lọc domain cụ thể vẫn áp dụng đồng thời.')
            st.checkbox('Bao gồm bài tổng hợp / hướng dẫn', key='include_roundups')
            st.checkbox('Chỉ giữ trang có mã Google Ads', key='require_ads')
            with st.expander('Dự án mới, độ phù hợp & lượt truy cập'):
                st.selectbox('Lọc độ mới theo', ['Không lọc', 'Ngày nội dung trên Google', 'Ngày ra mắt từ báo cáo'], key='new_basis')
                st.selectbox('Trong khoảng thời gian', [3, 6, 12], format_func=lambda value: f'{value} tháng gần đây', key='new_months')
                st.number_input('Lượt truy cập/tháng tối thiểu (0 = không lọc)', min_value=0, step=10000, key='min_visits')
                st.slider('Điểm phù hợp tối thiểu', 0, 100, key='min_score')
                st.caption('Ngày nội dung không phải ngày ra mắt. Ngày ra mắt và traffic lấy từ báo cáo bạn nhập ở bên phải. Thiếu dữ liệu sẽ bị loại khi bật bộ lọc tương ứng. Traffic chỉ dùng tháng đã hoàn tất trong 3 tháng gần nhất.')
            st.caption('Ưu tiên trang chương trình, tối đa 1 kết quả mỗi tên miền gốc. Tìm rộng dùng tối đa 6–18 lượt Serper, tùy số kết quả; có thể tìm được ít hơn số đã chọn.')
            submitted = st.form_submit_button('⌕  Bắt đầu lọc dự án  →', type='primary', use_container_width=True)
    with right:
        benefits = [('green', '◎', 'Tiết kiệm thời gian', 'Tìm nhanh các dự án có tín hiệu quảng cáo thay vì tìm thủ công.'), ('blue', '▥', 'Dữ liệu đáng tin cậy', 'Tra cứu từ Google, phân tích tín hiệu trên website.'), ('orange', '♧', 'Tìm cơ hội dễ dàng', 'Phát hiện ngách tiềm năng, đối thủ và từ khóa cho chiến lược affiliate.'), ('purple', '◈', 'Hỗ trợ SEO & Marketing', 'Phù hợp cho blogger, affiliate marketer, SEOer và website review.')]
        st.markdown('<div class="benefits">' + ''.join(f'<div class="benefit {color}"><span>{icon}</span><div><b>{title}</b><p>{copy}</p></div></div>' for color, icon, title, copy in benefits) + '</div>', unsafe_allow_html=True)
        stats = st.empty()
        with st.expander('Dữ liệu ngày ra mắt & traffic'):
            st.caption('Nhập báo cáo CSV có nguồn. Số traffic có thể là ước tính của nhà cung cấp; app không tự xác minh báo cáo và không suy ra traffic từ thứ hạng Google.')
            metrics_file = st.file_uploader('Báo cáo CSV (UTF-8)', type=['csv'], key='metrics_upload')
            st.download_button('Tải mẫu cột CSV', METRICS_TEMPLATE, 'project_metrics_template.csv', 'text/csv')
            st.caption('domain, monthly_visits, traffic_month (YYYY-MM), traffic_source, launched_at (YYYY-MM-DD), launch_source. Chỉ điền các nhóm dữ liệu bạn có; số lượt không có dấu phân cách.')
    if submitted:
        started = perf_counter()
        with st.spinner('Đang truy vấn Google và phân tích website...'):
            try:
                metrics = {}
                if metrics_file is not None:
                    if metrics_file.size > 2 * 1024 * 1024:
                        raise SearchError('Báo cáo CSV tối đa 2 MB.')
                    try:
                        metrics = read_metrics(metrics_file.getvalue())
                    except ValueError as exc:
                        raise SearchError(str(exc)) from None
                if st.session_state.min_visits and not any(row['monthly_visits'] is not None for row in metrics.values()):
                    raise SearchError('Bộ lọc traffic cần báo cáo có monthly_visits, traffic_month và traffic_source. Nhập CSV hoặc đặt ngưỡng về 0; Serper không cung cấp số traffic.')
                if st.session_state.new_basis == 'Ngày ra mắt từ báo cáo' and not any(row['launched_at'] for row in metrics.values()):
                    raise SearchError('Lọc dự án mới cần ngày ra mắt và nguồn trong CSV. Bạn có thể chọn lọc ngày nội dung Google nếu chưa có báo cáo ngày ra mắt.')
                age = 0 if st.session_state.new_basis == 'Không lọc' else st.session_state.new_months
                basis = 'launch' if st.session_state.new_basis == 'Ngày ra mắt từ báo cáo' else 'content'
                def matches(item, domain=None):
                    return passes_filters(item, metrics.get(domain or item['root_domain'], {}), age, basis, st.session_state.min_visits, st.session_state.min_score)
                hosts = [extract_domain('https://' + d.strip().removeprefix('https://').removeprefix('http://')).lower() for d in domains.split(',') if d.strip()]
                suffixes = st.session_state.suffixes
                if hosts and suffixes and not any(matches_suffix(host, suffixes) for host in hosts):
                    raise SearchError('Domain cụ thể không thuộc đuôi tên miền đã chọn. Đổi đuôi hoặc xóa domain để tiếp tục.')
                after = months_ago(date.today(), age).isoformat() if age and basis == 'content' else None
                results, discovery_stats = discover(search, industry, keyword.strip(), hosts, count, st.session_state.include_roundups, candidate_filter=matches, recent_after=after, suffixes=suffixes)
                rows = []
                final_domains = set()
                progress = st.progress(0)
                for idx, item in enumerate(results):
                    link = item.get('link', '').strip()
                    evidence = detect(link)
                    final_link = evidence.get('final_url', link)
                    final_host = extract_domain(final_link).lower()
                    final_domain = root_domain(final_link)
                    allowed = (not hosts or any(final_host == d or final_host.endswith('.' + d) for d in hosts)) and matches_suffix(final_link, suffixes)
                    if allowed and final_domain not in final_domains and matches(item, final_domain) and (not st.session_state.require_ads or evidence['ads']):
                        row = project_info(item)
                        record = metrics.get(final_domain, {})
                        final_domains.add(final_domain)
                        row.update({'Domain': final_domain, 'Ngành': industry, 'Từ khóa liên quan': keyword.strip() or industry,
                                    'Điểm phù hợp': item['rank_score'],
                                    'Loại trang': 'Bài tham khảo' if item['roundup'] else 'Ứng viên chương trình',
                                    'Affiliate': 'Có nội dung chương trình trên trang' if evidence['affiliate'] else 'Theo kết quả tìm kiếm; cần xác minh',
                                    'Google Ads': 'Có mã theo dõi Ads' if evidence['ads'] else 'Không thấy mã Ads' if evidence['checked'] else 'Chưa kiểm tra được',
                                    'Bằng chứng': '; '.join(item['reasons'] + evidence['ads']),
                                    'Truy vấn nguồn': item['source_query'], 'URL sau chuyển hướng': final_link})
                        row.update({'Ngày nội dung': str(item.get('date') or 'Chưa có dữ liệu'),
                                    'Ngày ra mắt (báo cáo)': record.get('launched_at') or 'Chưa có dữ liệu',
                                    'Nguồn ngày ra mắt': record.get('launch_source', ''),
                                    'Lượt truy cập/tháng (báo cáo)': record.get('monthly_visits'),
                                    'Tháng traffic': record.get('traffic_month', ''),
                                    'Nguồn traffic': record.get('traffic_source', '')})
                        rows.append(row)
                    progress.progress((idx + 1) / len(results))
                progress.empty()
                st.session_state.update(ket_qua_loc=rows, elapsed=round(perf_counter() - started, 1), searched=True, keywords=keyword.strip() or industry, discovery_stats=discovery_stats)
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
            table = [{'#': i, 'Domain': r['Domain'], 'Tên dự án': r['Tiêu đề'], 'Ngành': r.get('Ngành', ''), 'Điểm phù hợp': r.get('Điểm phù hợp', 0), 'Ngày nội dung': r.get('Ngày nội dung', 'Chưa có dữ liệu'), 'Ngày ra mắt (báo cáo)': r.get('Ngày ra mắt (báo cáo)', 'Chưa có dữ liệu'), 'Lượt truy cập/tháng': r.get('Lượt truy cập/tháng (báo cáo)'), 'Tháng traffic': r.get('Tháng traffic', ''), 'Google Ads': r.get('Google Ads', 'Chưa xác minh'), 'Hành động': r['Link thông tin dự án']} for i, r in enumerate(rows, 1)]
            st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True, column_config={'Hành động': st.column_config.LinkColumn('Hành động', display_text='Xem dự án ↗')})
            st.caption('Điểm phù hợp là điểm xếp hạng theo quy tắc, không phải xác suất chính xác. Mã Google Ads không chứng minh chiến dịch đang chạy. Trang chương trình vẫn cần xác minh trước khi tham gia.')
            with st.expander('Chi tiết dự án & PageSpeed'):
                for row in rows:
                    st.write('**' + row['Tiêu đề'] + '**')
                    st.write(row['Mô tả'])
                    st.write('Affiliate: ' + row.get('Affiliate', 'Chưa xác minh'))
                    st.write('Bằng chứng: ' + row.get('Bằng chứng', ''))
                    st.write('Truy vấn nguồn: ' + row.get('Truy vấn nguồn', ''))
                    st.write('Ngày nội dung Google: ' + row.get('Ngày nội dung', 'Chưa có dữ liệu'))
                    st.write('Ngày ra mắt theo báo cáo: ' + row.get('Ngày ra mắt (báo cáo)', 'Chưa có dữ liệu'))
                    st.write('Nguồn ngày ra mắt: ' + row.get('Nguồn ngày ra mắt', ''))
                    visits = row.get('Lượt truy cập/tháng (báo cáo)')
                    st.write('Traffic: ' + ('Chưa có dữ liệu' if visits is None else f"{visits:,} lượt — {row.get('Tháng traffic', '')}"))
                    st.write('Nguồn traffic: ' + row.get('Nguồn traffic', ''))
                    st.link_button('Đăng ký / xem dự án ↗', row['Link đăng ký'])
                    if row.get('PageSpeed Metrics'):
                        st.json(row['PageSpeed Metrics'])
        else:
            message = 'Không tìm thấy kết quả phù hợp' if st.session_state.searched else 'Chưa có kết quả'
            st.markdown(f'<div class="empty-table"><div class="table-head"><span>#</span><span>Domain</span><span>Tên dự án</span><span>Ngành</span><span>Từ khóa liên quan</span><span>Quảng cáo</span><span>Hành động</span></div><div class="empty"><div class="empty-icon">⌕</div><b>{message}</b><p>Vui lòng thiết lập bộ lọc và nhấn “Bắt đầu lọc dự án” để xem kết quả.</p></div></div>', unsafe_allow_html=True)
    if st.session_state.discovery_stats:
        summary = st.session_state.discovery_stats
        st.caption(f"Đã tìm bằng {summary['queries']} truy vấn, đánh giá {summary['candidates']} URL khác nhau và giữ {len(rows)} tên miền. Không thêm kết quả kém phù hợp chỉ để đủ số lượng.")
    st.markdown('<div id="huong-dan"></div>', unsafe_allow_html=True)
    with st.expander('ⓘ Hướng dẫn sử dụng'):
        st.write('Chọn ngành, nhập tên miền hoặc từ khóa tùy chọn, rồi nhấn Bắt đầu lọc dự án. Xuất CSV để mở kết quả trong Excel hoặc Lưu kết quả để tải dữ liệu JSON.')
        st.caption('Kết quả tìm kiếm Google được cung cấp qua Serper. Phát hiện quảng cáo dựa trên tín hiệu trong mã HTML của website.')
        st.write('Cấu hình SERPER_API_KEY trong Streamlit Settings → Secrets. Không cần Google API key hoặc CSE ID. Mỗi lần lọc có thể dùng nhiều lượt API tùy số kết quả.')
