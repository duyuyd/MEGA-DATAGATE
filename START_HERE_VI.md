# Bắt đầu với MEGA DataGate (Android/Termux hoặc máy tính)

## Chạy bản demo

Yêu cầu Python 3.11 trở lên. DataGate không cần thư viện runtime bên ngoài.

```bash
cd MEGA_DATAGATE_MVP
bash scripts/run_demo.sh
```

Demo sẽ tạo báo cáo profile, báo cáo schema drift, kết quả validation và file đã clean trong `build/demo-*`. Dữ liệu mẫu chứa lỗi có chủ đích nên validation trả `FAIL` nhưng script demo vẫn hoàn tất bình thường.

## Chạy test

```bash
python -m unittest discover -s tests -v
```

## Xuất bản repository GitHub riêng

Cần Git, GitHub CLI (`gh`) và đăng nhập trước bằng `gh auth login`.

```bash
bash scripts/publish_github.sh
```

Script lấy username từ phiên GitHub CLI, tạo repository `MEGA-DATAGATE` riêng và push nhánh `main`. Nó yêu cầu gõ chính xác `PUBLIC` trước khi tạo repository công khai. Script không đụng tới repository MEGA CHECKER.

Nếu repo `MEGA-DATAGATE` đã tồn tại, script sẽ dùng remote `origin` và push `main`; hãy kiểm tra remote trước khi chạy trong trường hợp đó.
