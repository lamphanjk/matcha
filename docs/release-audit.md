# Matcha v0.1.0-rc.2: phạm vi thay đổi

Đối chiếu với commit `ba359123e3dd537ade3197b01a53390a73207bac` của bản fork.
Đây là bản thử nghiệm, chưa xác nhận tích hợp trên site Frappe/ERPNext v15 thật.

## Mã xử lý chứng từ

| Phần | Kết quả kiểm tra |
|---|---|
| `reconcile`, `reconcile_xco`, undo và helper trong `payment_reconciliation.py` | AST giống bản gốc, ngoại trừ `get_exceptions` |
| `api/reconciliation.py`, `api/transactions.py` | Nội dung giống bản gốc |
| Hooks, scheduler và patches | Không thay đổi |
| Store frontend | 40 hàm giống bản gốc. Chỉ `loadExceptions` và `changeDateFilter` thay đổi |
| Allocation, gửi lệnh reconcile, undo, chuyển Exceptions sang Reconcile | Không thay đổi hàm xử lý |

Không thêm lệnh tự submit, tự phân bổ hoặc tự tạo Journal Entry khi tìm kiếm.
Các API mới chỉ đọc dữ liệu và metadata.
Kiểm tra tĩnh không chứng minh toàn bộ luồng chạy đúng trên mọi site.

## Những hành vi có thay đổi

- Exceptions dùng quyền đọc của người dùng qua `frappe.get_list`.
- Company, ngày hạch toán và Party giới hạn cả Payment và Invoice.
- Customer lấy SI. Supplier lấy PI. Mã Party đi cùng loại Party để tránh trùng tên.
- Tìm mã hóa đơn chỉ lọc Invoice. Custom field không lọc Payment.
- Mặc định Exceptions vẫn lấy hóa đơn còn dư nợ từ 30 ngày tuổi và toàn bộ thời gian.
- Có thể xem hóa đơn đã tất toán. Nút Reconcile của dòng có dư nợ bằng 0 bị khóa.
- Phân trang hóa đơn không còn giới hạn cứng 500 bản ghi.
- Tổng công nợ bao gồm mọi hóa đơn Submitted phù hợp với khoảng ngày, kể cả hóa đơn đã tất toán và trả hàng.
- Total paid bằng Total billing trừ Total unpaid, nên gồm cả cấn trừ và điều chỉnh.
- Tổng dùng tiền tệ tài khoản công nợ. Các tiền tệ khác nhau không cộng chung.
- Khoảng ngày chọn hóa đơn theo posting date. Dư nợ thể hiện trạng thái hiện tại, không phải số dư lịch sử.
- `get_exceptions` không còn trả hai khóa tổng cũ `total_si_amount` và `total_pi_amount`.
  Frontend trong repo không sử dụng chúng. Cần kiểm tra nếu server có tích hợp riêng gọi API này.

Không thể mô tả bản này là thay đổi giao diện thuần túy.
Tập chứng từ hiển thị có thể khác bản cũ vì bộ lọc và quyền đọc.
Người dùng vẫn quyết định chứng từ để đối soát bằng luồng Reconcile hiện có.

## Thay đổi dữ liệu cấu hình

Chỉ bổ sung ba field vào DocType Single `Matcha Settings`:

| Field | Loại | Tác dụng |
|---|---|---|
| `section_invoice_fields` | Section Break | Bố cục form |
| `invoice_fields_editor` | HTML | Giao diện chọn field |
| `invoice_field_config` | Code / JSON | Lưu lựa chọn Display và Filter trong `tabSingles` |

Các field intercompany cũ và quyền của Matcha Settings giữ nguyên.
Chỉ chạy validation field khi cấu hình field thay đổi hoặc khi tạo settings mới.
Không sửa DocType Sales Invoice, Purchase Invoice, Payment Entry hoặc GL Entry.
Không thêm patch chuyển đổi dữ liệu tài chính.

## Sửa lỗi phát hiện trong lần rà soát phát hành

Đã sửa tiền tệ Payment trong Exceptions về quy tắc bản gốc:
Receive dùng `paid_from_account_currency`, Pay dùng `paid_to_account_currency`.
Bản làm việc trước lần rà soát đã đảo hai nguồn này.
Lỗi chỉ nằm ở tiền tệ hiển thị, không đổi số tiền hoặc hàm ghi sổ.

## Kiểm tra có thể chạy lại

Chạy từ thư mục app với Python từ 3.10 và dependency frontend đã cài:

```bash
python3 scripts/audit_release.py
node scripts/audit_reconciliation.mjs
python3 -m unittest discover -s tests -v
node --test tests/test_settings_requests.mjs
```

Hai script audit so sánh với commit baseline cố định.
Nếu clone thiếu lịch sử, fetch tag baseline trước khi chạy.
Các unit test dùng Frappe giả lập, không thay thế kiểm thử database thật.

Lần kiểm tra phát hành này có 14 unit test đạt yêu cầu.
Có thêm ba kiểm thử Desk script cho HTTP method và xử lý lỗi tải metadata trong Settings.
Frontend build thành công bằng dependency từ `frontend/package-lock.json`, với Vite 6.4.1.
Lockfile không thay đổi so với baseline.
`npm audit --omit=dev` không báo lỗ hổng ở dependency production tại thời điểm kiểm tra.
Audit toàn bộ dependency báo 12 cảnh báo ở nhóm phát triển/build.
Nhóm này chưa được nâng phiên bản trong đợt cập nhật để giữ phạm vi thay đổi.
Không dùng Vite dev server làm server production.

## Bản vá rc.2 cho Matcha Settings

Traceback production chỉ ra lỗi tại bước `is_valid_http_method`, trước khi chạy hàm đọc metadata.
`frappe.call` mặc định gửi POST, trong khi `get_invoice_fields` chỉ cho phép GET.
Đã thêm `type: 'GET'` ở lời gọi Settings và giữ nguyên whitelist GET phía server.
Đã xử lý rejection của từng loại Invoice và lỗi khi refresh form.
Không thay đổi quyền đọc, schema, hoặc hàm xử lý chứng từ trong bản vá này.
Các unit test dùng mô phỏng request contract v15, chưa thay thế kiểm tra lại trên server production.

## Điều kiện trước khi dùng trên production

Trên bench test riêng, kiểm tra đủ các trường hợp sau:

| Trường hợp | Bằng chứng cần đối chiếu |
|---|---|
| Đối soát một Payment vào một Invoice | Phân bổ, dư nợ, log và GL/Payment Ledger đúng như bản gốc |
| Chia một Payment vào nhiều Invoice | Tổng phân bổ, số còn lại và làm tròn đúng |
| Nhiều Payment vào Invoice | Không vượt dư nợ, không tạo phân bổ trùng |
| Ngoại tệ, tỷ giá khác nhau | Tiền tệ, chênh lệch tỷ giá và chứng từ phát sinh đúng |
| Intercompany / XCO | Bridge account, Journal Entry liên kết và số dư đúng |
| Credit note, debit note, Journal Entry | Dấu số tiền và tham chiếu đúng |
| Undo sau reconcile | Log, tham chiếu và dư nợ trở về trạng thái mong đợi |
| Chỉ xem/tìm/lọc | Không đổi Invoice, Payment, GL Entry hoặc Payment Ledger |
| Quyền Accounts User và Accounts Manager | Không lộ chứng từ hoặc field ngoài quyền |
| Settings | Sửa bridge account và chọn custom field đều lưu được đúng quyền |
| RC → baseline → RC | App mở được, thao tác đối soát và settings hoạt động ở mỗi lần chuyển |
| Dữ liệu lớn | Đo thời gian đọc tổng công nợ và Exceptions, theo dõi worker |

Đối chiếu hai phiên bản từ hai bản sao cùng một snapshot database.
Chỉ tìm kiếm dữ liệu không chạy hàm hạch toán, nhưng truy vấn vẫn sử dụng tài nguyên worker.
Không cam kết không có issue trước khi hoàn thành các kiểm thử tích hợp này.

## Nguồn đối chiếu

- [ERPNext v15 Payment Entry](https://github.com/frappe/erpnext/blob/version-15/erpnext/accounts/doctype/payment_entry/payment_entry.py)
- [Frappe migrate](https://docs.frappe.io/framework/user/en/bench/reference/migrate)
- [Frappe restore](https://docs.frappe.io/framework/user/en/bench/reference/restore)
