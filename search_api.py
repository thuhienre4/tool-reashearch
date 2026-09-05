"""Google search requests with safe, actionable failures."""
import requests


class SearchError(Exception):
    """Contains only messages safe to display to the user."""


def search_google(session, query, count, api_key, cse_id):
    api_key, cse_id = api_key.strip(), cse_id.strip()
    if not api_key or not cse_id:
        raise SearchError('Thiếu GOOGLE_API_KEY hoặc GOOGLE_CSE_ID. Cấu hình trong Streamlit Secrets hoặc file .env, sau đó chạy lại app.')
    for value in (api_key, cse_id):
        if any(char.isspace() for char in value):
            raise SearchError('API key hoặc Search engine ID chứa khoảng trắng không hợp lệ. Hãy sao chép lại giá trị trong cấu hình.')
    items = []
    for start in range(1, min(max(count, 1), 100) + 1, 10):
        try:
            response = session.get('https://www.googleapis.com/customsearch/v1', params={
                'key': api_key, 'cx': cse_id, 'q': query,
                'start': start, 'num': min(10, count - start + 1),
            }, timeout=10)
        except requests.RequestException:
            raise SearchError('Không kết nối được Google Search. Kiểm tra kết nối mạng rồi thử lại.') from None
        try:
            data = response.json()
        except ValueError:
            raise SearchError('Google trả về phản hồi không hợp lệ. Vui lòng thử lại sau.') from None
        if response.status_code >= 400:
            error = data.get('error', {}) if isinstance(data, dict) else {}
            # Inspect Google's diagnostic, but never echo a request URL or credentials.
            diagnostic = str(error).lower()
            if 'api_key_invalid' in diagnostic or 'api key not valid' in diagnostic or 'keyinvalid' in diagnostic:
                hint = 'GOOGLE_API_KEY không hợp lệ. Kiểm tra hoặc tạo lại API key trong Google Cloud.'
            elif 'quota' in diagnostic or 'dailylimit' in diagnostic or response.status_code == 429:
                hint = 'Đã hết hạn mức Google Search. Kiểm tra quota trong Google Cloud hoặc thử lại sau.'
            elif response.status_code == 403:
                hint = 'Google từ chối quyền truy cập. Kiểm tra quyền dùng Custom Search JSON API và giới hạn API key của project.'
            elif response.status_code == 400:
                hint = 'Google từ chối tham số tìm kiếm. Kiểm tra GOOGLE_CSE_ID: phải là Search engine ID trong Programmable Search Engine, không phải URL hoặc API key. Đồng thời kiểm tra GOOGLE_API_KEY.'
            else:
                hint = 'Dịch vụ Google Search gặp lỗi. Vui lòng thử lại sau.'
            raise SearchError(f'Google Search (HTTP {response.status_code}): {hint}')
        if not isinstance(data, dict):
            raise SearchError('Google trả về dữ liệu không hợp lệ. Vui lòng thử lại sau.')
        items.extend(data.get('items', []))
        if not data.get('queries', {}).get('nextPage'):
            break
    return items[:count]
