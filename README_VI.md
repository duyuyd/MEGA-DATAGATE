# MEGA DataGate

**Cổng tiếp nhận dữ liệu thông minh, ưu tiên chạy cục bộ.** Profile dữ liệu lạ, phát hiện schema drift, kiểm tra theo contract và làm sạch theo quy tắc được duyệt mà không ghi đè file gốc.

> Trạng thái: MVP alpha. Bản hiện tại chạy thật, không cần thư viện runtime bên ngoài; hỗ trợ CSV, TSV, JSONL và NDJSON.

## Vấn đề giải quyết

Đội kỹ thuật thường nhận file từ nhiều nguồn. Tên cột thay đổi, trường biến mất, kiểu dữ liệu không đồng nhất, ô rỗng tăng, khóa bị trùng và định dạng không thống nhất. Công việc xử lý thường bị chia thành nhiều script ngắn hạn.

DataGate cung cấp một quy trình cục bộ thống nhất:

1. **Profile:** đọc dữ liệu theo luồng và tạo snapshot không chứa giá trị thô.
2. **Compare:** so sánh snapshot, phát hiện cột thêm/bớt/đổi kiểu và gợi ý cột có thể được đổi tên.
3. **Validate:** kiểm tra dữ liệu theo contract JSON có thể quản lý bằng Git.
4. **Clean:** chỉ áp dụng các phép biến đổi được khai báo rõ; tạo file mới và audit log.

## Bắt đầu nhanh trên Termux / Linux / macOS

```bash
bash scripts/run_demo.sh
```

Mở các file HTML được tạo trong thư mục `build/demo-*` để xem kết quả. Xem [hướng dẫn bắt đầu bằng tiếng Việt](START_HERE_VI.md) để chạy test và xuất bản repository GitHub riêng.

## Chạy nhanh

Yêu cầu Python 3.11 trở lên; không cần root, không cần tài khoản và không cần mạng khi chạy.

```bash
python -m pip install -e .
datagate inspect examples/incoming_customers.csv --out build/incoming
```

Repository đã kèm `examples/baseline.profile.json`, là snapshot tạo từ bộ dữ liệu mẫu cũ. So sánh schema:

```bash
datagate compare examples/baseline.profile.json build/incoming/profile.json --out build/drift
```

Kiểm tra dữ liệu:

```bash
datagate validate examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out build/validation
```

File mẫu cố ý có lỗi nên lệnh validate sẽ trả exit code `1` và vẫn tạo report.

Làm sạch có kiểm soát:

```bash
datagate clean examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out build/cleaned_customers.csv
```

File gốc không bị ghi đè. Audit được tạo cạnh file đầu ra.

## Dùng trong GitHub Actions

Repository có composite action để chặn pipeline khi dữ liệu không đạt contract:

```yaml
- uses: actions/checkout@v7.0.1
- uses: <OWNER>/MEGA-DATAGATE@v0.1.0
  with:
    input: data/incoming.csv
    contract: data/contracts/incoming.contract.json
    report-directory: .datagate/incoming-report
```

Action tải lên report không chứa giá trị thô và đánh fail job nếu contract không đạt. Thay `<OWNER>` và version bằng repo/tag sau khi phát hành.

## Các lệnh

```text
datagate inspect INPUT [--out DIRECTORY]
datagate compare BASELINE_PROFILE CURRENT_PROFILE [--out DIRECTORY]
datagate contract-init PROFILE_JSON --out NEW_CONTRACT_JSON
datagate validate INPUT --contract CONTRACT_JSON [--out DIRECTORY]
datagate clean INPUT --contract CONTRACT_JSON --out NEW_OUTPUT_FILE
```

## Điểm kỹ thuật cốt lõi

- Đọc file theo luồng; không bắt buộc nạp toàn bộ dataset vào RAM.
- Cardinality nhỏ được đếm chính xác; khi vượt 512 giá trị, chuyển sang HyperLogLog có kích thước cố định.
- Kiểm tra uniqueness dùng SQLite tạm trên đĩa thay vì giữ toàn bộ giá trị trong RAM. Thư mục tạm được xóa khi hoàn tất, nhưng đây không phải cơ chế xóa an toàn kiểu mật mã; cần cân nhắc chính sách lưu trữ nếu dữ liệu cực kỳ nhạy cảm.
- Gợi ý rename có similarity score dạng heuristic nhưng không tự động đổi cột.
- Report không lưu cell value; chỉ ghi chỉ số, field, row number và rule.
- Clean từ chối ghi đè input hoặc output đã tồn tại.

Đây là MVP có giới hạn rõ ràng, chưa phải ETL platform hoàn chỉnh. Xem [đặc tả sản phẩm](docs/PRODUCT_SPEC.md), [kiến trúc](docs/ARCHITECTURE.md), [lộ trình](docs/ROADMAP.md) và [hướng dẫn đóng góp](CONTRIBUTING.md).
