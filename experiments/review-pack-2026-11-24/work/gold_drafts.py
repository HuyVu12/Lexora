# -*- coding: utf-8 -*-
# Draft norms per sample index: (norms, reason, confidence). Norm = (modality, cue, slots)
O, P, E, M, U = "obligation", "prohibition", "entitlement", "permission", "unknown"


def n(m, cue=None, **s):
    return (m, cue, s)


D = {}


def d(i, norms, reason, conf="vừa"):
    D[i] = (norms, reason, conf)


# Thong tu 10/2020 Dieu 3 (items 0-23)
d(0, [n(U, None, action="lấy theo", object="tên của doanh nghiệp, cơ quan, tổ chức, hợp tác xã, liên hiệp hợp tác xã", conditions="đối với doanh nghiệp, cơ quan, tổ chức, hợp tác xã, liên hiệp hợp tác xã"),
      n(U, None, action="lấy theo", object="tên tổ hợp tác", conditions="đối với tổ hợp tác"),
      n(U, None, action="lấy theo", object="họ tên của người đại diện hộ gia đình, cá nhân", conditions="đối với hộ gia đình, cá nhân")],
  "Hướng dẫn cách ghi tên người sử dụng lao động trong hợp đồng, tách theo ba loại chủ thể; câu không có từ tình thái nên để chưa rõ loại.", "thấp")
d(1, [n(U, None, action="lấy theo", object="địa chỉ ghi trong giấy chứng nhận đăng ký doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã", conditions="đối với doanh nghiệp, cơ quan, tổ chức, hợp tác xã, liên hiệp hợp tác xã"),
      n(U, None, action="lấy theo", object="địa chỉ trong hợp đồng hợp tác", conditions="đối với tổ hợp tác"),
      n(U, None, action="lấy theo", object="địa chỉ nơi cư trú của hộ gia đình, cá nhân đó", conditions="đối với hộ gia đình, cá nhân")],
  "Hướng dẫn cách ghi địa chỉ người sử dụng lao động, tách theo ba loại chủ thể; không có từ tình thái.", "thấp")
d(2, [n(U, None, action="ghi theo", object="họ tên, chức danh của người có thẩm quyền giao kết hợp đồng lao động")],
  "Hướng dẫn ghi họ tên, chức danh người giao kết bên phía người sử dụng lao động; không có từ tình thái.", "thấp")
d(3, [], "Liệt kê nội dung thông tin cần có, dạng cụm danh từ, không tự nêu quy tắc xử sự (có thể coi là quy phạm nếu hiểu là phải ghi).", "thấp")
d(4, [], "Liệt kê loại thông tin (số giấy phép lao động), cụm danh từ, không nêu ai phải làm gì.", "thấp")
d(5, [], "Liệt kê thông tin về người đại diện theo pháp luật, cụm danh từ, không nêu ai phải làm gì.", "thấp")
d(6, [], "Giải thích nội dung mục Công việc; chữ phải trong mệnh đề quan hệ chỉ mô tả công việc, không đặt nghĩa vụ mới.", "thấp")
d(7, [n(U, None, action="ghi đầy đủ", object="các địa điểm đó", conditions="trường hợp người lao động làm việc có tính chất thường xuyên ở nhiều địa điểm khác nhau")],
  "Khi làm việc ở nhiều địa điểm thì ghi đủ các địa điểm; không có từ tình thái.", "thấp")
d(8, [], "Giải thích nội dung mục Thời hạn hợp đồng, không nêu ai phải làm gì.", "vừa")
d(9, [n(U, None, action="ghi", object="mức lương tính theo thời gian của công việc hoặc chức danh"),
      n(U, None, action="ghi", object="mức lương tính theo thời gian để xác định đơn giá sản phẩm hoặc lương khoán", conditions="đối với người lao động hưởng lương theo sản phẩm hoặc lương khoán")],
  "Hướng dẫn cách ghi mức lương, một quy tắc chung và một cho lương sản phẩm hoặc khoán; không có từ tình thái.", "thấp")
d(10, [], "Câu dẫn sang danh sách b1, b2, không nêu quy tắc.", "vừa")
d(11, [], "Mô tả loại phụ cấp lương (b1), không nêu ai phải làm gì.", "vừa")
d(12, [], "Mô tả loại phụ cấp lương (b2), không nêu ai phải làm gì.", "vừa")
d(13, [], "Câu dẫn sang danh sách c1, c2, không nêu quy tắc.", "vừa")
d(14, [], "Mô tả loại khoản bổ sung (c1), không nêu ai phải làm gì.", "vừa")
d(15, [], "Mô tả loại khoản bổ sung (c2), không nêu ai phải làm gì.", "vừa")
d(16, [n(U, None, action="ghi thành mục riêng trong hợp đồng lao động", conditions="Đối với các chế độ và phúc lợi khác")],
  "Các chế độ và phúc lợi khác được ghi thành mục riêng trong hợp đồng; không có từ tình thái.", "thấp")
d(17, [n(U, None, actor="hai bên", action="xác định", object="Hình thức trả lương")],
  "Hai bên xác định hình thức trả lương theo Điều 96 BLLĐ; không có từ tình thái.", "thấp")
d(18, [n(U, None, actor="hai bên", action="xác định", object="Kỳ hạn trả lương")],
  "Hai bên xác định kỳ hạn trả lương theo Điều 97 BLLĐ; không có từ tình thái.", "thấp")
d(19, [], "Mô tả nội dung mục nâng bậc, nâng lương (theo thỏa thuận hoặc quy định có sẵn), không đặt quy tắc riêng.", "thấp")
d(20, [], "Mô tả nội dung mục thời giờ làm việc, nghỉ ngơi (theo thỏa thuận hoặc quy định), không đặt quy tắc riêng.", "thấp")
d(21, [], "Mô tả nội dung mục trang bị bảo hộ lao động, không đặt quy tắc riêng.", "thấp")
d(22, [], "Chỉ dẫn chiếu sang pháp luật về bảo hiểm, không tự nêu quy tắc.", "vừa")
d(23, [], "Mô tả nội dung mục đào tạo, bồi dưỡng, không đặt quy tắc riêng.", "vừa")

# Nghi dinh 145/2020 Dieu 54 (items 24-36)
d(24, [], "Định nghĩa tiền lương theo thời gian.")
d(25, [], "Định nghĩa tiền lương tháng.", "cao")
d(26, [], "Định nghĩa tiền lương tuần.", "cao")
d(27, [n(U, None, object="tiền lương tuần", action="xác định", conditions="Trường hợp hợp đồng lao động thỏa thuận tiền lương theo tháng", quantities="bằng tiền lương tháng nhân với 12 tháng và chia cho 52 tuần")],
  "Quy tắc tính tiền lương tuần từ lương tháng; không có từ tình thái.", "thấp")
d(28, [], "Định nghĩa tiền lương ngày.", "cao")
d(29, [n(U, None, object="tiền lương ngày", action="xác định", conditions="Trường hợp hợp đồng lao động thỏa thuận tiền lương theo tháng", quantities="bằng tiền lương tháng chia cho số ngày làm việc bình thường trong tháng")],
  "Quy tắc tính tiền lương ngày từ lương tháng; không có từ tình thái.", "thấp")
d(30, [n(U, None, object="tiền lương ngày", action="xác định", conditions="Trường hợp hợp đồng lao động thỏa thuận tiền lương theo tuần", quantities="bằng tiền lương tuần chia cho số ngày làm việc trong tuần")],
  "Quy tắc tính tiền lương ngày từ lương tuần; không có từ tình thái.", "thấp")
d(31, [], "Định nghĩa tiền lương giờ.", "cao")
d(32, [n(U, None, object="tiền lương giờ", action="xác định", conditions="Trường hợp hợp đồng lao động thỏa thuận tiền lương theo tháng hoặc theo tuần hoặc theo ngày", quantities="bằng tiền lương ngày chia cho số giờ làm việc bình thường trong ngày")],
  "Quy tắc tính tiền lương giờ từ lương ngày; không có từ tình thái.", "thấp")
d(33, [], "Định nghĩa tiền lương theo sản phẩm.")
d(34, [], "Định nghĩa tiền lương khoán.")
d(35, [n(M, "được", object="Tiền lương của người lao động", action="trả bằng tiền mặt hoặc trả qua tài khoản cá nhân của người lao động được mở tại ngân hàng")],
  "Lương được trả bằng tiền mặt hoặc qua tài khoản ngân hàng, là lựa chọn nên xếp Được phép (có thể xếp Quyền).", "thấp")
d(36, [n(O, "phải", actor="Người sử dụng lao động", action="trả", object="các loại phí liên quan đến việc mở tài khoản và chuyển tiền lương", conditions="khi chọn trả lương qua tài khoản cá nhân của người lao động")],
  "Người sử dụng lao động phải trả phí mở tài khoản và chuyển lương khi chọn trả qua tài khoản.", "cao")

# Nghi dinh 145/2020 Dieu 70 (items 37-45)
d(37, [n(U, None, actor="người sử dụng lao động", action="tiến hành lập biên bản vi phạm", conditions="Khi phát hiện người lao động có hành vi vi phạm kỷ luật lao động tại thời điểm xảy ra hành vi vi phạm"),
       n(U, None, actor="người sử dụng lao động", action="thông báo", recipient="tổ chức đại diện người lao động tại cơ sở mà người lao động là thành viên, người đại diện theo pháp luật của người lao động chưa đủ 15 tuổi", conditions="Khi phát hiện người lao động có hành vi vi phạm kỷ luật lao động tại thời điểm xảy ra hành vi vi phạm")],
  "Trình tự xử lý kỷ luật: lập biên bản và thông báo khi phát hiện vi phạm; không có từ tình thái nên chưa rõ loại (có thể hiểu là nghĩa vụ).", "thấp")
d(38, [n(U, None, actor="người sử dụng lao động", action="thực hiện thu thập", object="chứng cứ chứng minh lỗi của người lao động", conditions="Trường hợp người sử dụng lao động phát hiện hành vi vi phạm kỷ luật lao động sau thời điểm hành vi vi phạm đã xảy ra")],
  "Khi phát hiện vi phạm muộn thì thu thập chứng cứ; không có từ tình thái.", "thấp")
d(39, [n(U, None, actor="người sử dụng lao động", action="thông báo", object="nội dung, thời gian, địa điểm tiến hành cuộc họp xử lý kỷ luật lao động, họ tên người bị xử lý kỷ luật lao động, hành vi vi phạm bị xử lý kỷ luật lao động", recipient="các thành phần phải tham dự họp quy định tại điểm b, điểm c khoản 1 Điều 122 của Bộ luật Lao động", deadlines="Ít nhất 05 ngày làm việc trước ngày tiến hành họp xử lý kỷ luật lao động"),
       n(U, None, actor="người sử dụng lao động", action="bảo đảm", object="các thành phần này nhận được thông báo", deadlines="trước khi diễn ra cuộc họp")],
  "Báo trước họp kỷ luật ít nhất 05 ngày làm việc và bảo đảm người dự nhận được thông báo; không có từ tình thái.", "thấp")
d(40, [n(O, "phải", actor="các thành phần phải tham dự họp quy định tại điểm b, điểm c khoản 1 Điều 122 của Bộ luật Lao động", action="xác nhận tham dự cuộc họp", recipient="người sử dụng lao động", conditions="Khi nhận được thông báo của người sử dụng lao động")],
  "Người dự họp phải xác nhận tham dự với người sử dụng lao động khi nhận thông báo.", "cao")
d(41, [n(U, None, actor="người lao động và người sử dụng lao động", action="thỏa thuận", object="việc thay đổi thời gian, địa điểm họp", conditions="Trường hợp một trong các thành phần phải tham dự không thể tham dự họp theo thời gian, địa điểm đã thông báo"),
       n(U, None, actor="người sử dụng lao động", action="quyết định", object="thời gian, địa điểm họp", conditions="trường hợp hai bên không thỏa thuận được")],
  "Hai quy tắc: hai bên thỏa thuận đổi thời gian, địa điểm; nếu không thỏa thuận được thì người sử dụng lao động quyết định.", "thấp")
d(42, [n(U, None, actor="Người sử dụng lao động", action="tiến hành họp xử lý kỷ luật lao động", conditions="theo thời gian, địa điểm đã thông báo quy định tại điểm a, điểm b khoản này")],
  "Họp xử lý kỷ luật theo thời gian, địa điểm đã thông báo; không có từ tình thái.", "thấp")
d(43, [n(U, None, actor="người sử dụng lao động", action="vẫn tiến hành họp xử lý kỷ luật lao động", conditions="Trường hợp một trong các thành phần phải tham dự họp quy định tại điểm b, điểm c khoản 1 Điều 122 của Bộ luật Lao động không xác nhận tham dự cuộc họp hoặc vắng mặt")],
  "Người dự họp không xác nhận hoặc vắng mặt thì người sử dụng lao động vẫn họp; không có từ tình thái.", "thấp")
d(44, [n(O, "phải", object="Nội dung cuộc họp xử lý kỷ luật lao động", action="được lập thành biên bản"),
       n(O, "phải", object="Nội dung cuộc họp xử lý kỷ luật lao động", action="thông qua", deadlines="trước khi kết thúc cuộc họp"),
       n(O, "phải", object="Nội dung cuộc họp xử lý kỷ luật lao động", action="có chữ ký của người tham dự cuộc họp quy định tại điểm b, điểm c khoản 1 Điều 122 của Bộ luật Lao động"),
       n(U, None, actor="người ghi biên bản", action="nêu rõ", object="họ tên, lý do không ký (nếu có) vào nội dung biên bản", conditions="trường hợp có người không ký vào biên bản")],
  "Biên bản cuộc họp phải được lập, thông qua và có chữ ký; nếu có người không ký thì người ghi biên bản nêu rõ họ tên, lý do.", "vừa")
d(45, [n(U, None, actor="người có thẩm quyền xử lý kỷ luật lao động", action="ban hành", object="quyết định xử lý kỷ luật lao động", deadlines="Trong thời hiệu xử lý kỷ luật lao động quy định tại khoản 1, khoản 2 Điều 123 của Bộ luật Lao động"),
       n(U, None, actor="người có thẩm quyền xử lý kỷ luật lao động", action="gửi", object="quyết định xử lý kỷ luật lao động", recipient="các thành phần phải tham dự quy định tại điểm b, điểm c khoản 1 Điều 122 của Bộ luật Lao động", deadlines="Trong thời hiệu xử lý kỷ luật lao động quy định tại khoản 1, khoản 2 Điều 123 của Bộ luật Lao động")],
  "Ban hành quyết định xử lý kỷ luật và gửi cho người dự họp trong thời hiệu; không có từ tình thái.", "thấp")

# BLLD 2019 Dieu 3 (46-59)
for i in (46, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59):
    d(i, [], "Định nghĩa khái niệm, không nêu quy tắc xử sự.", "cao")
d(47, [], "Định nghĩa độ tuổi lao động tối thiểu (đủ 15 tuổi), nằm trong Điều giải thích từ ngữ.", "vừa")
d(48, [n(O, "phải", actor="người sử dụng lao động", action="có năng lực hành vi dân sự đầy đủ", conditions="trường hợp người sử dụng lao động là cá nhân")],
  "Câu định nghĩa nhưng mệnh đề sau đặt yêu cầu: người sử dụng lao động là cá nhân phải có năng lực hành vi dân sự đầy đủ.", "thấp")
d(57, [], "Làm rõ trường hợp không bị xem là phân biệt đối xử, mang tính giải thích.", "thấp")

# BLLD Dieu 26 and 32
d(60, [n(O, "phải", actor="hai bên", action="thỏa thuận", object="Tiền lương của người lao động trong thời gian thử việc", quantities="ít nhất phải bằng 85% mức lương của công việc đó")],
  "Lương thử việc do hai bên thỏa thuận nhưng ít nhất bằng 85% lương công việc đó (nghĩa vụ).", "cao")
d(61, [], "Định nghĩa người lao động làm việc không trọn thời gian.", "cao")
d(62, [n(U, None, actor="Người lao động", action="thỏa thuận", recipient="người sử dụng lao động", object="làm việc không trọn thời gian", conditions="khi giao kết hợp đồng lao động")],
  "Người lao động thỏa thuận với người sử dụng lao động về làm việc không trọn thời gian khi giao kết hợp đồng; không có từ tình thái.", "thấp")
d(63, [n(E, "được", actor="Người lao động làm việc không trọn thời gian", action="hưởng", object="lương"),
       n(E, "được", actor="Người lao động làm việc không trọn thời gian", action="bình đẳng trong thực hiện quyền và nghĩa vụ với người lao động làm việc trọn thời gian"),
       n(E, "được", actor="Người lao động làm việc không trọn thời gian", action="bình đẳng về cơ hội"),
       n(E, "được", actor="Người lao động làm việc không trọn thời gian", action="không bị phân biệt đối xử"),
       n(E, "được", actor="Người lao động làm việc không trọn thời gian", action="bảo đảm an toàn, vệ sinh lao động")],
  "Người lao động không trọn thời gian được hưởng lương và các quyền bình đẳng; tách năm quyền theo dấu chấm phẩy và dấu phẩy.", "vừa")

# BLLD Dieu 34 (64-77): grounds for termination, no cue
G = "Một trường hợp chấm dứt hợp đồng lao động (liệt kê dưới tên Điều); không có từ tình thái nên để chưa rõ loại, có thể coi là không quy phạm."
d(64, [n(U, None, conditions="Hết hạn hợp đồng lao động", exceptions="trừ trường hợp quy định tại khoản 4 Điều 177 của Bộ luật này")], G, "thấp")
d(65, [n(U, None, conditions="Đã hoàn thành công việc theo hợp đồng lao động")], G, "thấp")
d(66, [n(U, None, actor="Hai bên", action="thỏa thuận chấm dứt", object="hợp đồng lao động")], G, "thấp")
d(67, [n(U, None, conditions="Người lao động bị kết án phạt tù nhưng không được hưởng án treo hoặc không thuộc trường hợp được trả tự do theo quy định tại khoản 5 Điều 328 của Bộ luật Tố tụng hình sự, tử hình hoặc bị cấm làm công việc ghi trong hợp đồng lao động theo bản án, quyết định của Tòa án đã có hiệu lực pháp luật")], G, "thấp")
d(68, [n(U, None, conditions="Người lao động là người nước ngoài làm việc tại Việt Nam bị trục xuất theo bản án, quyết định của Tòa án đã có hiệu lực pháp luật, quyết định của cơ quan nhà nước có thẩm quyền")], G, "thấp")
d(69, [n(U, None, conditions="Người lao động chết; bị Tòa án tuyên bố mất năng lực hành vi dân sự, mất tích hoặc đã chết")], G, "thấp")
d(70, [n(U, None, conditions="Người sử dụng lao động là cá nhân chết; bị Tòa án tuyên bố mất năng lực hành vi dân sự, mất tích hoặc đã chết")], G, "thấp")
d(71, [n(U, None, conditions="Người sử dụng lao động không phải là cá nhân chấm dứt hoạt động hoặc bị cơ quan chuyên môn về đăng ký kinh doanh thuộc Ủy ban nhân dân cấp tỉnh ra thông báo không có người đại diện theo pháp luật, người được ủy quyền thực hiện quyền và nghĩa vụ của người đại diện theo pháp luật")], G, "thấp")
d(72, [n(U, None, conditions="Người lao động bị xử lý kỷ luật sa thải")], G, "thấp")
d(73, [n(U, None, actor="Người lao động", action="đơn phương chấm dứt", object="hợp đồng lao động", conditions="theo quy định tại Điều 35 của Bộ luật này")], G, "thấp")
d(74, [n(U, None, actor="Người sử dụng lao động", action="đơn phương chấm dứt", object="hợp đồng lao động", conditions="theo quy định tại Điều 36 của Bộ luật này")], G, "thấp")
d(75, [n(U, None, actor="Người sử dụng lao động", action="cho người lao động thôi việc", conditions="theo quy định tại Điều 42 và Điều 43 của Bộ luật này")], G, "thấp")
d(76, [n(U, None, conditions="Giấy phép lao động hết hiệu lực đối với người lao động là người nước ngoài làm việc tại Việt Nam theo quy định tại Điều 156 của Bộ luật này")], G, "thấp")
d(77, [n(U, None, conditions="Trường hợp thỏa thuận nội dung thử việc ghi trong hợp đồng lao động mà thử việc không đạt yêu cầu hoặc một bên hủy bỏ thỏa thuận thử việc")], G, "thấp")

# BLLD Dieu 36 (78-91): lead-in "NSDLD co quyen don phuong cham dut HDLD trong truong hop sau day"
R = "Một trường hợp người sử dụng lao động có quyền đơn phương chấm dứt hợp đồng; tính quy phạm lấy theo câu dẫn, chủ thể và hành vi nằm ở câu dẫn."
d(78, [n(E, None, conditions="Người lao động thường xuyên không hoàn thành công việc theo hợp đồng lao động được xác định theo tiêu chí đánh giá mức độ hoàn thành công việc trong quy chế của người sử dụng lao động")], R, "vừa")
d(79, [n(O, "phải", actor="người sử dụng lao động", action="tham khảo ý kiến", object="Quy chế đánh giá mức độ hoàn thành công việc", recipient="tổ chức đại diện người lao động tại cơ sở", conditions="đối với nơi có tổ chức đại diện người lao động tại cơ sở")],
  "Quy chế đánh giá do người sử dụng lao động ban hành nhưng phải tham khảo ý kiến tổ chức đại diện người lao động tại cơ sở (nơi có tổ chức này).", "vừa")
d(80, [n(E, None, conditions="Người lao động bị ốm đau, tai nạn đã điều trị 12 tháng liên tục đối với người làm việc theo hợp đồng lao động không xác định thời hạn hoặc đã điều trị 06 tháng liên tục đối với người làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng hoặc quá nửa thời hạn hợp đồng lao động đối với người làm việc theo hợp đồng lao động xác định thời hạn có thời hạn dưới 12 tháng mà khả năng lao động chưa hồi phục")], R, "vừa")
d(81, [n(E, None, actor="người sử dụng lao động", action="xem xét để tiếp tục giao kết hợp đồng lao động", recipient="người lao động", conditions="Khi sức khỏe của người lao động bình phục")],
  "Sức khỏe người lao động bình phục thì người sử dụng lao động xem xét giao kết tiếp; theo hướng dẫn lấy tính quy phạm theo câu dẫn (Quyền) nhưng nghĩa thực tế gần với nghĩa vụ xem xét.", "thấp")
d(82, [n(E, None, conditions="Do thiên tai, hỏa hoạn, dịch bệnh nguy hiểm, địch họa hoặc di dời, thu hẹp sản xuất, kinh doanh theo yêu cầu của cơ quan nhà nước có thẩm quyền mà người sử dụng lao động đã tìm mọi biện pháp khắc phục nhưng vẫn buộc phải giảm chỗ làm việc")], R, "vừa")
d(83, [n(E, None, conditions="Người lao động không có mặt tại nơi làm việc sau thời hạn quy định tại Điều 31 của Bộ luật này")], R, "vừa")
d(84, [n(E, None, conditions="Người lao động đủ tuổi nghỉ hưu theo quy định tại Điều 169 của Bộ luật này", exceptions="trừ trường hợp có thỏa thuận khác")], R, "cao")
d(85, [n(E, None, conditions="Người lao động tự ý bỏ việc mà không có lý do chính đáng", quantities="từ 05 ngày làm việc liên tục trở lên")], R, "vừa")
d(86, [n(E, None, conditions="Người lao động cung cấp không trung thực thông tin theo quy định tại khoản 2 Điều 16 của Bộ luật này khi giao kết hợp đồng lao động làm ảnh hưởng đến việc tuyển dụng người lao động")], R, "vừa")
B = "Thời hạn người sử dụng lao động phải báo trước (nghĩa vụ theo câu dẫn), kèm loại hợp đồng áp dụng."
d(87, [n(O, None, deadlines="Ít nhất 45 ngày", conditions="đối với hợp đồng lao động không xác định thời hạn")], B, "cao")
d(88, [n(O, None, deadlines="Ít nhất 30 ngày", conditions="đối với hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng")], B, "cao")
d(89, [n(O, None, deadlines="Ít nhất 03 ngày làm việc", conditions="đối với hợp đồng lao động xác định thời hạn có thời hạn dưới 12 tháng và đối với trường hợp quy định tại điểm b khoản 1 Điều này")], B, "cao")
d(90, [n(O, None, object="thời hạn báo trước", action="thực hiện theo quy định của Chính phủ", conditions="Đối với một số ngành, nghề, công việc đặc thù")],
  "Ngành, nghề đặc thù thì thời hạn báo trước theo quy định của Chính phủ; tính quy phạm lấy theo câu dẫn (phải báo trước).", "vừa")
d(91, [n(U, None, actor="người sử dụng lao động", action="không phải báo trước", recipient="người lao động", conditions="Khi đơn phương chấm dứt hợp đồng lao động quy định tại điểm d và điểm e khoản 1 Điều này")],
  "Miễn nghĩa vụ báo trước trong hai trường hợp; 'không phải' không nằm trong bộ từ tình thái nên để chưa rõ loại.", "thấp")

# BLLD Dieu 111, 114, 117, 123
d(92, [n(E, "được", actor="người lao động", action="nghỉ", quantities="ít nhất 24 giờ liên tục", conditions="Mỗi tuần")],
  "Mỗi tuần người lao động được nghỉ ít nhất 24 giờ liên tục (quyền nhận ngày nghỉ).", "cao")
d(93, [n(O, "có trách nhiệm", actor="người sử dụng lao động", action="bảo đảm", object="cho người lao động được nghỉ", quantities="ít nhất 04 ngày", deadlines="tính bình quân 01 tháng", conditions="Trong trường hợp đặc biệt do chu kỳ lao động không thể nghỉ hằng tuần")],
  "Trường hợp đặc biệt, người sử dụng lao động có trách nhiệm bảo đảm nghỉ bình quân ít nhất 04 ngày mỗi tháng.", "cao")
d(94, [n(E, "có quyền", actor="Người sử dụng lao động", action="quyết định sắp xếp", object="ngày nghỉ hằng tuần", deadlines="vào ngày Chủ nhật hoặc ngày xác định khác trong tuần"),
       n(O, "phải", actor="Người sử dụng lao động", action="ghi vào nội quy lao động", object="ngày nghỉ hằng tuần")],
  "Có quyền sắp xếp ngày nghỉ hằng tuần nhưng phải ghi vào nội quy lao động; tách thành quyền và nghĩa vụ.", "vừa")
d(95, [n(E, "được", actor="người lao động", action="nghỉ bù", object="ngày nghỉ hằng tuần", deadlines="vào ngày làm việc kế tiếp", conditions="Nếu ngày nghỉ hằng tuần trùng với ngày nghỉ lễ, tết quy định tại khoản 1 Điều 112 của Bộ luật này")],
  "Ngày nghỉ hằng tuần trùng ngày lễ, tết thì người lao động được nghỉ bù vào ngày làm việc kế tiếp.", "cao")
d(96, [n(E, "được", actor="người lao động", object="số ngày nghỉ hằng năm của người lao động", action="tăng thêm", quantities="tương ứng 01 ngày", conditions="Cứ đủ 05 năm làm việc cho một người sử dụng lao động")],
  "Đủ 05 năm làm việc thì số ngày nghỉ hằng năm được tăng thêm 01 ngày (lợi ích nhận được).", "vừa")
d(97, [], "Định nghĩa kỷ luật lao động.", "cao")
d(98, [n(U, None, object="Thời hiệu xử lý kỷ luật lao động", deadlines="06 tháng kể từ ngày xảy ra hành vi vi phạm", action="là"),
       n(U, None, object="thời hiệu xử lý kỷ luật lao động", deadlines="12 tháng", conditions="trường hợp hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh của người sử dụng lao động", action="là")],
  "Thời hiệu xử lý kỷ luật là 06 tháng, hoặc 12 tháng với vi phạm liên quan tài chính, tài sản, bí mật; có thể coi là định nghĩa nên để thấp.", "thấp")
d(99, [n(M, "được", action="kéo dài", object="thời hiệu để xử lý kỷ luật lao động", deadlines="không quá 60 ngày kể từ ngày hết thời gian nêu trên", conditions="Khi hết thời gian quy định tại khoản 4 Điều 122 của Bộ luật này, nếu hết thời hiệu hoặc còn thời hiệu nhưng không đủ 60 ngày")],
  "Được kéo dài thời hiệu không quá 60 ngày khi hết thời gian quy định hoặc còn thời hiệu dưới 60 ngày; xếp Được phép (có thể xếp Quyền).", "vừa")
d(100, [n(O, "phải", actor="Người sử dụng lao động", action="ban hành", object="quyết định xử lý kỷ luật lao động", deadlines="trong thời hạn quy định tại khoản 1 và khoản 2 Điều này")],
  "Người sử dụng lao động phải ban hành quyết định xử lý kỷ luật trong thời hạn đã quy định.", "cao")
