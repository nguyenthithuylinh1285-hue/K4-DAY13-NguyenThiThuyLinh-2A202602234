# Ngày 13 — Robotaxi A: LiDAR 3D Object

Hôm nay bạn kiểm tra **pre-label từ PointPillars pretrained**, sửa cuboid 3D bằng bằng chứng và review bài của người khác. Bạn cần nhận ra khi nào lỗi nằm ở cả pipeline, khi nào chỉ một hộp cần chỉnh. Hộp model vẽ sẵn là gợi ý để bắt đầu, không phải đáp án.

Bài gồm hai phần: **nhóm 3–4 người** thực hành trên một PCD được cấp, rồi **cá nhân** sửa và QC các job được giao. Mỗi người có **phiên 240 phút riêng**; không có mốc 14h–18h chung và không ghép một cặp A↔B cố định.

| Tài liệu | Đọc khi nào |
| --- | --- |
| README.md (file này) | Đầu buổi: biết cần chuẩn bị, làm gì và nộp ở đâu |
| [Gói Student tải/chạy](bundle/README-STUDENT.md) | Tải ZIP đúng máy, chạy A/B/C không cần GPU |
| [PRE-LABEL.md](PRE-LABEL.md) | Trước khi sửa cuboid: chạy PointPillars và kiểm lỗi pipeline |
| [PRE-LABEL-REPORT.md](PRE-LABEL-REPORT.md), [TEAMMATES.md](TEAMMATES.md) | Ghi bằng chứng thí nghiệm và nhận xét từng thành viên |
| [HUONG-DAN.md](HUONG-DAN.md) | Thao tác nguồn → nộp v1 → QC → sửa và nộp v2 |
| [LABEL_GUIDELINE.md](LABEL_GUIDELINE.md) | Trước frame đầu tiên và khi không chắc class/hình học |
| [RUBRIC.md](RUBRIC.md) | Tự kiểm bài và hiểu LC kiểm tra những gì |

## Chuẩn bị đúng hệ thống và quyền dữ liệu

### Mở bài ở đâu?

LC gửi **link portal của ca và tài khoản CVAT**. Đăng nhập portal bằng tài khoản đó; khi mở bài nguồn, CVAT cũng cần đúng tài khoản. CVAT chương trình ở [cvat.note.transformerlabs.ai](https://cvat.note.transformerlabs.ai/), nhưng hãy vào đúng job bằng nút **Mở bài nguồn trong CVAT** trên portal để tránh nhầm ca. Link pilot dành cho LC không thay cho link lớp. Không tự tạo user mới nếu chưa thấy bài.

Phần sửa/QC chỉ cần trình duyệt có WebGL. Phần PointPillars dùng [gói Student KITTI](bundle/README-STUDENT.md) trên một máy chạy Docker CPU và Python 3.10+; không cần GPU. Nhóm không có máy phù hợp thực hành cùng máy LC của phòng. LC hỗ trợ theo lượt, không gửi inference cả lớp về ThinkPad. Trước ca, kiểm khả năng chạy với LC; bản đã thử trên Linux Intel/AMD và Mac Apple Silicon không bảo đảm mọi Windows/cấu hình đều chạy được.

### Dữ liệu nào được phép lấy về?

Repo có tài liệu, code và **một PCD KITTI Student** đã chuyển đổi, ghi nguồn và [giấy phép CC BY-NC-SA 3.0](data/ATTRIBUTION.md). Tải ZIP kèm image đúng kiến trúc từ [Releases](https://github.com/VinUni-AI20k/K4-L2L3-Day13-Robotaxi-LiDAR-3D-Object-Student/releases), không cần LC phát PCD riêng cho bước này. Dữ liệu KITTI chỉ dùng thí nghiệm học thuật phi thương mại và giữ ghi nguồn/giấy phép khi phát bản chuyển đổi. **Không có PCD/ảnh/output Robotaxi.** Gói Robotaxi LC vẫn chỉ cấp máy phòng; học viên không tự tải Robotaxi từ CVAT hay lấy gói LC về laptop.

1. Nhận đúng link/tài khoản của ca từ LC, không dùng tài khoản chung.
2. Xác nhận nhóm 3–4 người, máy chạy và đầu vào được cấp trước phần thực hành.
3. Giữ PCD/ảnh/annotation Robotaxi, report đã điền và danh sách thành viên trong kênh riêng do LC chỉ định; PCD KITTI chỉ chia sẻ theo giấy phép đã ghi. Không đăng ảnh/quay màn hình dữ liệu lên repo, VLearn, mạng xã hội hoặc nhóm công khai.
4. Không chia sẻ mật khẩu/token; báo lỗi bằng job ID và thông báo chữ.

**Sẵn sàng khi:** portal nhận đúng tài khoản, LC xác nhận môi trường thực hành và bạn biết nơi thu báo cáo private. Nếu chưa có bài hoặc dữ liệu chưa được cấp, báo LC thay vì mượn tài khoản hay tải một scan bất kỳ.

## Thực hành PointPillars trước khi sửa hộp

### Cần chứng minh điều gì?

PointPillars dùng pretrained KITTI, không train trong buổi này. Nhóm chạy **một PCD** qua ba cấu hình A/B/C; giữ nguyên checkpoint, score và phạm vi. So A/B để quan sát dịch z trước inference; so B/C để quan sát pillar. Đổi đúng một biến giúp bạn biết khác biệt đến từ thao tác nào. Phép dịch input có thể làm model đổi cả số hộp; nó khác với việc dịch cùng một lượng cho mọi hộp sau inference.

Theo [PRE-LABEL.md](PRE-LABEL.md), đọc JSON, ảnh Side và CSV. Sau đó kiểm ba ca z có chủ đích từ prediction thật để chọn hành động: dừng và kiểm pipeline nếu cả batch lệch, hoặc kiểm từng đối tượng nếu chỉ một hộp lệch. Những ca này chỉ để luyện nhận lỗi, không import vào CVAT và không được coi là nhãn đúng.

1. Mỗi thành viên bấm **Bắt đầu phiên 240 phút** khi bắt đầu phần pre-label. Thời gian này nằm trong phiên.
2. Chia vai vận hành, đọc JSON/cấu hình, xem hình học và ghi log; đổi vai giữa các lượt.
3. Chạy A/B/C trên máy được cấp hoặc máy LC phòng, ghi máy/image/input/config và kết quả thật.
4. Điền [báo cáo](PRE-LABEL-REPORT.md) với nhận xét riêng từng người, chuyển vào nơi thu private của LC và được LC kiểm trước phần nguồn.

**Hoàn tất khi:** có output ba lượt, quyết định về lỗi batch/từng hộp và nhận xét từng thành viên. Nếu chỉ xem kết quả chuẩn bị trước, ghi `provided-results`; LC chưa ghi nhận bạn đã tự chạy model. Portal chưa có nút upload hoặc khóa tự động bước pre-label. Không import prediction minh họa vào job khác frame.

## Làm nguồn, QC và phản hồi theo từng job

### Vòng làm bài vận hành thế nào?

Bạn có **30 job nguồn**, mỗi job là một frame. Bài riêng theo người; không cùng sửa một job với bạn trong nhóm. Sửa class, tâm, kích thước, hướng và hộp thiếu/thừa bằng PCD cùng ảnh camera. Rà cả năm class của schema. Điểm thưa hoặc vùng che khuất cần ghi sự chưa chắc; không co hộp sát vài điểm hoặc giữ nhãn chỉ vì model đã vẽ.

Sau khi nộp, **snapshot v1** là bản cố định để người khác đối chiếu. Người QC chỉ xem snapshot và gửi feedback; tác giả sửa tại job nguồn để tạo **v2**. Không cần làm hết 30 job trước khi QC, và không phải chờ một người cụ thể. Người nhận QC có thể khác lớp. Theo [HUONG-DAN.md](HUONG-DAN.md) để đọc nút, trạng thái và cách xử lý lỗi.

1. Mở nguồn → kiểm/sửa theo [guideline](LABEL_GUIDELINE.md) → **Save** trong CVAT.
2. Trở lại portal, khai đúng phạm vi rà rồi **Nộp job vào hàng đợi QC**. Đợi trạng thái từ `importing` sang `ready`; làm job khác trong lúc chờ.
3. Bấm **Nhận bài QC ngẫu nhiên** → **Xem snapshot 3D chỉ đọc** → ghi loại lỗi, ID/vùng, bằng chứng và đề xuất → **Nộp toàn bộ feedback**.
4. Khi nguồn có feedback, mở lại nguồn để đối chiếu/sửa → **Save** → chọn kết luận và **Nộp bản sửa và phản hồi** trên portal. Nếu thiếu bằng chứng, ghi rõ hoặc chọn **Cần coach phân xử**.

**Một vòng hoàn tất khi:** portal lưu feedback, tác giả đã nộp phản hồi/v2 và bài chuyển `done`. `done` cho biết đã hoàn thành vòng thao tác, không tự chứng nhận mọi cuboid đúng. Chỉ đổi `completed` trong CVAT không thay cho nộp portal. Khi đã nộp v1, không sửa tiếp bài đó trong lúc bàn giao/chờ QC; làm job khác rồi quay lại sau feedback.

## Nộp gì và tự kiểm trước khi kết thúc?

### Báo cáo nhóm và bài cá nhân nộp khác nhau

Báo cáo thí nghiệm là sản phẩm nhóm, thu riêng tại nơi LC cấp. Tạo thư mục `K4-DAY13-TenNhom/` với `TEAMMATES.md`, `PRE-LABEL-REPORT.md` và output được phép giữ. Bản đã điền chứa danh tính/dữ liệu, không commit lên repo public. Nếu dùng máy LC, để bằng chứng trong nơi lưu riêng của phòng và theo hướng dẫn LC, không tự sao chép Robotaxi ra ngoài.

Phần cá nhân nộp trực tiếp qua CVAT và portal: annotation đã Save, v1, feedback và phản hồi/v2. Không nộp ZIP hay CSV thay thế vòng này. Mỗi người chịu trách nhiệm thao tác của mình dù phần pre-label có làm chung. Thời lượng gợi ý là 60 phút pre-label, 115 phút nguồn, 50 phút QC và 15 phút phản hồi; các chặng có thể xen kẽ. Đây không phải cam kết làm đủ 30 frame full-range và 30 QC trong thời gian còn lại.

1. Kiểm báo cáo nhóm đã đến LC và từng người có nhận xét riêng, ghi đúng đã chạy thật hay chỉ phân tích.
2. Kiểm nguồn đã Save trước mỗi lượt nộp; phạm vi toàn frame chỉ chọn khi thật sự tìm cả thiếu và thừa.
3. Kiểm feedback đã **nộp**, không còn chỉ trong ô đang gõ; không đóng tab giữa lượt review chưa lưu.
4. Xem **Hạn phản hồi** từng bài. Feedback đến muộn có cửa sổ ít nhất 24 giờ sau mốc muộn hơn giữa cuối phiên và lúc feedback đến; theo hạn portal hiển thị.

**Kiểm cuối:** bài đang chờ reviewer được ghi đúng trạng thái; bạn không bị trừ điểm vì đợi hàng đợi. Điểm hiện dùng formative và chỉ quản trị thấy; xem [RUBRIC.md](RUBRIC.md) để tự kiểm thay vì suy ra bài đúng từ số hộp hoặc score model.

## Câu hỏi hay gặp

**Không có job hoặc đăng nhập lỗi?** Kiểm đúng portal/ca, đúng tài khoản ở cả portal và CVAT; báo LC kèm username/job ID, không gửi mật khẩu. Không tự tạo tài khoản mới.

**Hàng đợi QC trống?** Làm job nguồn khác hoặc quay lại sau. Không cần chờ một cặp cố định. Bài thực hành coach nếu có là bài hiệu chuẩn, không phải đáp án.

**QC có giới hạn thời gian không?** Mỗi lượt giữ quyền 20 phút; portal/viewer gia hạn khi tab hoạt động. Tab ẩn/mất mạng lâu có thể mất lượt. Nộp feedback trước khi đóng/tải lại; mất quyền thì quay về portal kiểm tra và báo LC nếu có sự cố.

**PCD giật hoặc tải lâu?** Giữ một job mở, đóng bớt tab, kiểm mạng/WebGL và báo LC với job ID/thông báo. Không tải PCD về để vượt lỗi.

**Máy nhóm không chạy Docker?** Làm cùng máy LC phòng theo lượt. Kết quả có sẵn hỗ trợ phân tích nhưng phải ghi rõ chưa trực tiếp chạy.

**Repo public có phải được phép public Robotaxi không?** Không. Gói Student KITTI được cấp theo giấy phép riêng; Robotaxi, tài khoản và bài làm vẫn riêng theo ca.
