# AffiScan — tìm kiếm affiliate qua Serper

App dùng kết quả Google từ Serper, lọc domain và kiểm tra tín hiệu quảng cáo/affiliate trong HTML. Giao diện Streamlit, xuất CSV/JSON, PageSpeed tùy chọn.

## Cấu hình trên Streamlit Cloud

1. Đăng ký tại https://serper.dev và lấy API key trong tài khoản của bạn.
2. Mở app → Settings → Secrets, thêm:

```toml
SERPER_API_KEY = "your_serper_api_key_here"
```

3. Save và khởi động lại app.
4. Chọn ngành, nhập từ khóa/domain tùy chọn và bắt đầu lọc.

Không cần `GOOGLE_API_KEY` hoặc `GOOGLE_CSE_ID` nữa. Có thể xóa hai cấu hình cũ. Không đưa key thật vào GitHub. Khi chưa có key, app vẫn mở được và hướng dẫn cấu hình khi tìm kiếm.

## Chạy trên máy

Python 3.10 trở lên. Cài thư viện:

```bash
pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env` cạnh `ads.py`, điền key, rồi chạy:

```bash
streamlit run ads.py
```

Biến môi trường (bao gồm `.env`) được ưu tiên trước Streamlit Secrets. `PAGESPEED_API_KEY` tùy chọn; để trống nếu không cần điểm hiệu năng website.

## Sử dụng

- Tối đa 100 kết quả; nhiều domain cách nhau bằng dấu phẩy.
- Gọi Serper theo trang 10 kết quả. Một lần lọc có thể dùng nhiều lượt API và trả ít hơn số kết quả đã chọn.
- Tín hiệu HTML không chứng minh website đang mua Google Ads.
- Ngày từ kết quả tìm kiếm không nhất thiết là ngày ra mắt dự án; thiếu ngày sẽ hiển thị “Không rõ”.
- CSV hỗ trợ tiếng Việt trong Excel; JSON lưu toàn bộ kết quả.
- API lỗi sẽ giữ kết quả lần trước và báo lỗi, không coi là lượt tìm thành công.

## Khắc phục lỗi

- Thiếu key/401: kiểm tra `SERPER_API_KEY`.
- 403: kiểm tra quyền key và trạng thái tài khoản Serper.
- 402: kiểm tra credits.
- 429: giảm tần suất và kiểm tra hạn mức.
- Lỗi mạng/5xx: thử lại sau.

## Kiểm tra

```bash
python -m unittest test_search_api
```

Kiểm tra dùng dữ liệu giả lập, không tiêu tốn credits. Cần key thật để kiểm tra kết nối Serper thực tế.
