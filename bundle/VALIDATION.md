# Kiểm chứng gói Student KITTI

Ngày thử: 01/10/2026. Một PCD KITTI demo `000008` đã chuyển đổi, 17.238 điểm; nguồn, giấy phép CC BY-NC-SA 3.0 và thay đổi tại [ATTRIBUTION](../data/ATTRIBUTION.md). Không dùng Robotaxi/private provided-results làm đầu vào hoặc minh chứng.

## Chạy model thật từ gói native

Cả hai gói kiểm manifest, nạp đúng image và chạy thật A/B/C + ba ca QC, `smoke.json` có `status: passed`. Giữ checkpoint KITTI/score0.3/frontROI, CPU tối đa4/RAMcontainer tối đa4GB. Đây là giới hạn, không phải RAM tối thiểu của laptop; không đo peakRAM mới.

| Bước | ThinkPad Linux amd64 (giây) | Mac Apple Silicon arm64 (giây) |
| --- | ---: | ---: |
| docker-load | 6.92 | 42.83 |
| run-A | 4.00 | 71.74 |
| run-B | 4.12 | 84.50 |
| run-C | 2.38 | 55.20 |
| qc-cases | 1.13 | 10.73 |

Thời gian wall gồm khởi động container và riêng bước load; không gồm tải ZIP, cài Docker/Python hoặc build image. Hai máy cùng ra A=1 hộp, B=13 hộp, C=6 hộp. B có 10vehicles, 2pedestrian, 1two-wheels; C có 6pedestrian. Đây là quan sát thực nghiệm, không phải số hộp/accuracy mục tiêu. Prediction hash khác giữa kiến trúc; không yêu cầu khớp bitwise hay chọn cấu hình dựa trên số hộp.

B có hơn hai hộp thật; helper tạo đủ ba ca có nhãn `training_only`, source hash trỏ đúng B. Không thêm hộp giả, không import ca lỗi, không coi prediction giữ chuyển đổi là reference.

## Danh tính và phạm vi kiểm tra

- Input PCD SHA256: `3b5ea3da13e2b19149cab6a8d521c2ca55f2df93f026b5a3f8c273ce70645d60`. Converter từ nguồn pinned SHA tái tạo đúng bytes.
- Checkpoint SHA256 cả hai image: `482dfcf63b932cc5ccf012b4bbdad52aa51aa33becf87d0a39d61c39b377b5b1`. ImageID riêng, code/input/checkpoint/filehash ghi trong manifest.
- Image tái sử dụng bản CPU native đã build từ Dockerfile/commit upstream cố định, chỉ chứa code/model/dependencies, không chứa Robotaxi hoặc dữ liệu input. Preannotate/helper không đổi so với source đã thử. Gói Student được đóng mới bằng PCD KITTI, không copy ZIP LC.
- Gói được đóng trong working tree đang sửa từ base Student revision `0831856`; manifest ghi `working_tree_dirty: true` cùng hash chính xác các file xuất. Không ghi sai rằng đó là clean release build; code xuất có hash đối chiếu với source public.
- 25 unit tests bundle/converter và 5 helper tests pass. Read-only reviewer kiểm nguồn/hợp đồng runner và tái tạo PCD; không thay cho các lần chạy model ở trên. Không có CI cấu hình, không coi local test là CI green.
- Source/data/manifest/licensing qua kiểm file allowlist; ZIP chỉ có image/input/code/blankreport/licensenotices, không có kết quả của học viên hoặc private media. ZIP+SHA256SUMS tại Releases.

## Giới hạn trước ca

**Windows chưa được thử trên máy thật.** Linux amd64 chạy thành công không bảo đảm mọi Windows/Docker Desktop đều đủ RAM hoặc mount đúng; LC/nhóm phải chạy thử trước ca. Apple Silicon được thử một máy với Docker Desktop; không phải SLA cho mọi Mac. Có thể mất vài phút để load/run, máy LC hỗ trợ nhóm không chạy được theo lượt.

Chỉ thí nghiệm KITTI học thuật phi thương mại; quyền này không mở quyền tải Robotaxi hoặc dùng dữ liệu trong production. Không chấm chất lượng cuboid bằng các prediction demo. Phần sửa/QC Robotaxi vẫn ở CVAT/viewer của ca.
