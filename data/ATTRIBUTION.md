# Nguồn và thay đổi của PCD Student

Mẫu thuộc **KITTI Vision Benchmark Suite**, do Karlsruhe Institute of Technology và Toyota Technological Institute at Chicago cung cấp. Ghi công Andreas Geiger, Philip Lenz, Raquel Urtasun và các tác giả KITTI.

- Điều kiện gốc: [KITTI Copyright](https://www.cvlibs.net/datasets/kitti/).
- Giấy phép dữ liệu và bản chuyển đổi: [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/); [văn bản pháp lý](https://creativecommons.org/licenses/by-nc-sa/3.0/legalcode). Chỉ dùng thí nghiệm học thuật phi thương mại, ghi nguồn và phát bản chuyển đổi cùng giấy phép. Không phải quyền dùng thương mại/production.
- File nguồn là **mẫu demo KITTI `000008.bin` do MMDetection3D cung cấp**, không tuyên bố là toàn bộ scan KITTI raw chưa xử lý. [File tại commit cố định](https://github.com/open-mmlab/mmdetection3d/blob/fe25f7a51d36e3702f961e198894580d83c4387b/demo/data/kitti/000008.bin).
- SHA256 gốc: `3b9de6cc966534900f6a1bdc93b21772e47a334eb2ef18082021956520d902d1`. 275.808 byte; 17.238 record little-endian float32 `x,y,z,reflectance`.

## Chuyển đổi phục vụ bài lab

Dùng [converter](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/blob/main/bundle/prepare-kitti-demo.py): giữ mọi điểm và thứ tự, giữ x/y; đổi `z_pcd = z_kitti + 1.73 m`. Đây là **phép đổi tọa độ đã khai báo để thực hành z**, không khẳng định ground thật chính xác bằng 0. Pipeline vẫn ước lượng `z_ground` từ scan (lần thử native amd64: 0,075 m).

Ghi PCD binary với `FIELDS x y z rgb`, `SIZE 4 4 4 4`, `TYPE F F F U`, stride 16 byte. Trường `rgb` chứa 0 (không có màu thực). **Reflectance gốc không được chuyển vào PCD**: bài chủ đích giữ adapter dùng kênh hằng hiện tại để quan sát giới hạn thiếu intensity, không thay checkpoint. Đây không phải benchmark KITTI tiêu chuẩn với reflectance thật và không phải phục hồi intensity. Manifest ghi hash và các thay đổi để không nhầm với bản nguồn.

Không có ảnh camera, label ground truth hoặc dữ liệu VinFast/Robotaxi trong gói Student. Không dùng prediction/ca lỗi của mẫu này làm reference hoặc nhập vào job Robotaxi khác frame.

## Trích dẫn

Andreas Geiger, Philip Lenz, Raquel Urtasun. **Are we ready for Autonomous Driving? The KITTI Vision Benchmark Suite.** CVPR, 2012.
