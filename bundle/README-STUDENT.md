# Gói Student — PointPillars trên một PCD KITTI

Nhóm 3–4 người dùng **một máy** chạy pretrained model CPU, đọc ba kết quả A/B/C và nhận lỗi pipeline trước khi sửa cuboid. Gói này dùng mẫu KITTI được phát theo **CC BY-NC-SA 3.0**, không có Robotaxi/VinFast, ảnh camera hay đáp án. Đọc `DATA-LICENSE.txt` và `ATTRIBUTION.md`; chỉ dùng thí nghiệm học thuật phi thương mại, giữ ghi nguồn/giấy phép khi phát bản chuyển đổi.

## 1. Chuẩn bị máy và gói đúng kiến trúc

Cần Docker Desktop Windows/Mac hoặc Docker Engine Linux, **Python 3.10+ trên máy**, Internet để tải ZIP lần đầu. Không cần GPU, tài khoản CVAT hoặc Tailscale để chạy thí nghiệm. Docker dùng **Linux containers**. `amd64` dành Intel/AMD; `arm64` dành Apple Silicon. Windows ARM chưa được thử, không chọn chỉ theo tên hệ điều hành. Bản native Linux amd64 và Mac arm64 phải được kiểm thực tế trước khi phát; kết quả smoke của người vận hành không bảo đảm mọi Windows/RAM đều chạy được.

1. Tải ZIP đúng kiến trúc từ [Releases của repo Student](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/releases).
2. Giải nén vào thư mục local ngắn, ví dụ `C:\Lab13\student-amd64` hoặc `~/Lab13/student-arm64`. Không chạy trong ZIP. Giữ **nguyên gói**, gồm manifest, image, input, practice và giấy phép.
3. Mở Docker, kiểm `docker info`. Có đủ dung lượng chứa ZIP + giải nén + Docker image; giới hạn container 4 GB không phải RAM tối thiểu máy.
4. Chọn người vận hành, người kiểm cấu hình/JSON, người xem hình học, người ghi log; đổi vai. Cần chạy thử trước ca; máy không chạy được dùng máy LC theo lượt.

**Sẵn sàng:** Docker báo Linux/đúng kiến trúc, Python 3.10+, có file `student-bundle.py` và `manifest.json` sau giải nén. Không tách riêng PCD/image khỏi manifest rồi chạy runner.

## 2. Chạy A/B/C

Mở Terminal/PowerShell **trong thư mục giải nén**. Runner kiểm hash, kiến trúc native trước load, load image đúng ID và chạy tuần tự. Dùng thư mục output **mới nằm ngoài gói**; không ghi đè kết quả lần trước. Chạy không dùng mạng trong container, input/code read-only, tối đa 4 CPU/4 GB RAM/container.

Mac/Linux:

```bash
python3 student-bundle.py run --bundle . --out ../ket-qua-nhom-01
```

Windows PowerShell:

```powershell
py -3 student-bundle.py run --bundle . --out ..\ket-qua-nhom-01
```

Nếu không có `py` nhưng đã cài Python, kiểm `python --version`, dùng `python`. Không dùng WSL path với Docker Windows khi chưa kiểm mount. Nếu sai kiến trúc, tải gói đúng; không bật emulation rồi ghi native.

| Lượt | delta (m) | Pillar XY (m) | Đối chiếu |
| --- | ---: | ---: | --- |
| A | 0 | 0.16 | A/B: đổi dịch z trước inference |
| B | 1.73 | 0.16 | Baseline thật để tạo ca lỗi |
| C | 1.73 | 0.32 | B/C: đổi pillar |

Giữ checkpoint KITTI, score 0.3 và front ROI. Runner không train hoặc tự tạo hộp giả. Với đầu vào này, x/y giữ gốc KITTI, z dịch +1.73 m để thực hành hệ nguồn; ground còn được ước lượng từ dữ liệu. Reflectance thật của nguồn **bị bỏ trong bản PCD** để giữ bài adapter kênh hằng, RGB=0 là placeholder. Đây không phải benchmark KITTI dùng intensity thật, không phải gốc mặt đường đo chính xác.

**Kiểm kết quả:** `smoke.json` có `status: passed`; `run-A/B/C` đủ JSON/ảnh Side/CSV; `qc-cases` đủ ba JSON/PNG và manifest trỏ đúng B. Thời gian smoke gồm khởi động/load, không phải số đo RAM. Không ép số hộp trùng một máy khác.

## 3. Phân tích và báo cáo

Mở JSON, ảnh Side và CSV. So A/B và B/C bằng quan sát có dẫn file; nhiều hộp hơn hoặc confidence cao hơn không tự là đúng hơn. Ca QC giữ chuyển đổi nguồn / lệch cả batch / lệch một hộp là biến đổi có kiểm soát từ prediction thật B, không phải detector chạy thêm hoặc đáp án chuẩn. Không import `case-*.json` vào CVAT; không nhập prediction demo vào frame Robotaxi.

1. Ghi số hộp, class, mean_z và quan sát A/B, B/C vào `PRE-LABEL-REPORT.md`.
2. Đối chiếu ca lỗi: cùng lệch cả batch thì dừng để kiểm transform/pipeline; một hộp lệch thì kiểm nhiều view/đối tượng; không đủ chứng cứ thì ghi chưa chắc.
3. Mỗi người ghi vai trò, nhận xét riêng và điều chưa chắc. Chỉ xem kết quả có sẵn phải ghi `provided-results`, không ghi đã chạy inference.
4. Thu báo cáo tại nơi private LC cấp. Thư mục nhóm `K4-DAY13-TenNhom/` có `TEAMMATES.md` và report/output; không public tên/MSSV hoặc bản điền. Phần này nằm trong phiên 240 phút, nhóm chạy xong quay lại phần nguồn/QC cá nhân trên CVAT/portal.

**Hoàn tất:** LC đã nhận báo cáo và mỗi thành viên giải thích được phép z, một quan sát pillar và quyết định khi gặp lỗi batch. Gói Student không dựng portal, không chấm điểm và không cấp quyền xuất Robotaxi. Xem [hướng dẫn thực hành](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/blob/main/PRE-LABEL.md) và [luồng cá nhân](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/blob/main/HUONG-DAN.md).
