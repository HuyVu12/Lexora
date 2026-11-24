"""Drafted labels for the blinded rejection audit (rejection-audit-v1, 104 claims, app set a18ba17ef7635).

Drafted 24/11/2026 by the in-session Claude agent from the claim and its source text only (sheet columns context,
unit_text, sentence, norm, which equal the items of the app set). The key (model, validator decision) was NOT read.
Labels: sai, dien_dat, dung_ngu_canh, dung, khong_ro (docs/guides/huong-dan-kiem-tra-quy-pham.md; first matching label wins).
Key: app item_id -> (label, confidence, reason, highlight phrases). Highlights are matched in every field that holds them.
"""

HD = "Hợp đồng lao động phải có những nội dung chủ yếu sau đây"
HD_REASON = ("Câu dẫn \"Hợp đồng lao động phải có những nội dung chủ yếu sau đây:\" cho nghĩa vụ \"phải\" và hành vi \"có\"; "
             "đối tượng là nguyên văn điểm. Nghĩa đúng, chữ \"phải\", \"có\" lấy từ câu dẫn.")
SATHAI = ("Hành vi \"áp dụng hình thức xử lý kỷ luật sa thải\" là tên Điều 125, chủ thể \"người sử dụng lao động\" lấy từ câu dẫn; "
          "điều kiện là nguyên văn khoản. Nghĩa đúng.")
NGHILE = ("Câu dẫn \"Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây:\" cho quyền, chủ thể, hành vi; "
          "đối tượng và số ngày là nguyên văn điểm. Nghĩa đúng.")
LUONG_DEM = ("Từ \"được\" ở đây là \"được tính\" (bị động), không phải từ tình thái; coi là nghĩa vụ tính tối thiểu thì vẫn chấp nhận được. "
             "Các ô là nguyên văn câu.")
THIEU_CHU_NGU = ("Các ô là nguyên văn, nhưng quy phạm không nói cái gì được tính (ô Đối tượng chỉ là mức \"ít nhất bằng ...%\"). "
                 "Không sai, chỉ mơ hồ; nếu cho rằng thiếu đối tượng làm sai nghĩa thì chọn Sai.")
TAM_HOAN_UQ = ("Câu là một trường hợp tạm hoãn hợp đồng: \"Người lao động được ủy quyền ...\" (\"được\" là bị động). "
               "Quy phạm ghi \"được phép\" và hành vi \"ủy quyền\" của người lao động, tức người lao động được phép ủy quyền: luật không nói vậy.")
HIEU_LUC = ("Câu tuyên bố một Nghị định hết hiệu lực, không đặt nghĩa vụ cho ai; quy phạm ghi tính quy phạm \"nghĩa vụ\" với chủ thể là một Nghị định. "
            "Sai tính quy phạm.")
THAM_VAN = "Câu dẫn \"Phạt tiền từ 5.000.000 đồng đến 10.000.000 đồng đối với người sử dụng lao động có một trong các hành vi sau đây:\""

A = {
    "R9606202419": ("dung", "thấp",
                    "Mọi ô là nguyên văn câu: \"người sử dụng lao động vẫn tiến hành họp xử lý kỷ luật lao động\" khi có thành phần vắng mặt. "
                    "Tính quy phạm \"nghĩa vụ\" không có từ tình thái; câu có thể hiểu là người sử dụng lao động vẫn được họp (quyền) chứ không bắt buộc. Nếu hiểu vậy thì chọn Sai.",
                    ["vẫn tiến hành họp xử lý kỷ luật lao động", "Tính quy phạm: nghĩa vụ"]),
    "R49a555b0a8": ("dung", "vừa",
                    "Chủ thể, hành vi, đối tượng là nguyên văn câu (\"người sử dụng lao động vẫn tiến hành họp xử lý bồi thường thiệt hại\"); tính quy phạm \"chưa rõ\" không sai. "
                    "Quy phạm bỏ điều kiện vắng mặt nhưng điểm c cũng nói người sử dụng lao động tiến hành họp, nên không thành sai nghĩa.",
                    ["tiến hành họp xử lý bồi thường thiệt hại"]),
    "R767a75370d": ("dung", "vừa",
                    LUONG_DEM + " Quy phạm lấy đúng nhánh 100% với điều kiện \"không làm thêm giờ vào ban ngày của ngày đó\".",
                    ["được tính", "ít nhất bằng 100%", "không làm thêm giờ vào ban ngày của ngày đó"]),
    "R85efaf6cfc": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "R7eaf3e9081": ("dung_ngu_canh", "cao", SATHAI, ["Áp dụng hình thức xử lý kỷ luật sa thải", "áp dụng hình thức xử lý kỷ luật sa thải"]),
    "R4efe7aac7a": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "R435070813b": ("dung", "vừa", LUONG_DEM, ["được tính ít nhất 300%", "Hành vi: tính"]),
    "Rab0c30c08d": ("dung_ngu_canh", "cao",
                    "Chủ thể, hành vi \"được sự đồng ý\", bên nhận, điều kiện và ngoại lệ đều lấy nguyên văn từ câu dẫn khoản 1; đối tượng là nguyên văn điểm c. Nghĩa đúng.",
                    ["phải được sự đồng ý của người lao động tham gia làm thêm", "Trừ các trường hợp quy định tại Điều 108 của Bộ luật Lao động"]),
    "R68e62ec239": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Người sử dụng lao động được sử dụng người lao động làm thêm không quá 300 giờ trong 01 năm ...\" cho chủ thể, hành vi, định lượng; điều kiện là nguyên văn điểm a. Nghĩa đúng.",
                    ["được sử dụng người lao động làm thêm không quá 300 giờ trong 01 năm"]),
    "Rfa363b1fd2": ("dien_dat", "thấp",
                    "Câu chỉ định nghĩa: tiền lương giờ thực trả \"được xác định theo điểm a khoản 1 Điều 55 Nghị định này\". "
                    "Quy phạm viết lại thành hành vi \"xác định tiền lương giờ thực trả\" (không nguyên văn), bỏ mất phần \"theo điểm a khoản 1 Điều 55\" và lấy \"Trong đó\" làm điều kiện. "
                    "Không mâu thuẫn với luật nhưng gần như rỗng; nếu cho rằng mất dẫn chiếu làm sai nghĩa thì chọn Sai.",
                    ["được xác định theo điểm a khoản 1 Điều 55 Nghị định này", "Hành vi: xác định tiền lương giờ thực trả", "Điều kiện: Trong đó"]),
    "R85b7e9ee25": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "R54b51a00df": ("dung", "vừa",
                    "Điều kiện và kết quả là nguyên văn câu (\"thì thời điểm chấm dứt hợp đồng lao động tính từ ngày ra thông báo\"); hành vi \"ra thông báo\" cũng có trong câu. "
                    "\"thì\" không phải từ tình thái nhưng tính quy phạm \"chưa rõ\" không khẳng định sai điều gì.",
                    ["thời điểm chấm dứt hợp đồng lao động tính từ ngày ra thông báo", "chưa rõ (từ: \"thì\")"]),
    "Rb36ec84382": ("dung", "vừa",
                    "\"Người sử dụng lao động có quyền quy định thời giờ làm việc theo ngày hoặc tuần\": quyền, chủ thể, hành vi, đối tượng đều nguyên văn. "
                    "Phần \"nhưng phải thông báo cho người lao động biết\" là một nghĩa vụ đi kèm, bỏ đi không làm quyền này sai.",
                    ["có quyền quy định thời giờ làm việc theo ngày hoặc tuần", "nhưng phải thông báo cho người lao động biết"]),
    "R62a610d7f1": ("dien_dat", "vừa",
                    "Câu viết \"phải được lập thành biên bản, thông qua trước khi kết thúc cuộc họp\"; hành vi \"được thông qua\" ghép chữ không liền nhau, không còn nguyên văn. Nghĩa vẫn đúng (nội dung cuộc họp phải được thông qua).",
                    ["phải được lập thành biên bản, thông qua trước khi kết thúc cuộc họp", "Hành vi: được thông qua"]),
    "R4cfd08a228": ("dung", "thấp", THIEU_CHU_NGU, ["Đối tượng: ít nhất 300%", "Đơn giá tiền lương sản phẩm vào ban ngày của ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương"]),
    "R7918a0db38": ("sai", "cao",
                    "Câu nói tiền lương \"do hai bên thỏa thuận nhưng không thấp hơn mức lương tối thiểu vùng ...\". "
                    "Quy phạm ghi \"cấm\" với hành vi \"thỏa thuận\", tức cấm hai bên thỏa thuận: ngược với câu, và bỏ mất giới hạn \"không thấp hơn\".",
                    ["do hai bên thỏa thuận nhưng không thấp hơn mức lương tối thiểu vùng", "Tính quy phạm: cấm (từ: \"không\")", "Hành vi: thỏa thuận"]),
    "Rb8f1eddc7d": ("dien_dat", "cao",
                    "Nghĩa đúng: tiền lương thử việc \"ít nhất phải bằng 85% mức lương của công việc đó\". Định lượng \"ít nhất 85%\" ghép chữ không liền nhau, không còn nguyên văn.",
                    ["ít nhất phải bằng 85% mức lương của công việc đó", "Định lượng: ít nhất 85%"]),
    "R8d3d01ade0": ("sai", "vừa",
                    "Câu chỉ định nghĩa \"Tái phạm là trường hợp ...\". Khoản 3 chỉ cho sa thải người đã bị xử lý \"kéo dài thời hạn nâng lương hoặc cách chức mà tái phạm\". "
                    "Quy phạm lấy riêng câu định nghĩa làm điều kiện sa thải, nên mất điều kiện giới hạn: thành tái phạm bất kỳ cũng bị sa thải.",
                    ["Tái phạm là trường hợp người lao động lặp lại hành vi vi phạm đã bị xử lý kỷ luật", "kéo dài thời hạn nâng lương hoặc cách chức mà tái phạm"]),
    "Re37fa0037e": ("dung", "cao",
                    "Mọi ô là nguyên văn câu, giữ cả ngoại lệ \"trừ trường hợp hai bên có thỏa thuận hoặc pháp luật có quy định khác\". "
                    "Hướng dẫn (ví dụ 3) coi câu này là Điều cấm.",
                    ["không được hưởng lương và quyền, lợi ích đã giao kết trong hợp đồng lao động", "trừ trường hợp hai bên có thỏa thuận hoặc pháp luật có quy định khác"]),
    "R80bd5b224c": ("dung_ngu_canh", "cao",
                    "Như các điểm khác của khoản 1 Điều 59: chủ thể, hành vi, bên nhận, điều kiện, ngoại lệ lấy từ câu dẫn; đối tượng \"Thời gian làm thêm\" là nguyên văn điểm a. Nghĩa đúng.",
                    ["phải được sự đồng ý của người lao động tham gia làm thêm"]),
    "Re5556714cc": ("sai", "vừa", HIEU_LUC, ["hết hiệu lực thi hành", "Tính quy phạm: nghĩa vụ"]),
    "R4edeefaa28": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "R490c8fc442": ("dien_dat", "thấp",
                    "Điều kiện viết \"trong trường hợp ...\" trong khi câu viết \"đối với trường hợp ...\", nên không còn nguyên văn. "
                    "Quy phạm cũng không nói cái gì được tính (đối tượng chỉ là mức \"ít nhất bằng 100% ...\"); nếu coi thiếu đối tượng là sai nghĩa thì chọn Sai.",
                    ["đối với trường hợp người lao động không làm thêm giờ", "Điều kiện: trong trường hợp", "Đối tượng: ít nhất bằng 100%"]),
    "R4dbf1c4d33": ("dung", "vừa", LUONG_DEM, ["được tính ít nhất 300%", "Hành vi: được tính"]),
    "R52fb44159f": ("sai", "vừa",
                    "Câu: người lao động \"được người sử dụng lao động thanh toán tiền lương cho những ngày chưa nghỉ\". Quyền là của người lao động. "
                    "Quy phạm ghi \"quyền\" với chủ thể \"người sử dụng lao động\", tức người sử dụng lao động có quyền thanh toán: sai chủ thể của quyền (với họ đây là nghĩa vụ); điều kiện thôi việc, mất việc cũng bị bỏ.",
                    ["thì được người sử dụng lao động thanh toán tiền lương cho những ngày chưa nghỉ", "Tính quy phạm: quyền", "Chủ thể: người sử dụng lao động"]),
    "R5284dd47c5": ("dien_dat", "cao",
                    "Nghĩa đúng. Chủ thể viết \"các thành phần tham dự họp quy định tại ...\" trong khi câu viết \"các thành phần phải tham dự họp quy định tại ...\" (bỏ chữ \"phải\"), nên không còn nguyên văn.",
                    ["các thành phần phải tham dự họp quy định tại điểm b, điểm c khoản 1 Điều 122", "Chủ thể: các thành phần tham dự họp"]),
    "R153ed78059": ("dung_ngu_canh", "cao",
                    "Đúng như ví dụ 1 của hướng dẫn: quyền, chủ thể, hành vi, đối tượng và \"không cần báo trước\" lấy từ câu dẫn khoản 2; điều kiện và ngoại lệ là nguyên văn điểm b.",
                    ["Người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước", "trừ trường hợp quy định tại khoản 4 Điều 97 của Bộ luật này"]),
    "Rafd5b2a29d": ("dung_ngu_canh", "cao", SATHAI, ["kéo dài thời hạn nâng lương hoặc cách chức mà tái phạm trong thời gian chưa xóa kỷ luật"]),
    "R5f8df93dd9": ("dung_ngu_canh", "cao",
                    "Chủ thể và kết quả \"Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng\" lấy từ câu dẫn khoản 2; hành vi, điều kiện, định lượng là nguyên văn điểm a. Cấm yêu cầu thử việc quá 01 lần: nghĩa đúng.",
                    ["Phạt tiền từ 2.000.000 đồng đến 5.000.000 đồng", "Yêu cầu người lao động thử việc quá 01 lần đối với một công việc"]),
    "R3cca63b47d": ("dung", "cao", "\"Chính phủ quy định chi tiết Điều này\": chủ thể và hành vi nguyên văn, tính quy phạm \"chưa rõ\" không sai.", ["Chính phủ quy định chi tiết Điều này"]),
    "Rdd2e6d5490": ("sai", "cao",
                    "Câu liệt kê các trường hợp \"được coi là có lý do chính đáng\", tức những trường hợp KHÔNG bị sa thải theo khoản 4. "
                    "Quy phạm lấy chính câu này làm điều kiện để áp dụng sa thải: ngược nghĩa.",
                    ["Trường hợp được coi là có lý do chính đáng", "mà không có lý do chính đáng", "Hành vi: áp dụng hình thức xử lý kỷ luật sa thải"]),
    "R3235cbdb1d": ("dung_ngu_canh", "vừa",
                    "Nghĩa đúng: người lao động \"được giữ nguyên tiền lương của công việc cũ trong thời hạn 30 ngày làm việc\". "
                    "Chữ \"người lao động\" không có trong câu này mà lấy từ câu trước của cùng khoản (\"Người lao động chuyển sang làm công việc khác ...\").",
                    ["được giữ nguyên tiền lương của công việc cũ trong thời hạn 30 ngày làm việc", "Người lao động chuyển sang làm công việc khác"]),
    "R0d73ed4bb3": ("dung_ngu_canh", "cao", NGHILE, ["Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây"]),
    "Rb57fa267a9": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "R9f3b937bc6": ("dien_dat", "cao",
                    "Nghĩa đúng (cấm yêu cầu người lao động thử việc quá 01 lần đối với một công việc). Hành vi \"Yêu cầu thử việc\" và đối tượng \"người lao động quá 01 lần ...\" bị tách, ghép lại từ \"Yêu cầu người lao động thử việc quá 01 lần\", không còn nguyên văn.",
                    ["Yêu cầu người lao động thử việc quá 01 lần đối với một công việc", "Hành vi: Yêu cầu thử việc", "Đối tượng: người lao động quá 01 lần"]),
    "R0341cfb653": ("dung", "cao", "\"Chính phủ quy định trình tự, thủ tục xử lý kỷ luật lao động\": các ô nguyên văn, tính quy phạm \"chưa rõ\" không sai.", ["Chính phủ quy định trình tự, thủ tục xử lý kỷ luật lao động"]),
    "Rf384514175": ("sai", "vừa",
                    "Câu là một trường hợp tạm hoãn hợp đồng: \"Người lao động được bổ nhiệm làm người quản lý doanh nghiệp ...\" (\"được\" là bị động). "
                    "Quy phạm ghi \"được phép\" và hành vi \"bổ nhiệm làm\" của người lao động: luật không cho phép gì ở đây. Ô Kết quả \"tạm hoãn\" đúng nhưng tính quy phạm sai.",
                    ["Người lao động được bổ nhiệm làm người quản lý doanh nghiệp", "Tính quy phạm: được phép", "Các trường hợp tạm hoãn thực hiện hợp đồng lao động bao gồm"]),
    "R0157003c8a": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "Rdcd23705cd": ("dung", "thấp",
                    "Các ô là nguyên văn câu \"Buộc người sử dụng lao động trả đủ tiền lương cộng với khoản tiền lãi ...\"; nghĩa vụ đúng. "
                    "Quy phạm bỏ phần \"đối với hành vi vi phạm quy định tại khoản 2, khoản 3 Điều này\" (giới hạn khi nào áp dụng); nếu coi đó là bỏ điều kiện giới hạn phạm vi thì chọn Sai.",
                    ["Buộc người sử dụng lao động trả đủ tiền lương", "đối với hành vi vi phạm quy định tại khoản 2, khoản 3 Điều này"]),
    "Rfc356c1ac6": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "R024df825db": ("dien_dat", "vừa",
                    "Quyền, chủ thể, hành vi, đối tượng đúng như câu \"Người lao động có quyền được biết lý do khấu trừ tiền lương của mình\". "
                    "Nhưng từ tình thái ghi là \"có権\" (ký tự lạ), không có trong câu. Tính quy phạm vẫn đúng nên không phải Sai; ghi chú ký tự lạ.",
                    ["có quyền được biết lý do khấu trừ tiền lương của mình", "có権"]),
    "R73aff9f2fb": ("dien_dat", "thấp",
                    "Câu: tiền lương công việc mới \"ít nhất phải bằng 85% ... nhưng không thấp hơn mức lương tối thiểu\". Hành vi \"bằng 85% ...\" bỏ chữ \"ít nhất\" (như ví dụ 4 của hướng dẫn) và bỏ \"không thấp hơn mức lương tối thiểu\"; "
                    "\"người lao động\" lấy từ câu khác. Nếu cho rằng bỏ \"ít nhất\" làm mất ý mức sàn thì chọn Sai.",
                    ["ít nhất phải bằng 85% tiền lương của công việc cũ", "Hành vi: bằng 85%"]),
    "Rea24e268be": ("dung", "cao", "\"người lao động phải hoàn trả số tiền đã tạm ứng\": nghĩa vụ, chủ thể, hành vi nguyên văn và đúng.", ["người lao động phải hoàn trả số tiền đã tạm ứng"]),
    "R9f53f93d23": ("dien_dat", "thấp",
                    "Điều kiện viết \"trong trường hợp ...\" trong khi câu viết \"đối với trường hợp ...\", nên không còn nguyên văn. "
                    "Quy phạm không nói cái gì được tính (đối tượng chỉ là mức \"ít nhất bằng 150% ...\"); nếu coi thiếu đối tượng là sai nghĩa thì chọn Sai.",
                    ["đối với trường hợp người lao động có làm thêm giờ", "Điều kiện: trong trường hợp", "Đối tượng: ít nhất bằng 150%"]),
    "Rea3104a0e3": ("dung", "thấp",
                    "Chủ thể và hành vi \"ghi rõ tiền lương, ...\" là nguyên văn; bảng kê do người sử dụng lao động lập nên nghĩa không sai. "
                    "Nhưng quy phạm bỏ nghĩa vụ chính \"phải thông báo bảng kê trả lương\" và lấy \"trong đó\" làm điều kiện; nếu coi vậy là sai nghĩa thì chọn Sai.",
                    ["phải thông báo bảng kê trả lương cho người lao động", "Điều kiện: trong đó"]),
    "Rd36beb8092": ("dien_dat", "vừa",
                    "Nghĩa đúng: người chưa đủ 15 tuổi \"thì phải có sự tham gia của người đại diện theo pháp luật\". Hành vi viết \"thì có sự tham gia ...\" (bỏ \"phải\", giữ \"thì\"), không còn nguyên văn.",
                    ["thì phải có sự tham gia của người đại diện theo pháp luật", "Hành vi: thì có sự tham gia"]),
    "R0ac942e1a9": ("dung", "vừa",
                    "Chủ thể, hành vi, đối tượng và hai điều kiện (\"Trường hợp thử việc đạt yêu cầu\", \"đối với trường hợp thỏa thuận thử việc trong hợp đồng lao động\") đều là nguyên văn câu; nghĩa đúng.",
                    ["người sử dụng lao động tiếp tục thực hiện hợp đồng lao động đã giao kết đối với trường hợp thỏa thuận thử việc trong hợp đồng lao động"]),
    "Re3aa8c95d3": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Phương án sử dụng lao động phải có những nội dung chủ yếu sau đây:\" cho \"phải\" và \"có\"; đối tượng là nguyên văn điểm d. Nghĩa đúng.",
                    ["Phương án sử dụng lao động phải có những nội dung chủ yếu sau đây"]),
    "Ra92fded30e": ("dung_ngu_canh", "cao", SATHAI, ["mà không có lý do chính đáng"]),
    "Ra549472d6f": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "Rf019405119": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "Rb7ff4b0d7c": ("dung", "cao",
                    "\"Người sử dụng lao động phải cho người lao động tạm ứng tiền lương ...\": mọi ô là nguyên văn câu, gồm cả điều kiện \"từ 01 tuần trở lên\" và mức \"tối đa không quá 01 tháng tiền lương\". Nghĩa đúng.",
                    ["phải cho người lao động tạm ứng tiền lương", "tối đa không quá 01 tháng tiền lương theo hợp đồng lao động"]),
    "Rf0c9c4d5eb": ("dung", "cao",
                    "Mọi ô là nguyên văn câu: \"người sử dụng lao động phải trả trợ cấp thôi việc theo quy định tại Điều 46 ...\" khi người lao động không muốn tiếp tục làm việc. Nghĩa đúng.",
                    ["người sử dụng lao động phải trả trợ cấp thôi việc theo quy định tại Điều 46 của Bộ luật này"]),
    "R2503fc9466": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "R35f7edb547": ("dung", "thấp",
                    "Hành vi và đối tượng là nguyên văn câu \"Phạt tiền, cắt lương thay việc xử lý kỷ luật lao động\". "
                    "Nhưng tên Điều 127 là \"Các hành vi bị nghiêm cấm ...\" mà quy phạm chỉ ghi tính quy phạm \"chưa rõ\", không nói là bị cấm. Nếu coi mất ý cấm là sai nghĩa thì chọn Sai.",
                    ["Các hành vi bị nghiêm cấm khi xử lý kỷ luật lao động", "Tính quy phạm: chưa rõ"]),
    "R7e22ad155c": ("dien_dat", "cao",
                    "Nghĩa đúng (quyền khiếu nại nếu thấy không thỏa đáng). Câu viết \"khiếu nại với người sử dụng lao động, với cơ quan có thẩm quyền ...\"; hành vi \"khiếu nại với cơ quan có thẩm quyền ...\" bỏ phần giữa nên không còn nguyên văn.",
                    ["có quyền khiếu nại với người sử dụng lao động, với cơ quan có thẩm quyền theo quy định của pháp luật", "Hành vi: khiếu nại với cơ quan có thẩm quyền"]),
    "Rb15d3f93e1": ("sai", "thấp",
                    "Câu: thời giờ của khoản 1 Điều 58 \"được giảm trừ khi tính tổng số giờ làm thêm\": đây là cách tính bắt buộc (\"được\" bị động), không phải điều được phép tùy chọn. "
                    "Quy phạm ghi \"được phép\". Nếu hiểu \"được giảm trừ\" là cho phép thì chọn Đúng, nguyên văn.",
                    ["được giảm trừ khi tính tổng số giờ làm thêm", "Tính quy phạm: được phép"]),
    "R3c3cbd3765": ("dung_ngu_canh", "cao", HD_REASON, [HD, "Chủ thể: Hợp đồng lao động"]),
    "R1f4f88c554": ("sai", "cao", TAM_HOAN_UQ + " Hành vi còn viết \"uy quyền\" thay cho \"ủy quyền\".",
                    ["Người lao động được ủy quyền", "Tính quy phạm: được phép", "Hành vi: uy quyền"]),
    "Rc0bf07b62f": ("dung", "vừa",
                    "Mọi ô là nguyên văn câu: người có thẩm quyền \"ban hành quyết định xử lý kỷ luật lao động và gửi đến các thành phần phải tham dự ...\" trong thời hiệu. "
                    "Tính quy phạm \"nghĩa vụ\" không có từ tình thái nhưng hợp với câu thủ tục.",
                    ["ban hành quyết định xử lý kỷ luật lao động và gửi đến các thành phần phải tham dự"]),
    "Rf63070aea3": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "Re744154e89": ("dung", "vừa",
                    "Nghĩa đúng: mức \"ít nhất bằng 200% ... áp dụng đối với sản phẩm làm thêm vào ngày nghỉ hằng tuần\". "
                    "Hành vi \"Mức ít nhất bằng 200%\" chỉ khác câu ở chữ hoa đầu (câu viết \"mức\"); coi như nguyên văn. Nếu tính cả chữ hoa thì chọn Đúng, diễn đạt lại.",
                    ["mức ít nhất bằng 200% so với đơn giá tiền lương sản phẩm của ngày làm việc bình thường, áp dụng đối với sản phẩm làm thêm vào ngày nghỉ hằng tuần", "Hành vi: Mức ít nhất bằng 200%"]),
    "R9fce0a0763": ("dung", "thấp", THIEU_CHU_NGU, ["Đối tượng: ít nhất bằng 200%", "Đơn giá tiền lương sản phẩm vào ban ngày của ngày nghỉ hằng tuần"]),
    "R5926b86319": ("dung", "vừa",
                    "\"Người lao động bị thôi việc thì được nhận trợ cấp mất việc làm theo quy định tại Điều 47\": quyền, chủ thể, hành vi, điều kiện đều nguyên văn và đúng.",
                    ["được nhận trợ cấp mất việc làm theo quy định tại Điều 47 của Bộ luật này"]),
    "Rf26da11fbf": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Người lao động làm thêm giờ được trả lương tính theo ...\" cho quyền, chủ thể, hành vi, đối tượng; điều kiện \"Vào ngày thường\" và mức \"ít nhất bằng 150%\" là nguyên văn điểm a. Nghĩa đúng.",
                    ["Người lao động làm thêm giờ được trả lương tính theo đơn giá tiền lương hoặc tiền lương thực trả theo công việc đang làm"]),
    "Reb16e0ddb8": ("dien_dat", "thấp",
                    "Ý là giới hạn thời giờ làm việc bình thường. Định lượng \"08 giờ trong 01 ngày và 48 giờ trong 01 tuần\" ghép lại, không nguyên văn; quy phạm không nêu cái gì bị giới hạn. "
                    "Hành vi đã chứa \"không quá\" nên ghép với \"cấm\" thành phủ định kép; nếu đọc theo nghĩa đen là cấm làm không quá 8 giờ thì chọn Sai.",
                    ["Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày", "Định lượng: 08 giờ trong 01 ngày và 48 giờ trong 01 tuần", "Tính quy phạm: cấm"]),
    "R8540692d7e": ("dien_dat", "vừa",
                    "Nghĩa đúng: người lao động được tạm ứng 50% tiền lương trong thời gian bị tạm đình chỉ. Điều kiện \"Trong thời gian bị tạm đình chỉ công việc trước khi bị đình chỉ công việc\" ghép hai đoạn không liền nhau, không còn nguyên văn.",
                    ["người lao động được tạm ứng 50% tiền lương trước khi bị đình chỉ công việc", "Điều kiện: Trong thời gian bị tạm đình chỉ công việc trước khi bị đình chỉ công việc"]),
    "R78ed1a3d39": ("dung_ngu_canh", "cao", SATHAI, ["Áp dụng hình thức xử lý kỷ luật sa thải"]),
    "R6e027ee504": ("dung_ngu_canh", "cao", NGHILE, ["Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây"]),
    "Rdadff296d8": ("dung", "cao",
                    "\"... bảo đảm cho người lao động được nghỉ tính bình quân 01 tháng ít nhất 04 ngày\": quyền nghỉ của người lao động, điều kiện và định lượng đều nguyên văn và đúng.",
                    ["người lao động được nghỉ tính bình quân 01 tháng ít nhất 04 ngày"]),
    "Rb7875614f7": ("dung", "cao",
                    "Mọi ô là nguyên văn câu: \"người sử dụng lao động phải trả lương ngừng việc theo quy định tại Điều 99\" trong trường hợp người lao động không đồng ý và phải ngừng việc. Nghĩa đúng.",
                    ["người sử dụng lao động phải trả lương ngừng việc theo quy định tại Điều 99 của Bộ luật này"]),
    "Rf02f93aa06": ("dung_ngu_canh", "thấp",
                    "Ý \"không thấp hơn mức lương tối thiểu\" là đúng và hành vi là nguyên văn; bên thụ hưởng \"người lao động\" lấy từ câu khác của khoản. "
                    "Quy phạm không nói cái gì không được thấp hơn (tiền lương theo công việc mới); nếu coi vậy là sai nghĩa thì chọn Sai.",
                    ["nhưng không thấp hơn mức lương tối thiểu", "Hành vi: thấp hơn mức lương tối thiểu"]),
    "Rd257b33c36": ("sai", "thấp",
                    "Hành vi và đối tượng đúng ý câu \"Tiền lương theo công việc mới ít nhất phải bằng 85% ...\". Nhưng chủ thể \"Người sử dụng lao động\" không có trong câu, đơn vị hay tên Điều; "
                    "hướng dẫn coi thêm chủ thể luật không nói là Sai. Chủ thể này hợp lý về ý (người trả lương), nên nếu chấp nhận thì chọn Đúng, diễn đạt lại.",
                    ["Chủ thể: Người sử dụng lao động", "ít nhất phải bằng 85% tiền lương của công việc cũ nhưng không thấp hơn mức lương tối thiểu"]),
    "Raaba7536cf": ("dung_ngu_canh", "vừa", HD_REASON + " \"Hợp đồng lao động\" được đặt ở ô Điều kiện thay vì Chủ thể, nhưng không đổi nghĩa.", [HD, "Điều kiện: Hợp đồng lao động"]),
    "R3a7da3f055": ("dung", "thấp", THIEU_CHU_NGU, ["Đối tượng: ít nhất bằng 100%", "Đơn giá tiền lương sản phẩm vào ban ngày của ngày làm việc bình thường"]),
    "R3409a466ff": ("dung", "thấp",
                    "Các ô là nguyên văn câu \"Người lao động phải chấp hành quyết định áp dụng biện pháp đưa vào trường giáo dưỡng ...\". "
                    "Nhưng câu này nằm trong danh sách các trường hợp tạm hoãn hợp đồng; quy phạm biến nó thành nghĩa vụ của người lao động và không nói đến tạm hoãn. Nếu coi vậy là luật không nói thì chọn Sai.",
                    ["Các trường hợp tạm hoãn thực hiện hợp đồng lao động bao gồm", "Người lao động phải chấp hành quyết định"]),
    "R7a0260bd8f": ("sai", "thấp",
                    "Câu nói người sử dụng lao động \"quy định cụ thể trong nội quy lao động những trường hợp do nhu cầu sản xuất, kinh doanh\" mà họ được tạm thời chuyển người lao động. "
                    "Quy phạm chỉ giữ \"được tạm thời chuyển\" \"trong những trường hợp do nhu cầu sản xuất, kinh doanh\", bỏ điều kiện phải quy định trong nội quy (và giới hạn 60 ngày ở câu trước). "
                    "Nếu cho rằng phần bỏ không đổi nghĩa thì chọn Đúng, diễn đạt lại (chữ \"trong\" được thêm vào điều kiện).",
                    ["quy định cụ thể trong nội quy lao động những trường hợp do nhu cầu sản xuất, kinh doanh", "Điều kiện: trong những trường hợp do nhu cầu sản xuất, kinh doanh"]),
    "R29bb980db7": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Người lao động được nghỉ việc riêng mà vẫn hưởng nguyên lương ...\" cho quyền, chủ thể, hành vi; điều kiện và \"03 ngày\" là nguyên văn điểm c. Nghĩa đúng.",
                    ["Người lao động được nghỉ việc riêng mà vẫn hưởng nguyên lương"]),
    "R7cb4004ddb": ("dung", "thấp", THIEU_CHU_NGU, ["Đối tượng: ít nhất bằng 150%", "Đơn giá tiền lương sản phẩm vào ban ngày của ngày làm việc bình thường"]),
    "Rdf8b48d5df": ("dung_ngu_canh", "cao", HD_REASON, [HD]),
    "Rb606b20a37": ("dien_dat", "thấp",
                    "Câu: trong thời gian chưa ký hợp đồng mới thì quyền, nghĩa vụ và lợi ích của hai bên \"được thực hiện theo hợp đồng đã giao kết\" (\"được\" bị động). "
                    "Quy phạm viết lại thành \"thực hiện quyền, nghĩa vụ và lợi ích\", bỏ mất \"theo hợp đồng đã giao kết\" và ghi \"được phép\". Nếu coi mất phần này hoặc tính quy phạm là sai nghĩa thì chọn Sai.",
                    ["được thực hiện theo hợp đồng đã giao kết", "Hành vi: thực hiện quyền, nghĩa vụ và lợi ích", "Tính quy phạm: được phép"]),
    "Rc1b73fa932": ("dung_ngu_canh", "cao", NGHILE, ["Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây"]),
    "Rcda5a9af44": ("dung", "thấp",
                    "Các ô là nguyên văn câu (\"không quá 12 giờ trong 01 ngày\", điều kiện làm việc theo tuần). Quy phạm không nêu cái gì bị giới hạn (tổng số giờ làm việc bình thường và làm thêm). "
                    "Hành vi đã chứa \"không quá\" nên ghép với \"cấm\" thành phủ định kép; nếu đọc theo nghĩa đen thì chọn Sai.",
                    ["tổng số giờ làm việc bình thường và số giờ làm thêm không quá 12 giờ trong 01 ngày", "Tính quy phạm: cấm"]),
    "R32987141ef": ("dung_ngu_canh", "vừa",
                    THAM_VAN + " cho chủ thể và kết quả. Câu phạt hành vi \"Không tham khảo ý kiến ...\", nên quy phạm nghĩa vụ \"tham khảo ý kiến\" là đúng nghĩa; các ô khác là nguyên văn điểm c.",
                    ["Phạt tiền từ 5.000.000 đồng đến 10.000.000 đồng", "Không tham khảo ý kiến", "Tính quy phạm: nghĩa vụ"]),
    "R78b016e6f0": ("dung_ngu_canh", "thấp",
                    "Câu dẫn \"... chỉ được thử việc một lần đối với một công việc và bảo đảm điều kiện sau đây:\" cho hành vi \"thử việc\"; thời hạn \"Không quá 06 ngày làm việc\" và điều kiện là nguyên văn khoản 4. "
                    "Nghĩa vụ ở đây là bảo đảm thời gian thử việc không quá 06 ngày. Nếu đọc là bắt buộc phải thử việc thì chọn Sai.",
                    ["bảo đảm điều kiện sau đây", "Không quá 06 ngày làm việc đối với công việc khác", "Hành vi: thử việc"]),
    "R6e65d62e03": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"3. Người sử dụng lao động có trách nhiệm sau đây:\" cho nghĩa vụ và chủ thể; hành vi \"trả lại\", đối tượng và điều kiện là nguyên văn điểm a. Nghĩa đúng.",
                    ["Người sử dụng lao động có trách nhiệm sau đây", "nếu người sử dụng lao động đã giữ của người lao động"]),
    "Rbf0e761f7c": ("dung", "cao",
                    "\"người sử dụng lao động phải báo cho người lao động biết trước ít nhất 03 ngày làm việc\": mọi ô là nguyên văn câu và đúng.",
                    ["người sử dụng lao động phải báo cho người lao động biết trước ít nhất 03 ngày làm việc"]),
    "R3ec6bcf241": ("sai", "vừa", TAM_HOAN_UQ + " Ô Kết quả \"tạm hoãn\" đúng nhưng tính quy phạm và hành vi sai.",
                    ["Người lao động được ủy quyền", "Tính quy phạm: được phép", "Hành vi: ủy quyền để thực hiện"]),
    "R9517cd6b2e": ("dung", "thấp", THIEU_CHU_NGU, ["Đối tượng: ít nhất bằng 300%", "Tiền lương giờ vào ban ngày của ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương"]),
    "R75e6015238": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Người lao động làm thêm giờ được trả lương tính theo ...\" cho quyền, chủ thể, hành vi, đối tượng; điều kiện và mức \"ít nhất bằng 300% chưa kể ...\" là nguyên văn điểm c. Nghĩa đúng.",
                    ["Người lao động làm thêm giờ được trả lương tính theo đơn giá tiền lương hoặc tiền lương thực trả theo công việc đang làm"]),
    "R981fc13ba3": ("sai", "cao", TAM_HOAN_UQ + " Hành vi còn viết \"uy quyền\" thay cho \"ủy quyền\".",
                    ["Người lao động được ủy quyền", "Tính quy phạm: được phép", "Hành vi: uy quyền"]),
    "R5f220d8214": ("dung", "vừa", "\"Chính phủ quy định chi tiết Điều này\": các ô nguyên văn; coi giao việc cho Chính phủ là nghĩa vụ thì hợp lý.", ["Chính phủ quy định chi tiết Điều này"]),
    "R3d6cefb8a9": ("dung", "vừa", LUONG_DEM, ["được tính ít nhất bằng 200%", "Hành vi: tính"]),
    "R2b4a1e0bf0": ("sai", "thấp",
                    "Câu chỉ áp dụng \"Đối với người lao động hưởng lương theo sản phẩm\". Quy phạm ghi \"Tiền lương làm thêm giờ\" được tính \"theo công thức sau\" mà bỏ giới hạn này (và không có công thức), nên áp cho mọi người lao động. "
                    "\"Tiền lương làm thêm giờ\" lấy từ câu dẫn hoặc tên Điều. Nếu cho rằng phần bỏ không đổi nghĩa thì chọn Đúng, mượn câu dẫn.",
                    ["Đối với người lao động hưởng lương theo sản phẩm", "Đối tượng: Tiền lương làm thêm giờ", "Điều kiện: theo công thức sau"]),
    "Rf82af6111f": ("dien_dat", "vừa",
                    "Nghĩa đúng nhưng gần như rỗng: tiền lương làm việc ban đêm của người hưởng lương theo sản phẩm \"được tính như sau\". Hành vi \"tính tiền lương làm việc vào ban đêm\" đảo trật tự chữ, không nguyên văn.",
                    ["tiền lương làm việc vào ban đêm được tính như sau", "Hành vi: tính tiền lương làm việc vào ban đêm"]),
    "R3b4e8e6a00": ("dung", "vừa",
                    "\"Người lao động đơn phương chấm dứt hợp đồng lao động theo quy định tại Điều 35\": các ô nguyên văn; tính quy phạm \"chưa rõ\" không sai. Quy phạm không nói đây là một trường hợp chấm dứt hợp đồng, nhưng không sai nghĩa.",
                    ["Người lao động đơn phương chấm dứt hợp đồng lao động theo quy định tại Điều 35 của Bộ luật này"]),
    "Rd51e8684a5": ("dien_dat", "thấp",
                    "Ý là giới hạn thời giờ làm việc theo tuần. Định lượng \"10 giờ trong 01 ngày và 48 giờ trong 01 tuần\" ghép lại, không nguyên văn; quy phạm không nêu cái gì bị giới hạn. "
                    "Hành vi đã chứa \"không quá\" nên ghép với \"cấm\" thành phủ định kép; nếu đọc theo nghĩa đen thì chọn Sai.",
                    ["thời giờ làm việc bình thường không quá 10 giờ trong 01 ngày", "Định lượng: 10 giờ trong 01 ngày và 48 giờ trong 01 tuần", "Tính quy phạm: cấm"]),
    "Rf2a3eaec1b": ("sai", "vừa", HIEU_LUC + " (Câu còn nêu hai Nghị định khác, quy phạm chỉ lấy Nghị định 05/2015.)", ["hết hiệu lực thi hành", "Tính quy phạm: nghĩa vụ"]),
    "R9a09f93083": ("dien_dat", "thấp",
                    "Câu: việc cho thôi việc \"chỉ được tiến hành sau khi\" trao đổi ý kiến và thông báo trước 30 ngày. Hành vi viết \"tiếp hành\" (sai chữ, không nguyên văn), chủ thể lấy từ tên Điều; "
                    "quy phạm bỏ chữ \"chỉ\" nên điều kiện từ bắt buộc thành đủ. Nếu coi mất \"chỉ\" là đổi nghĩa thì chọn Sai.",
                    ["chỉ được tiến hành sau khi", "Hành vi: tiếp hành"]),
    "Rfacbb8ed3a": ("dung_ngu_canh", "cao",
                    "Câu dẫn \"Người sử dụng lao động được sử dụng người lao động làm thêm không quá 300 giờ trong 01 năm ...\" cho chủ thể, hành vi, định lượng; điều kiện là nguyên văn điểm d. Nghĩa đúng.",
                    ["được sử dụng người lao động làm thêm không quá 300 giờ trong 01 năm"]),
    "R658e308411": ("dung", "vừa",
                    "Chủ thể và hành vi \"bình đẳng trong thực hiện quyền và nghĩa vụ\" là nguyên văn; quyền đúng. Quy phạm bỏ vế so sánh \"với người lao động làm việc trọn thời gian\" nên hơi mơ hồ nhưng không sai.",
                    ["bình đẳng trong thực hiện quyền và nghĩa vụ với người lao động làm việc trọn thời gian"]),
    "R84292496e5": ("dung_ngu_canh", "cao", NGHILE, ["Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây"]),
    "R0d83c36a50": ("dung", "thấp",
                    "Điều kiện và định lượng là nguyên văn điểm a (\"Ít nhất 45 ngày đối với hợp đồng lao động không xác định thời hạn\"). "
                    "Quy phạm không nói ai làm gì (báo trước của người sử dụng lao động ở câu dẫn), nên gần như rỗng nhưng không sai.",
                    ["phải báo trước cho người lao động như sau", "Ít nhất 45 ngày"]),
    "R4089828986": ("sai", "cao",
                    THAM_VAN + " phạt việc KHÔNG tham khảo ý kiến. Quy phạm ghi \"cấm\" với hành vi \"tham khảo ý kiến ...\", tức cấm tham khảo ý kiến: ngược nghĩa. "
                    "Hành vi còn viết \"mức lao động\" thay cho \"định mức lao động\".",
                    ["Không tham khảo ý kiến", "Tính quy phạm: cấm (từ: \"Không\")", "mức lao động; quy chế thưởng"]),
}
