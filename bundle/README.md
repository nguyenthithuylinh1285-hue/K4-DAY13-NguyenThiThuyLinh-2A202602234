# Student bundle — tải, chạy và tái tạo

Học viên đọc [README-STUDENT.md](README-STUDENT.md), tải đúng ZIP từ [Releases](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/releases) và giữ nguyên gói để runner kiểm manifest. [Nguồn/giấy phép mẫu](../data/ATTRIBUTION.md) và [validation](VALIDATION.md) mô tả đầu vào và máy đã thử.

## Người chuẩn bị gói

Không dùng gói LC Robotaxi để tạo bản Student. `student-bundle.py pack` chỉ nhận PCD trùng hash `data/demo.pcd` của repo, cùng provenance/giấy phép của mẫu KITTI. Code/pretrained upstream giữ giấy phép riêng; `POINTPILLARS-LICENSE.txt` được lấy từ chính image khi đóng gói.

1. Build image native từ repo root trước ca:

```bash
docker build -t day13-pointpillars:student practice
```

2. Đóng gói trên máy Docker Linux native đúng architecture:

```bash
python3 bundle/student-bundle.py pack --pcd data/demo.pcd --image day13-pointpillars:student --out /duong-dan-moi/student-bundle
```

Windows dùng `py -3` và đường dẫn local tương ứng; pack cần Git CLI để ghi provenance. Gói kiểm checkpoint hash, input hash, image ID, code hashes và commit/dirty state. Không dùng output có sẵn hoặc emulation để ghi là đã native smoke.

3. Chạy thật gói vừa tạo, output ở ngoài gói:

```bash
python3 /duong-dan-moi/student-bundle/student-bundle.py run --bundle /duong-dan-moi/student-bundle --out /duong-dan-moi/ket-qua-smoke
```

4. Sau khi `smoke.json` passed, ZIP **nội dung** thư mục gói, không ZIP cả folder bao ngoài và không thêm dữ liệu/report đã điền của học viên. Tạo SHA256 của ZIP, phát qua release. Gói Student hiện không chứa `provided-results`; học viên phải chạy và tự ghi kết quả.

## Tái tạo PCD

Mẫu đang ở `data/demo.pcd` nên không cần tải lại để làm bài. Maintainer muốn tái tạo dùng source public tại URL cố định trong `prepare-kitti-demo.py`, nguồn `.bin` hash cố định. Tải bằng công cụ có HTTPS CA phù hợp, rồi:

```bash
python3 bundle/prepare-kitti-demo.py --source /duong-dan/000008.bin --out /thu-muc-moi/data
```

Để script tự tải, bỏ `--source`. Không tắt xác minh TLS nếu Python báo lỗi CA. Converter từ chối source khác hash và file output đã tồn tại; giữ attribution/license khi đặt bản chuyển đổi vào repo.

## Test không cần Docker

```bash
python3 -m unittest discover -s bundle -q
python3 -m unittest discover -s practice/tests -q
```

Test unit dùng mock ở biên Docker để kiểm hợp đồng runner. Chúng không thay lần chạy model/PCD thật. Xem validation cho bằng chứng native và giới hạn Windows.
