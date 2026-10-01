# Ngày 13 — Sửa cuboid nguồn và QC chéo trên portal

Lab có hai phần: **thực hành PointPillars theo nhóm 3–4**, rồi **chỉnh/QC cá nhân**. Mỗi người có 30 job nguồn, mỗi job một frame. Bạn sửa cuboid trong CVAT, Save từng job rồi nộp qua portal để người khác QC. Bạn cũng nhận bài QC ngẫu nhiên và phản hồi nhận xét trên bài của mình. Phần chỉnh/QC không nộp file; phần PointPillars có báo cáo nhóm private và nhận xét riêng từng người.

Coach cung cấp địa chỉ portal và tài khoản CVAT của ca học. Đăng nhập portal bằng tài khoản đó. Robotaxi và ảnh camera mở trong hệ thống; không tải dữ liệu về máy. Trước khi chỉnh cuboid, nhóm làm [phần PointPillars bắt buộc](PRE-LABEL.md) trên một PCD minh họa được cấp, bằng Docker CPU của máy nhóm hoặc máy LC phòng. Không cần GPU và không gửi inference lớp về ThinkPad. Người có quyền vẫn chuẩn bị pre-annotations Robotaxi cho các job CVAT. Hộp dự đoán chỉ là điểm khởi đầu, chưa phải đáp án. Đọc [quy tắc gán nhãn và QC](LABEL_GUIDELINE.md) trước khi sửa frame đầu tiên.

Bắt đầu tại [README.md](README.md); dùng [tiêu chí tự kiểm](RUBRIC.md) khi hoàn thiện bài. Các sơ đồ trong guideline là minh họa, không chứa PCD hoặc ảnh camera thật.

## Bắt đầu phiên và làm job nguồn

Trong portal, bấm **Bắt đầu phiên 240 phút** khi bắt đầu phần PointPillars. Đồng hồ tính riêng cho từng người; thời gian thí nghiệm nằm trong 240 phút. Nhóm hoàn thành thí nghiệm và LC kiểm báo cáo theo [PRE-LABEL.md](PRE-LABEL.md), rồi mới chuyển sang job nguồn. Bước kiểm này do LC ghi nhận, portal chưa khóa tự động. Mở thẻ **Bài nguồn** rồi chọn **Mở bài nguồn trong CVAT**. CVAT cần đăng nhập riêng bằng đúng tài khoản của ca. Nếu trình duyệt đang giữ tài khoản khác, đăng xuất khỏi CVAT và đăng nhập lại; không chia sẻ tài khoản để vượt lỗi quyền. Bạn có thể xen kẽ làm nguồn, QC và sửa theo feedback; không cần xong cả 30 job mới nhận QC.

Trong CVAT, rà toàn frame bằng nhiều góc nhìn, kiểm cả hộp đã có và đối tượng bị bỏ sót. Chỉnh class, vị trí, kích thước, hướng và đáy theo bằng chứng. Xóa hộp thừa; thêm hộp thiếu khi có cơ sở. Rà cả năm class của schema, kể cả hai class model không dự đoán. Nếu PCD thưa, vùng bị che hoặc thiếu intensity, giữ sự chưa chắc; không dựng hộp theo tưởng tượng và không co hộp theo vài điểm gần nhất.

Bấm **Save** trong CVAT. Trên portal, chọn **Toàn frame, gồm hộp thiếu/thừa** chỉ khi đã tìm cả đối tượng thiếu lẫn hộp thừa trên toàn frame; nếu chưa, chọn **Một phần**. Đây là phạm vi tự khai, không thay cho thao tác rà. Checkpoint: CVAT đã lưu sửa đổi ở đúng job và phạm vi portal phản ánh phần thực sự đã kiểm.

## Nộp từng job vào hàng đợi QC

Sau **Save** trong CVAT, trở lại thẻ nguồn và bấm **Nộp job vào hàng đợi QC**. Portal chụp bản v1 cố định cho người QC. Kiểm tra trạng thái thẻ và, khi có, mở **Đối chiếu snapshot v1 chỉ đọc** để xem bản đã nộp. Sửa tiếp trong CVAT không làm bản v1 tự đổi.

Bạn có thể chuyển ngay sang job nguồn khác. Trong lúc bàn giao và chờ QC, không sửa tiếp bài vừa nộp. CVAT chương trình không bảo đảm khóa nguồn; hãy theo trạng thái portal. Sau feedback, bạn sẽ sửa nguồn và nộp bản v2 riêng. Nếu portal báo snapshot sai lệch hoặc chặn nộp, báo coach đối chiếu; không sửa bản QC. Checkpoint: job đã rời `draft`; đợi chuyển qua `importing` rồi `ready` trước khi QC. Khi snapshot sẵn sàng, xem được v1. Chưa có feedback không có nghĩa bài đã đúng.

## Nhận và viết QC chéo

Bấm **Nhận bài QC ngẫu nhiên** khi muốn nhận bài đã sẵn sàng. Reviewer có thể khác lớp; không có cặp cố định và bạn không QC bài mình. Nếu chưa có bài phù hợp, làm job nguồn tiếp hoặc quay lại sau. Chờ hàng đợi không bị trừ điểm. Thẻ **Bài QC thực hành của coach** là bài luyện tập, không phải đáp án chuẩn.

Ở thẻ **QC**, chọn **Xem snapshot 3D chỉ đọc**. Viewer hiển thị PCD, cuboid v1 và ảnh camera cùng frame. Dùng **Trên**, **Trước**, **Bên**, **Đặt lại**, chọn hộp theo ID, xoay, dịch và phóng to để kiểm tra. Viewer có thể lấy mẫu điểm để hiển thị. Không sửa hộp trong viewer hoặc job QC của CVAT; hãy viết nhận xét để tác giả sửa tại job nguồn.

Mỗi nhận xét cần đủ **Loại lỗi**, **ID QC hoặc vùng tọa độ khi thiếu hộp**, **Bằng chứng/góc nhìn/điều chưa chắc**, và **Đề xuất sửa hoặc lý do giữ nguyên**. Dùng **Thêm nhận xét** cho lỗi khác. Ví dụ minh họa, không phải dữ liệu thật: “ID QC 17 · Sai class · góc Trên và ảnh camera cho thấy xe hai bánh · kiểm lại và đổi `vehicles` sang `two-wheels` nếu xác nhận.” Nếu thiếu đối tượng chưa có ID, mô tả vùng đủ rõ để tìm lại; đừng bịa ID. Chọn phạm vi **Một phần** hoặc **Toàn frame, gồm hộp thiếu/thừa** theo phần đã rà. **Không thấy lỗi trong phần đã rà** không có nghĩa toàn frame đúng khi bạn mới kiểm một phần.

Bấm **Nộp toàn bộ feedback** trước khi đóng hoặc tải lại trang: nội dung đang gõ chưa phải feedback đã lưu. Lượt QC có lease 20 phút; portal/viewer gia hạn mỗi phút khi tab hoạt động. Tab ẩn hoặc mất mạng lâu có thể làm lượt được giao lại. Nếu hết quyền, quay về portal kiểm tra trạng thái. Hết phiên 240 phút không nhận lượt mới; lượt đang giữ còn lease có tối đa 20 phút để hoàn tất. Checkpoint: portal đã nhận feedback và form của lượt đó biến mất.

## Sửa bài nguồn theo feedback

Khi bài của bạn có **Feedback**, đọc nhận xét, mở **Mở bài nguồn trong CVAT**, đối chiếu PCD, ảnh và snapshot v1 rồi sửa điều có bằng chứng. Bấm **Save** trong CVAT. Nếu chưa đồng ý hoặc cần coach phân xử, nêu rõ phần thiếu bằng chứng; không sửa chỉ để đóng bước.

Trên portal, chọn **Kết luận** là **Đồng ý**, **Chưa đồng ý** hoặc **Cần coach phân xử**. Trong ô **Save ở bài nguồn rồi ghi đã sửa gì / lý do**, ghi thay đổi hoặc lý do giữ nguyên. Bấm **Nộp bản sửa và phản hồi** để nộp v2. Ví dụ minh họa: “Đã đổi class hộp ID 17 sau khi kiểm ảnh và góc Trên; giữ kích thước vì phần đuôi bị che, cần coach xem nếu còn nghi ngờ.”

Portal hiển thị **Hạn phản hồi** của từng bài. Cửa sổ hoàn thiện cộng ít nhất 24 giờ vào mốc muộn hơn giữa lúc kết thúc phiên và lúc nhận feedback. Dựa vào hạn trên thẻ, không tự lấy lúc kết thúc 240 phút làm hạn sửa. Chờ reviewer không bị trừ điểm. Checkpoint: portal lưu phản hồi và bản v2 của đúng job; nếu trạng thái không đổi, xem thông báo lỗi và kiểm lại Save.

## Tự kiểm trước khi kết thúc

- Job nguồn đã **Save** trong CVAT trước khi nộp v1 hoặc v2 trên portal.
- Phạm vi tự khai đúng phần đã rà, gồm tìm hộp thiếu và hộp thừa nếu chọn toàn frame.
- Feedback có ID hoặc vùng, loại lỗi, bằng chứng và đề xuất; điểm chưa chắc được nói rõ.
- Bài có feedback đã được đối chiếu ở nguồn, Save và **Nộp bản sửa và phản hồi** trước hạn hiện trên thẻ.

Portal không hiển thị điểm cho học viên. Điểm quy trình, thử độ khớp với nhãn nguồn chưa phân xử và điểm chất lượng sau khi quản trị duyệt reference là các kết quả riêng chỉ dành cho quản trị; không phải tuyên bố điểm môn chính thức. Nhãn nguồn và prediction đều có thể sai.
