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
- Tìm bằng tối đa 6 truy vấn theo ngách thay vì một truy vấn duy nhất. Dùng tối đa 6 lượt API khi chọn 10–30 kết quả, 12 khi chọn 50, 18 khi chọn 100. Có thể trả ít hơn số đã chọn.
- Chấm điểm theo tiêu đề/mô tả, URL chương trình, thông tin tham gia/hoa hồng và từ khóa. Đây là điểm quy tắc, không phải xác suất hoặc xác nhận trang chính thức.
- Mặc định bỏ bài tổng hợp/hướng dẫn; có tùy chọn bao gồm bài tham khảo. Gộp subdomain theo tên miền đăng ký (hỗ trợ co.uk và tên miền nền tảng riêng), tối đa một kết quả mỗi tên miền gốc.
- Kết quả là ứng viên chương trình affiliate. Không yêu cầu mã Ads trừ khi bật bộ lọc tương ứng. Chỉ AW conversion ID hoặc URL conversion cụ thể được ghi nhận là mã Ads; affiliate, pixel, gclid hoặc Google Analytics riêng lẻ không được coi là Google Ads.
- Tín hiệu HTML không chứng minh website đang mua Google Ads. Trang tải lỗi vẫn có thể xuất hiện với nhãn “Chưa kiểm tra được”.
- Xem bằng chứng, truy vấn nguồn và trạng thái affiliate trong phần chi tiết hoặc file xuất.
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
python -m unittest test_search_api test_discovery
```

Kiểm tra dùng dữ liệu giả lập, không tiêu tốn credits. Cần key thật để kiểm tra kết nối Serper thực tế.
