"""Serper search adapter with safe failures and paginated organic results."""
import requests


class SearchError(Exception):
    """Messages safe to display without exposing API credentials."""


def search_serper(session, query, count, api_key):
    api_key = api_key.strip()
    if not api_key or api_key == 'your_serper_api_key_here':
        raise SearchError('Thiếu SERPER_API_KEY. Lấy key tại serper.dev rồi thêm vào Streamlit Settings → Secrets hoặc file .env. Không cần Google API key hoặc CSE ID.')
    if any(char.isspace() for char in api_key):
        raise SearchError('SERPER_API_KEY chứa khoảng trắng không hợp lệ. Vui lòng sao chép lại key.')
    count = min(max(int(count), 1), 100)
    items, seen = [], set()
    for page in range(1, (count + 9) // 10 + 1):
        try:
            response = session.post('https://google.serper.dev/search',
                headers={'X-API-KEY': api_key},
                json={'q': query, 'num': 10, 'page': page}, timeout=20)
        except requests.RequestException:
            raise SearchError('Không kết nối được Serper. Vui lòng thử lại sau.') from None
        if response.status_code >= 400:
            hints = {
                400: 'Serper từ chối tham số tìm kiếm. Thử lại với từ khóa khác.',
                401: 'SERPER_API_KEY không hợp lệ. Kiểm tra key trong Serper Dashboard.',
                403: 'Serper từ chối quyền truy cập. Kiểm tra key và trạng thái tài khoản Serper.',
                402: 'Không đủ credits Serper. Kiểm tra số dư trong Serper Dashboard.',
                429: 'Serper giới hạn lượt gọi. Kiểm tra hạn mức và thử lại sau.',
            }
            raise SearchError(f'Serper (HTTP {response.status_code}): ' + hints.get(response.status_code, 'Dịch vụ tìm kiếm gặp lỗi. Vui lòng thử lại sau.'))
        try:
            data = response.json()
        except ValueError:
            raise SearchError('Serper trả về phản hồi không hợp lệ. Vui lòng thử lại sau.') from None
        if not isinstance(data, dict) or not isinstance(data.get('organic'), list):
            raise SearchError('Serper trả về dữ liệu không hợp lệ. Vui lòng thử lại sau.')
        organic = data['organic']
        if any(not isinstance(item, dict) for item in organic):
            raise SearchError('Serper trả về kết quả không hợp lệ.')
        for item in organic:
            link = item.get('link', '')
            if not isinstance(link, str) or not link.startswith(('https://', 'http://')) or link in seen:
                continue
            seen.add(link)
            items.append({'title': str(item.get('title') or link), 'link': link,
                          'snippet': str(item.get('snippet') or ''), 'date': item.get('date')})
        if len(items) >= count or len(organic) < 10:
            break
    return items[:count]
