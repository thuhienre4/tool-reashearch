# AffiScout — Affiliate Marketplace

Ứng dụng Streamlit để tìm, lọc và đánh giá các website có chương trình affiliate dựa trên ngành hàng, tên miền và từ khóa.

## Chay tool

Can dung Python 64-bit de cai Streamlit/Pandas on dinh. Python 32-bit tren Windows co the loi khi cai `pandas`.

```powershell
pip install -r requirements.txt
streamlit run ads.py
```

Mo trinh duyet tai:

```text
http://localhost:8501
```

## Cau hinh Google Search

Giao diện vẫn mở được khi chưa có API key, nhưng cần Google Custom Search để chạy tìm kiếm.

Muon quet tu dong ket qua Google:

1. Copy `.env.example` thành `.env`
2. Điền `GOOGLE_API_KEY`
3. Điền `GOOGLE_CSE_ID`
4. Chạy lại ứng dụng

## Dau vao

- Ngành hàng
- Tên miền tùy chọn, ví dụ `example.com`
- Từ khóa bổ sung, ví dụ `hosting`, `creator`, `plugin`
- Số lượng kết quả Google cần phân tích

## Dau ra

- Link dự án và link đăng ký
- Ngày phát hiện/phát hành
- Chỉ số PageSpeed nếu có cấu hình `PAGESPEED_API_KEY`
- Lưu và ẩn các link đã xem
- Xuất CSV
