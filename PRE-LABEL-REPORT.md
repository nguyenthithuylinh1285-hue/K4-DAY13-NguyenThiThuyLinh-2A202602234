# Báo cáo thực hành PointPillars — Day 13

Giữ bản đã điền ngoài Git, trong thư mục nhóm private do LC thu. Đây là kiểm tra formative; không ghi điểm của người khác.

## Nhóm và provenance

- Mã nhóm/phòng: C305
- Thành viên: xem `TEAMMATES.md` (họ tên/MSSV, vai trò từng lượt):
  1. Võ Thị Bảo Chi - 2A202602200 (Vận hành lệnh)
  2. Võ Lê Xuân Nhi - 2A202602202 (Kiểm cấu hình / JSON)
  3. Nguyễn Thị Thùy Linh - 2A202602234 (Xem hình học / kiểm ảnh Side)
  4. Hoàng Gia Linh - 2A202602192 (Ghi log / tổng hợp báo cáo)
- Trạng thái: `executed-by-group`
- Người thực sự chạy: cả nhóm (trên máy tính nhóm phòng C305 - Windows amd64); ngày/giờ: 01/10/2026, 14:57–14:58 (ICT)
- Image tag và image ID: `day13-pointpillars:lc-20261001-amd64` / `sha256:e03983bd922ec29890bf547db8de408402efd82583680b62e671c20da2fd2c82`; phiên bản repo: `0831856d921609312d42c7582c366e5a311bb7b1`
- PCD được cấp / frame_id: `demo.pcd` (KITTI 000008, 17.238 điểm) / frame_id=`demo`; chạy trên máy nhóm; fingerprint PCD SHA256: `3b5ea3da13e2b19149cab6a8d521c2ca55f2df93f026b5a3f8c273ce70645d60`
- Checkpoint: PointPillars KITTI có sẵn trong image; checkpoint SHA256: `482dfcf63b932cc5ccf012b4bbdad52aa51aa33becf87d0a39d61c39b377b5b1` (epoch_160.pth tại `/opt/PointPillars/pretrained/`)
- Phạm vi: front-window; score threshold: 0.3
- Giả định kênh thứ tư/intensity: kênh hằng số theo lớp (RGB=0 placeholder, reflectance gốc đã bỏ); z_ground ước lượng từ PCD = 0.075 m

## Ba lượt inference thật

| Lượt | delta | Pillar XY | Số hộp | mean_z | File JSON/Side/CSV | Quan sát có bằng chứng |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0 | 0.16 | 1 | 0.330 | `run-A/boxes-demo-delta-0-voxel-0.16.json`, `side-demo-delta-0-voxel-0.16.png`, `summary.csv` | 1 hộp `vehicles`, tâm z=0.330 m; model bắt được rất ít do PCD chưa được bù độ cao về hệ tọa độ chuẩn của checkpoint KITTI |
| B | 1.73 | 0.16 | 13 | 1.034 | `run-B/boxes-demo-delta-1.73-voxel-0.16.json`, `side-demo-delta-1.73-voxel-0.16.png`, `summary.csv` | 10 `vehicles`, 2 `pedestrian`, 1 `two-wheels`; hộp phân bố hợp lý trên mặt đường ở dải z ~0.7-1.4 m |
| C | 1.73 | 0.32 | 6 | 1.091 | `run-C/boxes-demo-delta-1.73-voxel-0.32.json`, `side-demo-delta-1.73-voxel-0.32.png`, `summary.csv` | 6 `pedestrian`, toàn bộ `vehicles` biến mất do kích thước pillar lớn làm mất chi tiết hình học của xe; mean_z không đổi nhiều (~1.091 m) |

- **A/B: thay input trước model có khác dịch cùng một hằng số cho output không? Vì sao?**
  Khác nhau hoàn toàn. Thay delta từ 0 lên 1.73 m làm thay đổi tọa độ z của từng điểm mây điểm trước khi đưa vào mạng (`z_model = z_source - z_ground - delta`). Điều này làm thay đổi phân bố điểm vào các pillar và kích hoạt các đặc trưng khác nhau trong mạng nơ-ron, dẫn đến số hộp tăng vọt từ 1 lên 13 và phân bố class đa dạng (không phải chỉ dịch vị trí các hộp đã có).
- **B/C: thấy gì khi đổi pillar? Có đủ bằng chứng để nói cấu hình nào tốt hơn không?**
  Khi tăng pillar XY từ 0.16 lên 0.32 m, số lượng hộp giảm từ 13 xuống 6 và mất hoàn toàn phân lớp `vehicles`. Không thể vội kết luận cấu hình nào tốt hơn nếu chưa có ground truth chuẩn để đối chiếu, tuy nhiên cấu hình pillar 0.16 m giữ được chi tiết tốt hơn và phát hiện được các đối tượng kích thước lớn như ô tô.
- **Giới hạn ROI và góc Side ảnh hưởng cách đọc miss/yaw thế nào?**
  Phạm vi ROI front-window giới hạn vùng không gian xử lý phía trước; các đối tượng ngoài ROI bị cắt bỏ là do phạm vi lọc, không phải do model bỏ sót sai. Hình chiếu Side chiếu toàn bộ không gian lên mặt phẳng X-Z, làm các đối tượng ở các tọa độ Y khác nhau bị đè lên nhau, do đó không thể xác định chính xác góc quay (yaw) hay phân biệt các xe đi song song chỉ dựa vào góc Side.
- **JSON nào còn chưa đủ cơ sở để import? Cần kiểm gì tiếp?**
  Cả ba file JSON đều chưa đủ cơ sở để import thẳng vào CVAT cho bài toán Robotaxi thực tế vì đây mới chỉ là inference thử nghiệm trên KITTI demo. Cần kiểm tra đối chiếu thêm hình chiếu Top (BEV), Front và kết hợp ảnh Camera để kiểm tra độ khít (tightness) và góc yaw trước khi đưa vào gắn nhãn chính thức.

## Ca QC có kiểm soát — không import CVAT

| Ca | Số hộp lệch z / tổng hộp | Lượng lệch | Class/x/y/yaw có đổi? | Dừng batch, kiểm từng hộp hay chưa rõ? | Bằng chứng |
| --- | --- | --- | --- | --- | --- |
| case-correct | 0 / 13 | 0 m | Không đổi | — | Baseline chuẩn: hộp nằm ở độ cao z từ 0.7 đến 1.4 m, khớp mặt đường |
| case-batch-z | 13 / 13 | -1.805 m (tức -(z_ground + delta)) | Không đổi | **Dừng batch**: Toàn bộ hộp bị hạ thấp cùng một lượng, đây là lỗi hệ thống do quên cộng bù z ngược | `side-batch-z.png` cho thấy toàn bộ 13 hộp bị chìm sâu dưới mặt đường (z < 0) |
| case-one-box-z | 1 / 13 | -1.805 m (ở hộp đầu tiên) | Không đổi | **Kiểm từng hộp**: Chỉ 1 hộp đơn lẻ bị lỗi, các hộp khác bình thường, không dừng cả batch | `side-one-box-z.png` chỉ có duy nhất 1 hộp bị tụt xuống dưới, 12 hộp còn lại giữ nguyên vị trí |

Ghi rõ: helper tạo biến đổi có chủ đích từ prediction của Run B (`boxes-demo-delta-1.73-voxel-0.16.json`), không phải kết quả inference riêng hoặc nhãn đúng. Đây là dữ liệu dùng cho mục đích đào tạo QC (training only).

## Nhận xét cá nhân

### Võ Thị Bảo Chi — 2A202602200
- **Vai trò:** Vận hành lệnh — trực tiếp chạy lệnh bundle (`student-bundle.py run`), kiểm soát tiến trình chạy của Docker container và kiểm tra kết quả trả về của từng lượt A, B, C.
- **Quan sát A/B/C:** Khi chạy lượt A (delta=0), chỉ có đúng 1 hộp được phát hiện với mean_z = 0.330 m. Sang lượt B (delta=1.73), số hộp tăng lên 13 và mean_z = 1.034 m. Điều này chứng minh việc bù độ cao z là cốt lõi để mô hình PointPillars nhận diện đúng ngữ cảnh mặt đường.
- **Diễn giải phép z thuận/ngược:** Phép biến đổi thuận đưa mây điểm từ hệ tọa độ cảm biến về hệ tọa độ huấn luyện của KITTI (`z_model = z_source - z_ground - delta`). Sau khi mạng dự đoán ra bounding boxes, phép biến đổi ngược bắt buộc phải cộng bù lại (`z_source = z_model + z_ground + delta`) để hộp về đúng độ cao thực tế của xe.
- **Quyết định lỗi batch & hành động:** Đối với `case-batch-z`, khi phát hiện toàn bộ hộp đều bị chìm, tôi quyết định dừng ngay batch tiền gán nhãn, thông báo cho kỹ sư phụ trách pipeline kiểm tra lại script biến đổi tọa độ, tuyệt đối không chỉnh sửa thủ công từng hộp trong CVAT.
- **Điều chưa chắc:** Cần tìm hiểu thêm về lý do tại sao ở lượt A chỉ có đúng 1 vật thể được nhận diện thay vì không có vật thể nào.

### Võ Lê Xuân Nhi — 2A202602202
- **Vai trò:** Kiểm cấu hình / JSON — phân tích cấu trúc file `manifest.json`, đối chiếu tham số delta, voxel_size và kiểm tra định dạng dữ liệu đầu ra của các file JSON.
- **Quan sát A/B/C:** Ở lượt C (voxel_size = 0.32), số hộp giảm một nửa so với B (từ 13 xuống 6) và hoàn toàn không nhận diện được xe con (vehicles=0, pedestrian=6). Kích thước pillar tăng gấp đôi làm suy giảm độ phân giải không gian nghiêm trọng đối với các vật thể kích thước lớn.
- **Diễn giải phép z thuận/ngược:** Giá trị `z_ground = 0.075 m` và `delta = 1.73 m` tổng cộng tạo ra độ dịch 1.805 m. Nếu quên bước chuyển ngược, toàn bộ bounding box sẽ bị dịch xuống dưới lòng đất một khoảng đúng bằng 1.805 m.
- **Quyết định lỗi batch & hành động:** Phân biệt rõ giữa lỗi hệ thống và lỗi đơn lẻ: `case-batch-z` là lỗi toàn bộ (phải dừng xử lý batch), còn `case-one-box-z` chỉ là lỗi cục bộ của 1 đối tượng, cần kiểm tra lại đối tượng đó trên 3 hình chiếu BEV/Side/Front.
- **Điều chưa chắc:** Liệu ngưỡng score threshold 0.3 đã tối ưu cho cả pedestrian và vehicles chưa, hay cần các ngưỡng lọc điểm riêng cho từng lớp.

### Nguyễn Thị Thùy Linh — 2A202602234
- **Vai trò:** Xem hình học / kiểm ảnh Side — quan sát trực quan các file ảnh chiếu cạnh (`side-*.png`), đối chiếu tương quan vị trí hộp với đám mây điểm.
- **Quan sát A/B/C:** So sánh `side-demo-delta-0-voxel-0.16.png` và `side-demo-delta-1.73-voxel-0.16.png` thấy rõ sự khác biệt: ở lượt B các hộp bao quanh sát các cụm điểm phản xạ của thân xe, phân bố trải dài dọc trục X từ 3 m đến 55 m.
- **Diễn giải phép z thuận/ngược:** Nhìn từ góc Side, độ cao z quyết định hộp có nằm "chạm đất" hay "bay lơ lửng/chìm dưới đất". Nếu không có bước chuyển ngược, trực quan trên ảnh Side sẽ thấy ngay các đáy hộp nằm thấp hơn hẳn bề mặt đường.
- **Quyết định lỗi batch & hành động:** Khi thấy ảnh `side-batch-z.png`, tất cả các hộp đều chìm dưới vạch z=0, đây là dấu hiệu trực quan rõ nhất của lỗi dịch z hàng loạt. Hành động: Báo cáo dừng batch và yêu cầu re-run pipeline với công thức chuyển ngược chính xác.
- **Điều chưa chắc:** Góc nhìn Side bị che khuất và đè các điểm theo trục Y, nên cần kết hợp thêm BEV (Top-down) mới xác định được chính xác biên dạng ngang của xe.

### Hoàng Gia Linh — 2A202602192
- **Vai trò:** Ghi log / tổng hợp báo cáo — ghi nhận thời gian chạy từng bước từ `smoke.json`, tổng hợp số liệu vào các bảng và hoàn thiện báo cáo nhóm.
- **Quan sát A/B/C:** Thời gian chạy thực tế trên máy: run-A (4.2s), run-B (4.1s), run-C (2.8s). Lượt C chạy nhanh hơn rõ rệt vì kích thước voxel lớn hơn (0.32 m) làm số lượng pillar cần tính toán giảm đi đáng kể.
- **Diễn giải phép z thuận/ngược:** Phép biến đổi z là ánh xạ affine hai chiều giữa hệ tọa độ cảm biến LiDAR của xe tự hành và hệ quy chiếu chuẩn mà mô hình PointPillars KITTI yêu cầu. Không thể bỏ qua bất kỳ chiều nào trong hai chiều biến đổi này.
- **Quyết định lỗi batch & hành động:** Đánh giá `case-correct` là bản đối chứng hợp lệ về mặt kỹ thuật, `case-batch-z` phải bị từ chối nhập vào CVAT. Với `case-one-box-z`, cần khoanh vùng kiểm tra riêng hộp bị lệch z thay vì từ chối cả file.
- **Điều chưa chắc:** Giá trị `z_ground = 0.075 m` được ước tính tự động từ demo.pcd, cần kiểm tra xem trên các địa hình dốc hoặc mấp mô thì thuật toán ước tính mặt đất có hoạt động ổn định không.

## LC ghi nhận riêng

- Quyền dùng PCD/image và đúng ca:
- Có chạy thật / chỉ phân tích; còn cần lượt thực hành bổ sung:
- Output đủ, giữ bản gốc, không đưa ca lỗi vào CVAT:
- Nhận xét từng thành viên và quyết định dừng pipeline:
- Đồng ý chuyển sang chỉnh/QC / cần bổ sung; lý do:
