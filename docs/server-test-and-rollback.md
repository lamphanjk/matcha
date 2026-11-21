# Đưa Matcha lên Git và test hai phiên bản

## 1. Mục đích

Hướng dẫn này đưa bản cập nhật lên Git và chuyển phiên bản trên bench test Frappe v15.
Mục tiêu là giữ đường quay lại bản cũ và tách việc test khỏi production.

## 2. Đối tượng

Quản trị viên Git và quản trị viên bench Frappe/ERPNext v15.
Các lệnh server chạy bằng tài khoản quản lý bench.

## 3. Cần có gì trước khi bắt đầu

| Mục | Yêu cầu |
|---|---|
| Repo | `https://github.com/lamphanjk/matcha` |
| Bản gốc | Tag `v0.0.1-baseline`, commit `ba359123e3dd537ade3197b01a53390a73207bac` |
| Bản test | Tag `v0.1.0-rc.4`, app version `0.1.0rc4` |
| Nhánh phát triển | `codex/party-balances-v15`. Chưa cần merge vào `main` |
| Server test | Bench riêng, cùng phiên bản Frappe/ERPNext và các custom app với production |
| Database test | Bản sao có thể phục hồi, không dùng database production để thử reconcile |
| Backup | Database, public/private files và site config, gồm encryption key. Đã thử phục hồi |
| Git server | Working tree sạch. Ghi lại commit thực tế đang chạy trước khi đổi |
| Quản lý dịch vụ | Hướng dẫn dưới dùng bench thông thường. Docker/Cloud cần quy trình restart tương ứng |

Các site chung bench dùng chung mã nguồn app và thường dùng chung assets/process.
Tạo thêm site test trên bench production không cách ly phiên bản Matcha.
Không đổi branch trên bench production để thử riêng một site.
Tắt scheduler, email và tích hợp gửi dữ liệu thật trên bản sao test trước khi sử dụng.

`v0.0.1-baseline` chỉ mô tả mã gốc trong bản fork này.
Nếu commit trên server khác baseline, dùng commit đã ghi từ server làm mốc rollback.
Không đổi hoặc ghi đè tag cũ đã phát hành.

## Cập nhật từ rc.1, rc.2 hoặc rc.3 lên rc.4

Bản rc.4 dùng định dạng tiền theo System Settings và bao gồm bản sửa HTTP method trong Settings của rc.2.
Nếu site đã migrate thành công ở rc.1, bản vá này không có thay đổi schema hoặc patch mới.
Không cần chạy migrate chỉ để sửa định dạng tiền hoặc lỗi GET/POST này.

Từ thư mục bench, đặt `TEST_SITE` thành tên site thật rồi chạy từng lệnh:

```bash
bench --site "$TEST_SITE" set-maintenance-mode on
git -C apps/matcha status --short
git -C apps/matcha fetch matcha-fork refs/tags/v0.1.0-rc.4:refs/tags/v0.1.0-rc.4
git -C apps/matcha switch --detach v0.1.0-rc.4
bench build --app matcha
bench --site "$TEST_SITE" clear-cache
bench --site "$TEST_SITE" clear-website-cache
bench restart
bench --site "$TEST_SITE" set-maintenance-mode off
```

Nếu working tree có thay đổi khác ngoài lockfile đã biết, dừng trước khi switch.
Nếu lệnh lỗi, giữ maintenance mode và kiểm tra lỗi trước khi mở site.
Tải lại trình duyệt rồi mở Matcha Settings.
Trong Network, request `get_invoice_fields` phải dùng GET.
Kiểm tra dấu phân cách và số lẻ theo Number Format và Currency Precision trong System Settings.
USD và VND cùng dùng precision hệ thống, không có ngoại lệ viết riêng trong app.
Nếu bật Use Number Format from Currency, kiểm tra thêm Number Format của Currency.
Tải lại Matcha sau mỗi thay đổi cấu hình hiển thị.
Nếu GET vẫn trả 403 từ hàm đọc Invoice, kiểm tra quyền đọc theo user.
Bản vá không xử lý asset 404 của Frappe hoặc app khác.

## 4. Các bước

### Bước 1 — Đẩy nhánh và tag lên Git

Trên máy phát triển, vào repo con `Matcha/matcha`, không dùng repo cha `Matcha`.
Kiểm tra branch, commit và tag trước khi push:

```bash
git status --short
git log -1 --oneline
git tag --list
git show v0.0.1-baseline --no-patch
git show v0.1.0-rc.4 --no-patch
```

Sau khi commit và hai tag đã được tạo, đẩy đúng ba ref này:

```bash
git push --atomic --set-upstream origin codex/party-balances-v15 refs/tags/v0.0.1-baseline refs/tags/v0.1.0-rc.4
```

Lệnh không cập nhật `main` và không force-push.
Nếu tag chưa tồn tại ở máy phát triển, kiểm tra trạng thái phát hành trước khi tiếp tục.

### Bước 2 — Ghi lại phiên bản và backup bench test

Thay hai giá trị dưới bằng bench và site test thực tế:

```bash
BENCH_DIR=/path/to/isolated/frappe-bench
TEST_SITE=matcha-test.example.com
cd "$BENCH_DIR"
git -C apps/matcha status --short
git -C apps/matcha rev-parse HEAD
git -C apps/frappe rev-parse HEAD
git -C apps/erpnext rev-parse HEAD
bench --site "$TEST_SITE" list-apps
bench --site "$TEST_SITE" backup --with-files --compress
```

Nếu working tree có thay đổi, dừng và lưu chúng thành commit riêng.
Không dùng `git reset --hard` để bỏ qua thay đổi chưa rõ nguồn.
Lưu các SHA và đường dẫn backup vào nhật ký triển khai ngoài thư mục app.
Giữ nguyên commit Frappe/ERPNext trong suốt bài test hai phiên bản.

### Bước 3 — Chuyển sang bản test

```bash
bench --site "$TEST_SITE" set-maintenance-mode on
git -C apps/matcha fetch origin --tags
git -C apps/matcha switch --detach v0.1.0-rc.4
git -C apps/matcha describe --tags --exact-match
```

Tag cố định đúng commit cần test. `git pull` không phải lệnh chọn phiên bản cũ.
Trước migrate, kiểm tra các app khác không có thay đổi hoặc patch đang chờ.
`bench migrate` đồng bộ cả site, không chỉ Matcha.

```bash
bench --site "$TEST_SITE" migrate
bench build --app matcha
bench --site "$TEST_SITE" clear-cache
bench --site "$TEST_SITE" clear-website-cache
bench restart
bench --site "$TEST_SITE" set-maintenance-mode off
```

Release đã chứa SPA build trong `matcha/public/matcha` và entry HTML tương ứng.
Nếu cần tự build lại SPA, chạy trước `bench build`:

```bash
cd "$BENCH_DIR/apps/matcha/frontend"
npm ci
npm run build
cd "$BENCH_DIR"
```

Nếu một lệnh lỗi, giữ maintenance mode và kiểm tra log trước khi mở site.
`bench restart` khởi động lại dịch vụ của bench, không riêng một app.

### Bước 4 — Kiểm thử chức năng

Mở `/matcha` và đăng nhập bằng user test có quyền phù hợp.
Kiểm tra Party, khoảng ngày, custom field và số tổng trước.
Tiếp tục chạy các trường hợp đối soát trong [bảng kiểm tích hợp](release-audit.md).
Ghi lại số dư và chứng từ phát sinh sau mỗi trường hợp.
Đối chiếu cùng dữ liệu đầu vào trên bản gốc.

### Bước 5 — Quay lại mã nguồn cũ

Ví dụ dưới áp dụng khi server ban đầu chạy đúng tag baseline.
Nếu khác, thay tag bằng SHA đã ghi ở Bước 2.
Đóng các tab Matcha đang mở trước khi chuyển phiên bản.

```bash
cd "$BENCH_DIR"
bench --site "$TEST_SITE" set-maintenance-mode on
git -C apps/matcha status --short
git -C apps/matcha switch --detach v0.0.1-baseline
bench build --app matcha
bench --site "$TEST_SITE" clear-cache
bench --site "$TEST_SITE" clear-website-cache
bench restart
bench --site "$TEST_SITE" set-maintenance-mode off
```

Mở lại `/matcha` và tải lại trang để lấy bundle của bản cũ.
Không mặc định chạy migrate ngược.
Bài test này giữ metadata cấu hình bổ sung trong database để kiểm tra tương thích bản cũ.
Không xóa field hoặc dữ liệu trong `tabSingles` để rollback giao diện.
Xác nhận cách rollback này trên bench test trước khi dùng ở nơi khác.

### Bước 6 — Chuyển lại bản test

Lặp Bước 3 với `v0.1.0-rc.4`.
Kiểm tra Matcha Settings, các thao tác đối soát và lịch sử sau lần chuyển.
Nếu bản cũ đã lưu lại Settings, kiểm tra lựa chọn field có còn hay cần cấu hình lại.

### Bước 7 — Phục hồi snapshot khi cần so sánh lại dữ liệu

Đổi Git không hoàn tác Payment Entry, Invoice, Journal Entry, GL hoặc log đã ghi khi test.
Khi cần trạng thái database ban đầu, chỉ phục hồi trên bản sao test có thể bỏ dữ liệu mới.

Đặt code của tất cả app về các SHA đã ghi cùng backup trước.
Đặt site test vào maintenance mode.
Dùng đường dẫn thật của từng file backup:

```bash
bench --site "$TEST_SITE" restore /absolute/path/site-database.sql.gz --with-public-files /absolute/path/site-files.tgz --with-private-files /absolute/path/site-private-files.tgz
bench build --app matcha
bench --site "$TEST_SITE" clear-cache
bench --site "$TEST_SITE" clear-website-cache
bench restart
bench --site "$TEST_SITE" set-maintenance-mode off
```

Giữ site config và encryption key khớp snapshot.
Không dùng `--force` để bỏ qua cảnh báo downgrade.
Không phục hồi backup cũ lên production đang phát sinh giao dịch mới để sửa lỗi giao diện.

## 5. Kết quả

- Hai phiên bản có mốc Git riêng để chọn đúng commit.
- `main` giữ nguyên trong thời gian test.
- Có ghi nhận phiên bản, backup và kết quả bài test RC → baseline → RC.
- Có bằng chứng đối chiếu luồng đối soát trước khi xem xét production.

## 6. Xử lý sự cố

Chưa có lỗi từ server test thực tế để ghi vào bảng xử lý sự cố.
Ghi lại lệnh lỗi, thời điểm, commit và log khi chạy trên server.
Không đưa mật khẩu hoặc site config vào Git khi báo lỗi.

## 7. Ghi chú

Không thể bảo đảm không ảnh hưởng hệ thống chỉ bằng kiểm tra diff và unit test.
Migrate, build và restart cần cửa sổ bảo trì nếu bench đang phục vụ người dùng.
Chưa phát hành bản stable. Chỉ tạo `v0.1.0` sau khi bài test server đạt yêu cầu.
Tài liệu không cần ảnh vì các bước triển khai thực hiện qua terminal.

Tham khảo: [Git tags](https://git-scm.com/docs/git-tag), [Git switch](https://git-scm.com/docs/git-switch),
[Frappe migrate](https://docs.frappe.io/framework/user/en/bench/reference/migrate),
[Frappe restore](https://docs.frappe.io/framework/user/en/bench/reference/restore).
