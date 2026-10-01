# Code CPU cho phần PointPillars

Code được tách từ bộ lab Day 13, dùng để thực hành theo [PRE-LABEL.md](../PRE-LABEL.md). Đầu vào Student là [KITTI 000008 đã chuyển đổi](../data/ATTRIBUTION.md); image archive nằm trong ZIP Releases. Xem [gói tải/chạy](../bundle/README-STUDENT.md). Bản Robotaxi riêng của LC không được phát cho laptop học viên.

- `preannotate.py`: đọc PCD, inference checkpoint KITTI, đổi tọa độ và xuất JSON/Side/CSV.
- `pipeline-qc-cases.py`: tạo các ca lỗi z có kiểm soát từ prediction; không chạy model hoặc tạo reference.
- `Dockerfile` và `patches/`: build image CPU native. LC chuẩn bị trước ca; không bắt cả lớp build tại chỗ.

Nếu được giao chuẩn bị image, chạy từ repo root:

```bash
docker build -t day13-pointpillars:lab practice
```

Đây là build có tải dependencies/upstream từ mạng, khác với chạy container inference `--network none`. Không có lệnh pull registry công khai. Thời gian build và khả năng Windows phụ thuộc máy; cần thử trước ca. Lần tách repo này giữ nguyên source Docker/model adapter của bản đã thử trên Linux amd64 và Mac arm64, không phải một lần benchmark mới.

Helper có test stdlib, chạy từ repo root không cần dữ liệu thật:

```bash
python3 -m unittest discover -s practice/tests -v
```

Trên Windows dùng `py -3` thay `python3`. Test kiểm biến đổi/cấu trúc helper; không chứng minh detector hay máy Windows chạy được.

Upstream model: [zhulf0804/PointPillars](https://github.com/zhulf0804/PointPillars), commit `620e6b0d07e4cb37b7b0114f26b934e8be92a0ba`. Docker giữ upstream license trong checkout; xem [LICENSE upstream](https://github.com/zhulf0804/PointPillars/blob/620e6b0d07e4cb37b7b0114f26b934e8be92a0ba/LICENSE). CPU patches không đổi checkpoint, và constant reflectance không phục hồi intensity thật.
