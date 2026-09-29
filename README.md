# Giảm dung lượng trang PDF

Ứng dụng desktop (Python + PySide6) quét một thư mục (hoặc cả một ổ đĩa),
tìm mọi file PDF và nén từng trang xuống dưới một giới hạn dung lượng
(KB/trang) do người dùng đặt. Nếu một trang đã dùng độ phân giải và chất
lượng thấp nhất mà vẫn không xuống được mức mong muốn, ứng dụng vẫn giữ kết
quả nén tối đa có thể và báo rõ trạng thái "đã đạt giới hạn nén" cho trang/
file đó thay vì âm thầm thất bại.

## Cách hoạt động

Mỗi trang PDF được render thành ảnh rồi nén lại bằng JPEG, dò một dải DPI
giảm dần (300 → 72) và tại mỗi mức DPI, dò nhị phân chất lượng JPEG để tìm
chất lượng cao nhất vẫn nằm trong giới hạn KB/trang. File PDF kết quả được
dựng lại từ các ảnh đã nén. Cách tiếp cận này phù hợp nhất với PDF dạng scan
(ảnh chụp giấy tờ) — với PDF là văn bản/vector thuần, trang cũng sẽ bị
raster hoá thành ảnh trong quá trình nén.

## Chạy từ mã nguồn

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Build file thực thi (Windows/Ubuntu)

Build cục bộ bằng PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name pdf-page-compressor --icon assets/icon.ico run.py   # Windows
pyinstaller --onefile --windowed --name pdf-page-compressor --icon assets/icon.png run.py    # Linux
```

File thực thi nằm trong `dist/`.

### Build tự động qua GitHub Actions

Workflow tại [`.github/workflows/build.yml`](.github/workflows/build.yml) tự
build song song trên `windows-latest` và `ubuntu-latest` mỗi khi push lên
nhánh `main`, mở pull request, hoặc chạy tay (`workflow_dispatch`). Kết quả
là 2 artifact tải về được:

- `pdf-page-compressor-windows` — chứa `pdf-page-compressor.exe`
- `pdf-page-compressor-linux` — chứa file thực thi ELF `pdf-page-compressor`

Nếu push một tag dạng `vX.Y.Z`, workflow còn tự tạo GitHub Release và đính
kèm 2 bản build (`.zip`) vào release đó.

## Cấu trúc dự án

```
app/
  core/
    scanner.py       # quét thư mục tìm file .pdf
    compressor.py     # engine nén PDF theo trang
    worker.py          # QThread chạy nền, phát tín hiệu tiến trình
  ui/
    main_window.py     # giao diện chính (PySide6)
    styles.py           # theme QSS hiện đại
  main.py               # khởi tạo QApplication
run.py                  # entry point dùng để chạy trực tiếp / build PyInstaller
assets/                 # icon ứng dụng (icon.png, icon.ico)
```

## Giới hạn hiện tại

- Nội dung trang PDF (kể cả văn bản chọn được) bị chuyển thành ảnh JPEG khi
  nén — phù hợp cho PDF scan, nhưng sẽ mất khả năng chọn/copy text trên PDF
  vốn là văn bản thuần.
- Không hỗ trợ PDF có mật khẩu (sẽ báo "Bỏ qua" cho các file này).
