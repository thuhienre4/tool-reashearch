# AffiScan - Bộ Lọc Dự Án Affiliate Có Quảng Cáo Google

**AffiScan** là một công cụ tìm kiếm và phân tích các dự án affiliate có dấu hiệu chạy quảng cáo Google, được xây dựng bằng Streamlit và Google Custom Search API.

## 🎯 Tính Năng

- 🔍 **Tìm kiếm dự án affiliate** theo ngành nghề
- 🎯 **Lọc theo domain** cụ thể
- 🔑 **Tìm kiếm bằng từ khóa** bổ sung
- 📊 **Phân tích Website Performance** (Performance, SEO, Best Practices)
- 💾 **Xuất kết quả CSV** để phân tích ngoài
- ⚡ **Tối ưu hiệu suất** với caching và connection pooling

## 📋 Yêu Cầu

- Python 3.8+
- Tài khoản Google Cloud với API Custom Search được kích hoạt

## 🚀 Cài Đặt

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/affiscan.git
cd affiscan
```

### 2. Tạo Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu Hình API Credentials

1. Tạo file `.env` từ template:
```bash
cp .env.example .env
```

2. Mở `.env` và điền thông tin:

#### Lấy Google Custom Search API Key:

- Truy cập: https://console.cloud.google.com/
- Tạo project mới hoặc chọn project hiện tại
- Kích hoạt "Custom Search API"
- Tạo API Key từ "Credentials"
- Copy `GOOGLE_API_KEY` vào file `.env`

#### Lấy Custom Search Engine ID:

- Truy cập: https://cse.google.com/cse/all
- Tạo search engine mới hoặc chọn cái cũ
- Copy ID vào `GOOGLE_CSE_ID` trong `.env`

#### Google PageSpeed Insights API (Tùy chọn):

- Có thể lấy từ cùng Google Cloud Console
- Nếu không có, app vẫn hoạt động nhưng sẽ không hiển thị performance metrics

**File `.env` ví dụ:**
```env
GOOGLE_API_KEY=AIzaSyCtcz_viHAADq3OIBIvi_is-vCmpb01TEk
GOOGLE_CSE_ID=d3deb6056c8744d3b
PAGESPEED_API_KEY=optional_key_here
```

## 🎮 Chạy Ứng Dụng

```bash
streamlit run ads.py
```

App sẽ tự động mở tại: **http://localhost:8501**

## 📖 Hướng Dẫn Sử Dụng

1. **Chọn Ngành** từ danh sách (Wordpress, AI, Marketing, etc.)
2. **Nhập Domain** (tùy chọn): Lọc kết quả chỉ từ domain này
3. **Nhập Từ Khóa** (tùy chọn): Thêm từ khóa tìm kiếm
4. **Điều Chỉnh Số Kết Quả**: Slider 10-50 kết quả
5. **Click "🚀 Bắt Đầu Lọc"** để bắt đầu tìm kiếm

## 📊 Kết Quả Hiển Thị

Mỗi kết quả hiển thị:
- 📝 **Tên Dự Án + Domain**
- 📄 **Mô Tả** (150 ký tự đầu)
- 📊 **Website Performance** (nếu có PageSpeed API):
  - 🟢 = Tốt (>= 80)
  - 🟡 = Trung bình (50-79)
  - 🔴 = Cần cải thiện (< 50)
- 👉 **Link Đăng Ký**
- 🔗 **Link Thông Tin Chi Tiết**
- ⏰ **Thời Gian Ra Mắt**

## 💾 Xuất Kết Quả

- Nhấn nút **"⬇️ Tải kết quả CSV"** để tải file CSV
- Mở trong Excel hoặc Google Sheets để phân tích

## 🔧 Tối Ưu Hóa

App có các tối ưu hóa sau:

- **Connection Pooling**: Tái sử dụng kết nối HTTP
- **Retry Logic**: Tự động thử lại khi API lỗi
- **Caching**: Cache kết quả kiểm tra ads 1 giờ
- **Regex Pre-compiled**: Biên dịch regex một lần

## 📁 Cấu Trúc Thư Mục

```
affiscan/
├── ads.py                 # Ứng dụng chính
├── requirements.txt       # Dependencies
├── .env.example          # Template biến môi trường
├── .gitignore           # Git ignore file
├── README.md            # File này
└── LICENSE              # Giấy phép (tùy chọn)
```

## 🐛 Troubleshooting

### Lỗi: "API Credentials Missing"
- Đảm bảo file `.env` tồn tại và có `GOOGLE_API_KEY` + `GOOGLE_CSE_ID`
- Kiểm tra API keys có hợp lệ không

### Lỗi: "Timeout khi kiểm tra URL"
- URL nó quá chậm hoặc không phản hồi
- App sẽ skip và tiếp tục với URL tiếp theo

### Không thấy Performance Metrics
- `PAGESPEED_API_KEY` chưa được cấu hình
- Thêm vào `.env` nếu muốn có metrics

## 📝 License

MIT License - Tự do sử dụng và chỉnh sửa

## 🤝 Đóng Góp

Nếu bạn tìm được bug hoặc có ý tưởng cải thiện:
1. Fork repository
2. Tạo branch mới (`git checkout -b feature/improvement`)
3. Commit thay đổi (`git commit -m "Add improvement"`)
4. Push lên branch (`git push origin feature/improvement`)
5. Tạo Pull Request

## 📞 Liên Hệ

Nếu có câu hỏi hoặc vấn đề, vui lòng tạo **Issue** trên GitHub.

## ⭐ Yêu Cầu

Nếu bạn thấy công cụ này hữu ích, hãy **⭐ Star** repository!

---

**Made with ❤️ for Affiliate Marketers**
