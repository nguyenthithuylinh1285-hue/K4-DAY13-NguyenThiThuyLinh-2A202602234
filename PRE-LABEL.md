# Phần bắt buộc — PointPillars và QC pipeline

Trước khi chỉnh cuboid, nhóm 3–4 người chạy **PointPillars pretrained KITTI** trên một PCD được phép dùng. Sản phẩm là ba lượt inference thật, ảnh Side/JSON/CSV, các ca QC lỗi z có kiểm soát và nhận xét riêng của từng thành viên. Không train model; không chạy inference cho cả 30 job của từng người.

## Chạy nhanh gói Student

Nhóm có một máy chạy Docker dùng [gói Student](bundle/README-STUDENT.md), tải ZIP đúng kiến trúc tại [Releases](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/releases), giải nén và chạy `student-bundle.py`. Gói có **mẫu KITTI 000008** với [ghi nguồn/giấy phép CC BY-NC-SA 3.0](data/ATTRIBUTION.md), chỉ dùng học thuật phi thương mại; không có dữ liệu Robotaxi. PCD đã đổi z +1.73 m, giữ x/y, bỏ reflectance thật và thêm RGB=0 để dùng adapter hằng hiện tại. Không gọi đây là benchmark KITTI với intensity thật.

Runner thực hiện đúng A/B/C và các ca QC mô tả bên dưới; không phải dựng portal. Bài nhóm dùng KITTI trên laptop, bài cá nhân vẫn sửa/QC Robotaxi trong CVAT/viewer. Có thể chạy lệnh từng lượt ở các mục tiếp theo để tìm hiểu cấu hình, nhưng dùng runner là đường chạy thống nhất, không cần build image tại lớp. Máy không chạy được dùng máy LC theo lượt.

## 1. Chọn máy và bắt đầu phiên

Một máy trong nhóm chạy Docker CPU. Nhóm không có máy chạy được dùng máy LC của phòng, chạy lần lượt một yêu cầu; học viên vẫn chọn cấu hình và đọc kết quả. Không gửi inference về ThinkPad vận hành CVAT. Không cần GPU.

1. Tải ZIP Student đúng kiến trúc ở mục trên và chạy thử trước ca. Image được nạp từ archive trong ZIP, không cần registry; PCD `input/demo.pcd` là KITTI đã chuyển đổi có quyền phân phối theo giấy phép. LC cấp nơi thu báo cáo private. Gói Robotaxi riêng của LC vẫn chỉ chạy máy phòng, không chuyển cho học viên.
2. Nhóm chọn người vận hành lệnh, người kiểm cấu hình/JSON, người xem hình học; người thứ tư ghi log. Đổi vai giữa các lượt. Mỗi người viết nhận xét riêng.
3. Mỗi thành viên đăng nhập portal, bấm **Bắt đầu phiên 240 phút** khi bắt đầu phần này. Không đợi hết thí nghiệm mới bắt đầu đồng hồ.
4. Kiểm image/PCD chạy được trước buổi học. Nếu có lỗi setup, chuyển sang máy LC; không dành cả giờ để build.

Phân bổ gợi ý trong 240 phút: 60 phút thực hành pre-label, 115 phút sửa nguồn, 50 phút QC, 15 phút phản hồi/tổng kết. Các chặng nguồn/QC có thể xen kẽ; feedback muộn vẫn theo hạn riêng trên portal. 30 job là lượng phân công, không phải lời bảo đảm hoàn thành đủ 30 frame full-range và 30 QC trong thời gian còn lại.

Robotaxi thật vẫn ở CVAT/viewer được cấp; quyền tải tạm trên ThinkPad không tự áp dụng cho laptop hoặc máy LC. Dùng KITTI của gói Student; không lấy PCD Robotaxi từ CVAT về để làm phần này khi chưa được cấp phép. Bộ minh họa phải phù hợp định dạng và hệ tọa độ script; không dùng một scan bất kỳ rồi mặc định nó có gốc mặt đất như Robotaxi.

**Checkpoint:** có PCD được cấp, đúng image, máy chạy được và vai trò nhóm; đồng hồ phiên đã bắt đầu. Thiếu đầu vào thì báo LC, chưa chuyển thành bài chỉ đọc kết quả mà ghi là đã chạy.

## 2. Chạy ba cấu hình trên cùng PCD

Giữ checkpoint, frame, score threshold và phạm vi như nhau. Đổi đúng một biến giữa các lượt để giải thích được nguyên nhân. Các lệnh dưới dùng `--from KITTI`, score `0.3`, chỉ cửa sổ **phía trước** của checkpoint; không tự thêm `--full-scene` ở một lượt. Vật ngoài ROI không phải bằng chứng model bỏ sót trong bài so cấu hình này.

| Lượt | `delta` (m) | Pillar XY (m) | So với lượt nào? |
| --- | ---: | ---: | --- |
| A | 0 | 0.16 | B: ảnh hưởng giả định chiều cao sensor trước inference |
| B | 1.73 | 0.16 | A; cũng là baseline để so pillar và tạo ca QC |
| C | 1.73 | 0.32 | B: ảnh hưởng cỡ pillar |

### Chuẩn bị đường dẫn

Ví dụ image tag `day13-pointpillars:lab` là tên dùng trong lệnh; thay bằng tag LC cung cấp. Không có lệnh pull registry đã xuất bản trong repo. Nếu LC phát file image tar, nạp bằng `docker load -i <file-image-LC-cap>` rồi kiểm tên/tag thực tế. Người chuẩn bị image có thể build từ `practice/Dockerfile` trước ca, không yêu cầu mọi laptop build tại lớp.

Tạo thư mục input chỉ chứa `demo.pcd` được cấp, và thư mục output mới. Mac/Linux, chạy trong terminal:

```bash
IMAGE='day13-pointpillars:lab'
DATA_DIR='/duong-dan-tuyet-doi/input'
OUT_DIR='/duong-dan-tuyet-doi/K4-DAY13-TenNhom/output'
mkdir -p "$OUT_DIR"
docker image inspect "$IMAGE" --format '{{.Id}} {{.Architecture}}'
```

Windows PowerShell, thay bằng đường dẫn thật trên máy:

```powershell
$IMAGE = 'day13-pointpillars:lab'
$DATA_DIR = 'C:\Lab13\input'
$OUT_DIR = 'C:\Lab13\K4-DAY13-TenNhom\output'
New-Item -ItemType Directory -Force -Path $OUT_DIR | Out-Null
docker image inspect $IMAGE --format '{{.Id}} {{.Architecture}}'
```

Lưu image ID/architecture và phiên bản repo vào báo cáo. File vào mount read-only; file ra thuộc nhóm, không ghi đè output của nhóm khác. Các lệnh dưới chạy được từng dòng trong cả Bash và PowerShell sau khi khai biến đúng shell:

```bash
docker run --rm --network none --cpus 4 --memory 4g --mount "type=bind,source=$DATA_DIR,target=/data,readonly" --mount "type=bind,source=$OUT_DIR,target=/out" "$IMAGE" --data /data/demo.pcd --out /out/run-A --from KITTI --deltas 0 --voxel-size 0.16 --score-thresh 0.3
docker run --rm --network none --cpus 4 --memory 4g --mount "type=bind,source=$DATA_DIR,target=/data,readonly" --mount "type=bind,source=$OUT_DIR,target=/out" "$IMAGE" --data /data/demo.pcd --out /out/run-B --from KITTI --deltas 1.73 --voxel-size 0.16 --score-thresh 0.3
docker run --rm --network none --cpus 4 --memory 4g --mount "type=bind,source=$DATA_DIR,target=/data,readonly" --mount "type=bind,source=$OUT_DIR,target=/out" "$IMAGE" --data /data/demo.pcd --out /out/run-C --from KITTI --deltas 1.73 --voxel-size 0.32 --score-thresh 0.3
```

`4g`/4 CPU là giới hạn của lệnh, không phải chứng nhận máy 4 GB RAM chạy được: còn hệ điều hành, Docker VM và trình duyệt. Không tăng số container song song trên máy LC. Giới hạn của từng phòng phải theo lần smoke thực tế trước ca.

**Checkpoint:** mỗi `run-A/B/C` có `boxes-*.json`, `side-*.png`, `summary.csv`. Đọc thông báo lỗi nếu thiếu file; không tự điền số hộp hay dùng nhãn nguồn thay prediction.

## 3. Đọc output và giải thích phép đổi z

Mở JSON, ảnh Side và CSV của cả ba lượt. `frame_id`, `dataset`, `delta`, `voxel_size`, `z_ground` phải cùng đầu vào/cấu hình đã ghi. Mỗi hộp có class, tâm `x/y/z`, `length/width/height`, yaw và score. Bảy số hình học là ba tọa độ tâm, ba kích thước và yaw; class/score là trường riêng.

Trong pipeline KITTI của script:

```text
z_model  = z_source - z_ground - delta
z_source = z_model  + z_ground + delta
```

`z_ground` được ước lượng từ PCD; `delta=1.73` là giả định cao độ sensor của checkpoint KITTI trong bài. Không áp hằng số này cho mọi sensor/model. Script còn chuyển yaw, class và bottom-z thành center-z theo checkpoint; JSON đã ở hệ nguồn, không tự đổi thêm lần nữa khi đọc.

1. A so B: ghi số hộp, lớp, mean_z và vị trí quan sát được. Model chạy lại trên input đã dịch, nên số hộp/vị trí có thể đổi; **không kết luận mọi hộp phải lệch đúng 1.73 m**.
2. B so C: giữ delta, xem thay pillar có làm đổi số hộp/vị trí/lớp không. Đây là thay biểu diễn/input cho mạng, không phải quên cộng z ngược.
3. Kiểm phạm vi: Side là hình chiếu toàn scene x-z, có thể chồng xe khác y. Không dùng nó một mình để duyệt hình học từng hộp; sau khi pipeline hợp lý còn cần Top/Side/Front và camera.
4. Ghi những gì chưa đủ bằng chứng. Không chọn cấu hình chỉ vì nhiều hộp hơn hoặc score cao hơn.

PCD Robotaxi thiếu intensity thật; PCD KITTI Student chủ đích bỏ reflectance nguồn để thực hành cùng adapter. Script dùng kênh hằng số theo lớp ở hai lượt đọc. RGB không phải intensity. Nếu bộ minh họa dùng định dạng khác, LC phải xác nhận adapter trước; không gọi các hằng số là dữ liệu intensity được phục hồi. Đường `z=0` trên ảnh Side là đường tham chiếu của plot, không chứng nhận mặt đường cục bộ mọi vị trí.

**Checkpoint:** mỗi người giải thích được vì sao đổi `delta` trước inference khác với dịch hộp sau inference; nêu được một quan sát B/C có chứng cứ từ output, không chỉ đoán theo lý thuyết.

## 4. Thực hành nhận lỗi cả batch

Các lượt A/B/C đều dùng script đổi z thuận/ngược. Để nhìn thấy lỗi quên phép ngược một cách rõ, dùng helper tạo **ca lỗi có kiểm soát từ prediction thật của lượt B**. Helper không chạy lại model và không thay đổi JSON B.

Khai `PRACTICE_DIR` là đường dẫn tuyệt đối tới thư mục `practice` của repo trên máy chạy (Bash: `PRACTICE_DIR='/.../practice'`; PowerShell: `$PRACTICE_DIR='C:\...\practice'`). Nếu PCD được cấp có tên `demo.pcd`, file B theo lệnh trên là `boxes-demo-delta-1.73-voxel-0.16.json`.

```bash
docker run --rm --network none --cpus 4 --memory 4g --entrypoint python --mount "type=bind,source=$PRACTICE_DIR,target=/practice,readonly" --mount "type=bind,source=$DATA_DIR,target=/data,readonly" --mount "type=bind,source=$OUT_DIR,target=/out" "$IMAGE" /practice/pipeline-qc-cases.py --prediction /out/run-B/boxes-demo-delta-1.73-voxel-0.16.json --out /out/qc-cases --pcd /data/demo.pcd
```

LC có thể chạy helper trước và cấp bộ ca qua kênh private của phòng. Nếu B có ít hơn hai hộp, helper sẽ từ chối (một hộp không phân biệt được lỗi batch với lỗi đơn lẻ): báo model không ra hộp dùng được, kiểm dữ liệu/ROI/cấu hình hoặc xin một PCD minh họa khác đã được phép. Không thêm hộp giả chỉ để đủ bài.

Ba ca gồm bản giữ phép chuyển nguồn, bản mọi hộp bị trừ cùng `z_ground+delta`, và bản chỉ một hộp bị trừ lượng đó. Đây là **controlled examples**, không phải ba lượt detector, không phải đáp án và không được import vào CVAT học viên.

1. So ảnh Side và tâm z giữa các ca; ghi số hộp lệch, độ lệch và những trường còn giữ nguyên.
2. Nếu cùng một lượng z ở cả batch: **dừng sửa tay**, báo LC kiểm phép chuyển frame, yêu cầu tạo lại prediction từ pipeline đúng.
3. Nếu một hộp lệch còn các hộp khác không đổi: kiểm bằng nhiều view để xem lỗi đối tượng. Không chốt lỗi pipeline chỉ vì một hộp nổi/chìm.
4. Nếu không có hộp bám cụm điểm: kiểm đầu vào, ROI và domain/checkpoint. Không vẽ bù cho đủ số lượng kỳ vọng.

**Checkpoint:** mỗi người ghi một quyết định “dừng batch / kiểm từng hộp / chưa đủ bằng chứng” với bằng chứng. Không import `case-*.json` hoặc coi bản “correct conversion” là cuboid đúng; nó chỉ giữ nguyên chuyển đổi z của prediction gốc.

## 5. Nộp bằng chứng và chuyển sang chỉnh/QC

Dùng [mẫu báo cáo](PRE-LABEL-REPORT.md). Nhóm tạo thư mục private `K4-DAY13-TenNhom/`, có `TEAMMATES.md` ghi thành viên/MSSV và `PRE-LABEL-REPORT.md`; output A/B/C và ca QC ở bên trong. Mỗi người có nhận xét riêng. Không commit dữ liệu, kết quả, danh sách người hoặc báo cáo đã điền vào repo công khai.

1. Người chạy thật ghi máy/architecture/image ID/PCD được cấp/cấu hình, số hộp và trạng thái thực hiện. Nếu chỉ phân tích bộ chuẩn bị trước thì ghi `provided-results`, không ghi `executed-by-group`.
2. Chuyển báo cáo vào thư mục thu bài private mà LC cấp tại mục 1. Repo/portal hiện **không có upload report, bộ chạy model từ xa hoặc kiểm tra hoàn thành phần này tự động**. LC ghi nhận thủ công trong sổ ca private.
3. LC kiểm ba output, nhận xét cá nhân, quyết định QC và quyền dữ liệu. Khi đạt phần pre-label, quay lại [HUONG-DAN.md](HUONG-DAN.md) để làm job nguồn/30 job được giao và QC ngẫu nhiên.

Nếu dùng kết quả có sẵn vì máy lỗi, LC ghi nhận phần phân tích đã làm và hẹn lượt chạy thật trên máy phòng khi có điều kiện; chưa chứng nhận kỹ năng chạy model. Không trừ điểm tự động vì chờ máy. Phần này dùng kiểm tra formative, chưa gắn điểm chính thức hoặc bảng điểm công khai.

PCD KITTI minh họa trên laptop khác frame Robotaxi của 30 job. **Không nạp prediction demo vào job Robotaxi khác frame.** Pre-annotations cho Robotaxi do người có quyền chuẩn bị, xác minh frame/schema/transform và import; học viên bắt đầu từ các hộp đó. Khi ca minh họa được cấp riêng trong CVAT, chỉ LC/operator import prediction gốc đúng frame, không import ca lỗi có kiểm soát.

**Hoàn tất:** LC đã nhận báo cáo, từng thành viên có nhận xét, việc chạy thật/có sẵn được ghi đúng và nhóm biết khi nào phải dừng pipeline trước khi sửa cuboid.
