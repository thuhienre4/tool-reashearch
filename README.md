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
- **Đuôi tên miền**: chọn một hoặc nhiều đuôi như `.com`, `.io`, `.ai`, `.com.vn`, `.co.uk`. Để trống để tìm mọi đuôi. Các đuôi được kết hợp bằng OR, còn domain cụ thể và các bộ lọc khác áp dụng đồng thời. Kiểm tra cả URL kết quả và URL sau chuyển hướng. `.com` không khớp `.com.vn`; `.vn` bao gồm `.com.vn`.
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

## Lọc dự án mới và traffic

Mở **Dự án mới, độ phù hợp & lượt truy cập** trong bộ lọc:

- Chọn **Ngày nội dung trên Google** để lọc nội dung trong 3/6/12 tháng. App thêm mốc ngày vào truy vấn và kiểm tra lại ngày trong kết quả. Đây không phải ngày ra mắt dự án; ngày thiếu hoặc không đọc được sẽ không vượt bộ lọc.
- Chọn **Ngày ra mắt từ báo cáo** nếu có nguồn xác nhận ngày ra mắt trong CSV. App không tự xác minh nội dung nguồn và không suy ra ngày ra mắt từ tuổi domain/ngày bài viết.
- Đặt **Lượt truy cập/tháng tối thiểu**, ví dụ 10000. Đặt 0 để không lọc traffic. Chỉ dùng số liệu của tháng đã hoàn tất, trong 3 tháng gần nhất; dữ liệu thiếu/cũ bị loại.
- Chọn điểm phù hợp tối thiểu. Điểm này đánh giá độ phù hợp affiliate theo quy tắc, không dự đoán lợi nhuận hoặc tăng trưởng.

Serper không cung cấp lượt truy cập. Trong **Dữ liệu ngày ra mắt & traffic**, tải mẫu CSV rồi điền từ báo cáo bạn có quyền sử dụng. Không bắt buộc mua thêm API. Schema:

```text
domain,monthly_visits,traffic_month,traffic_source,launched_at,launch_source
```

`domain` bắt buộc. Traffic cần đủ `monthly_visits` (số nguyên không dấu phân cách), `traffic_month` (YYYY-MM) và `traffic_source` (nhà cung cấp/báo cáo). Ngày ra mắt cần `launched_at` (YYYY-MM-DD) và `launch_source` (nguồn công bố). Có thể bỏ trống một nhóm nếu không có. Mỗi tên miền gốc chỉ có một dòng; tối đa 5.000 dòng và 2 MB, UTF-8. Dữ liệu chỉ lưu trong phiên làm việc Streamlit, không ghi lên GitHub.

Số liệu nhà cung cấp có thể là ước tính. Bảng và file xuất ghi rõ tháng và nguồn để kiểm tra lại. Không có dữ liệu được giữ là trống, không biến thành 0 lượt.

## Lỗi cấu hình/dịch vụ

- Thiếu key/401: kiểm tra `SERPER_API_KEY`.
- 403: kiểm tra quyền key và trạng thái tài khoản Serper.
- 402: kiểm tra credits.
- 429: giảm tần suất và kiểm tra hạn mức.
- Lỗi mạng/5xx: thử lại sau.

## Kiểm tra

```bash
python -m unittest test_search_api test_discovery test_project_filters test_ui
```

Kiểm tra dùng dữ liệu giả lập, không tiêu tốn credits. Cần key thật để kiểm tra kết nối Serper thực tế.
