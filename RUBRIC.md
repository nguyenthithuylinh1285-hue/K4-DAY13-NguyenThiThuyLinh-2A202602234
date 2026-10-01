# Day 13 — Tiêu chí tự kiểm và phản hồi formative

Tài liệu này giúp bạn biết bài cần có bằng chứng gì. Điểm trong pilot/ca hiện tại **chỉ quản trị thấy**; repo không công bố điểm cá nhân, đáp án hay trọng số điểm môn chính thức. Không áp dụng bảng 70/30 của script nhóm cũ cho luồng này.

## 1. Phần PointPillars theo nhóm

LC kiểm báo cáo tại nơi thu private của phòng. Mỗi thành viên có vai trò và nhận xét riêng; một người chạy không có nghĩa các thành viên khác được bỏ phần phân tích.

| Cần có | Bằng chứng để tự kiểm |
| --- | --- |
| Đầu vào/môi trường đúng | PCD được cấp, máy/architecture, image/checkpoint, phạm vi và cấu hình được ghi |
| Thực hiện được mô tả trung thực | Phân biệt chạy bởi nhóm, chạy trên máy LC và chỉ đọc `provided-results` |
| Ba lượt có thể đối chiếu | JSON/Side/CSV A/B/C, cùng frame/checkpoint/score/ROI, đổi đúng một biến |
| Đọc kết quả có cơ sở | So A/B và B/C bằng số liệu và file, không chọn cấu hình vì nhiều hộp hơn |
| Phân biệt lỗi pipeline/đối tượng | Quyết định dừng batch hay kiểm từng hộp với bằng chứng; không import ca lỗi |
| Nhận xét cá nhân | Vai trò, quan sát, phép z thuận/ngược và điều chưa chắc của từng người |

**Tự kiểm:** LC đã nhận báo cáo, output được giữ riêng đúng quyền và phần chưa thực hiện được ghi rõ. Bước này do LC ghi nhận thủ công; portal chưa tự upload/chấm báo cáo pre-label.

## 2. Phần sửa cuboid và QC cá nhân

Chất lượng được xem qua bằng chứng hình học và cách bạn xử lý feedback. Nộp đủ thao tác không thay thế việc kiểm hộp; số hộp và confidence không tự chứng minh hộp đúng. Dùng [LABEL_GUIDELINE.md](LABEL_GUIDELINE.md) để kiểm class và hình học.

| Cần có | Bằng chứng để tự kiểm |
| --- | --- |
| Rà đúng phạm vi | Kiểm hộp thiếu/thừa và cả năm class; khai một phần/toàn frame đúng thực tế |
| Cuboid có cơ sở | Class, tâm, dài/rộng/cao, hướng, đáy cục bộ được đối chiếu qua nhiều view/camera |
| v1 được nộp đúng | Save nguồn trước khi nộp portal; không sửa bản QC hoặc sửa tiếp nguồn khi chờ bàn giao |
| Feedback hữu ích | ID hoặc vùng, loại lỗi, góc nhìn/bằng chứng, đề xuất hoặc lý do giữ nguyên |
| v2/phản hồi có cơ sở | Đối chiếu nhận xét, Save và nộp phản hồi; ghi lý do khi bất đồng/cần coach |
| Trung thực khi thiếu bằng chứng | Nêu điều chưa chắc; không bịa hộp, tự nhận rà toàn frame hoặc tự nhận chạy model |

**Tự kiểm:** feedback/phản hồi đã nộp và trạng thái portal đúng. `done` chỉ là vòng thao tác hoàn tất. Khi chưa có reviewer, tiếp tục nguồn; chờ reviewer không bị trừ điểm. Không suy ra phải đủ 30 lượt QC vì được giao 30 job nguồn.

## 3. Hiểu đúng kết quả đánh giá

Có ba loại kết quả riêng: **quy trình formative**, **độ khớp nhãn nguồn chưa phân xử**, và **chất lượng theo reference đã duyệt**. Prediction và nhãn nguồn đều có thể sai. Vì vậy, khớp nhãn nguồn hơn không nhất thiết nghĩa bạn sửa đúng hơn; độ đúng cuboid cần reference được kiểm tra và duyệt.

1. Dùng guideline để tự rà, không cố bắt chước prediction hoặc tìm đáp án riêng.
2. Nêu bằng chứng nếu không đồng ý feedback; chọn **Cần coach phân xử** khi cần.
3. Theo hạn phản hồi trên thẻ bài; báo sự cố kèm job ID và thông báo chữ.

**Hoàn tất tự kiểm khi:** bạn giải thích được phần đã làm, phần đang chờ và phần chưa đủ cơ sở. Kết quả chưa có reference/chưa đủ điều kiện không tự được coi là 0 điểm. LC participant và học viên không xem bảng điểm riêng của quản trị.
