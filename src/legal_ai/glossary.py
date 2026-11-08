"""Plain-language explanations of Lexora's review vocabulary, shown on hover or focus.

One source for the demo workspace and both graph viewers: `embed_terms` inlines the
glossary, the tooltip script and its style into a page at the `<!--LEXORA_TERMS-->` marker.
The texts explain how Lexora uses each word when reviewing a statute; they are not legal
definitions and not legal advice. Examples are illustrative sentences, not quoted law.
"""

from pathlib import Path
import json

MARKER = "<!--LEXORA_TERMS-->"

# Each entry: term (display name), definition, optional cues (words that signal it),
# optional example sentence and the exact part of it the term refers to (highlight).
GLOSSARY = {
    "norm": {
        "term": "Quy phạm",
        "definition": "Một quy tắc xử sự rút ra từ một câu trong văn bản: ai phải, được hay không được làm gì, trong điều kiện nào. Lexora tách mỗi quy phạm thành các thành phần để bạn đối chiếu với nguyên văn.",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
    },
    "modality": {
        "term": "Tính quy phạm",
        "definition": "Cho biết câu đang bắt buộc, cấm, cho phép hay trao quyền. Lexora nhận ra loại này qua từ chỉ dấu trong câu, ví dụ “phải”, “không được”, “có quyền”.",
        "example": "Người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "phải",
    },
    "obligation": {
        "term": "Nghĩa vụ",
        "definition": "Việc chủ thể bắt buộc phải làm. Không làm là vi phạm.",
        "cues": "phải, có nghĩa vụ, có trách nhiệm, bắt buộc, buộc, chịu trách nhiệm",
        "example": "Người sử dụng lao động phải trả lương cho người lao động đúng hạn.",
        "highlight": "phải",
    },
    "prohibition": {
        "term": "Điều cấm",
        "definition": "Việc chủ thể không được làm.",
        "cues": "không được, cấm, nghiêm cấm, bị cấm",
        "example": "Người sử dụng lao động không được giữ bản chính giấy tờ tùy thân của người lao động.",
        "highlight": "không được",
    },
    "entitlement": {
        "term": "Quyền",
        "definition": "Điều chủ thể được hưởng hoặc được đòi hỏi; bên kia phải tôn trọng hoặc đáp ứng.",
        "cues": "có quyền, được quyền, được",
        "example": "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động.",
        "highlight": "có quyền",
    },
    "permission": {
        "term": "Được phép",
        "definition": "Chủ thể được làm nhưng không bắt buộc phải làm.",
        "cues": "có thể, được",
        "example": "Hai bên có thể thỏa thuận về việc làm thử.",
        "highlight": "có thể",
    },
    "definition": {
        "term": "Định nghĩa",
        "definition": "Câu giải thích một từ ngữ được dùng trong văn bản. Không đặt ra việc phải làm.",
        "cues": "là, được hiểu là",
        "example": "Người lao động là người làm việc cho người sử dụng lao động theo thỏa thuận và được trả lương.",
        "highlight": "là",
    },
    "procedure": {
        "term": "Thủ tục",
        "definition": "Trình tự, cách thức hoặc hồ sơ cần có để thực hiện một việc.",
        "example": "Việc xử lý kỷ luật lao động phải được lập thành biên bản.",
        "highlight": "được lập thành biên bản",
    },
    "unknown_modality": {
        "term": "Chưa rõ loại",
        "definition": "Lexora chưa tìm thấy từ chỉ dấu loại quy phạm trong câu. Bạn có thể bôi đen từ chỉ dấu trong văn bản để gán loại.",
    },
    "actor": {
        "term": "Chủ thể",
        "definition": "Người hoặc tổ chức mà quy phạm hướng tới: ai phải làm, ai được làm hoặc ai không được làm.",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "người sử dụng lao động",
    },
    "action": {
        "term": "Hành vi",
        "definition": "Việc chủ thể làm, được làm hoặc không được làm. Thường là động từ chính của câu.",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "thông báo",
    },
    "object": {
        "term": "Đối tượng",
        "definition": "Sự vật, giấy tờ hay nội dung mà hành vi tác động tới.",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "kết quả thử việc",
    },
    "beneficiary": {
        "term": "Bên thụ hưởng",
        "definition": "Người được hưởng lợi ích từ việc chủ thể thực hiện quy phạm.",
        "example": "Người sử dụng lao động phải trả lương cho người lao động đúng hạn.",
        "highlight": "người lao động",
    },
    "recipient": {
        "term": "Bên nhận",
        "definition": "Người nhận thông tin, giấy tờ hoặc tài sản mà chủ thể chuyển tới.",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "người lao động",
    },
    "counterparty": {
        "term": "Bên đối ứng",
        "definition": "Bên còn lại trong quan hệ mà chủ thể tham gia, ví dụ bên cùng ký hợp đồng.",
        "example": "Người sử dụng lao động giao kết hợp đồng lao động với người lao động.",
        "highlight": "người lao động",
    },
    "outcome": {
        "term": "Kết quả",
        "definition": "Hệ quả pháp lý xảy ra khi quy phạm được áp dụng.",
        "example": "Khi việc làm thử đạt yêu cầu thì hợp đồng lao động đã giao kết được tiếp tục thực hiện.",
        "highlight": "hợp đồng lao động đã giao kết được tiếp tục thực hiện",
    },
    "conditions": {
        "term": "Điều kiện",
        "definition": "Hoàn cảnh phải có thì quy phạm mới áp dụng.",
        "cues": "khi, nếu, trường hợp, trong thời gian",
        "example": "Khi kết thúc thời gian thử việc, người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.",
        "highlight": "Khi kết thúc thời gian thử việc",
    },
    "exceptions": {
        "term": "Ngoại lệ",
        "definition": "Trường hợp quy phạm không áp dụng dù các điều kiện khác đã có.",
        "cues": "trừ trường hợp, trừ khi, không áp dụng",
        "example": "Người lao động phải báo trước cho người sử dụng lao động, trừ trường hợp không được trả lương đúng hạn.",
        "highlight": "trừ trường hợp không được trả lương đúng hạn",
    },
    "quantities": {
        "term": "Định lượng",
        "definition": "Con số, tỷ lệ hoặc mức tối thiểu, tối đa đi kèm quy phạm.",
        "example": "Tiền lương thử việc ít nhất phải bằng 85% mức lương của công việc đó.",
        "highlight": "ít nhất phải bằng 85%",
    },
    "deadlines": {
        "term": "Thời hạn",
        "definition": "Khoảng thời gian hoặc mốc thời gian phải tuân theo.",
        "example": "Người sử dụng lao động phải thanh toán đủ các khoản tiền trong thời hạn 14 ngày làm việc.",
        "highlight": "trong thời hạn 14 ngày làm việc",
    },
    "scope": {
        "term": "Ngữ cảnh cha",
        "definition": "Câu dẫn ở đầu Điều hoặc khoản mà câu đang xét thuộc về. Câu dẫn áp dụng cho mọi điểm bên dưới nó.",
        "example": "Người lao động có các quyền sau đây: a) Làm việc, tự do lựa chọn việc làm.",
        "highlight": "Người lao động có các quyền sau đây:",
    },
    "references": {
        "term": "Dẫn chiếu",
        "definition": "Chỗ câu nhắc tới một Điều, khoản hoặc văn bản khác. Lexora chỉ nối dẫn chiếu khi tìm được đúng đích; không tự suy đoán.",
        "example": "Người lao động được nghỉ theo quy định tại Điều 111 của Bộ luật này.",
        "highlight": "theo quy định tại Điều 111 của Bộ luật này",
    },
    "gap": {
        "term": "Câu chưa có quy phạm",
        "definition": "Câu trong văn bản chưa được tách thành quy phạm nào. Trước khi công bố, mỗi câu như vậy cần được thêm quy phạm hoặc đánh dấu không phải quy phạm, để không bỏ sót nội dung.",
    },
    "entity": {
        "term": "Thực thể",
        "definition": "Một người, tổ chức hay khái niệm được nhắc tới trong quy phạm, ví dụ “người lao động”. Hai đề cập chỉ được coi là cùng một thực thể khi người duyệt xác nhận.",
    },
    "source_unit": {
        "term": "Đơn vị nguồn",
        "definition": "Điều, khoản hoặc điểm trong văn bản gốc chứa câu mà quy phạm được rút ra.",
    },
    "evidence": {
        "term": "Bằng chứng",
        "definition": "Đoạn trích nguyên văn kèm vị trí ký tự chính xác trong văn bản gốc. Mỗi thành phần của quy phạm đều phải có bằng chứng.",
    },
    "approved": {
        "term": "Quy phạm đã duyệt",
        "definition": "Quy phạm đã được người duyệt đối chiếu với nguyên văn và chấp nhận. Chỉ quy phạm đã duyệt mới được dùng khi hỏi đáp. Hiệu lực pháp luật của văn bản vẫn chưa được xác minh.",
    },
    "ai": {
        "term": "AI đề xuất",
        "definition": "Quy phạm do model AI đề xuất cho câu mà bộ quy tắc chưa tách được. Mọi giá trị AI đưa ra đều được kiểm tra có đúng nguyên văn trong câu; bạn vẫn cần duyệt như mọi quy phạm khác.",
    },
    "manual": {
        "term": "Thêm thủ công",
        "definition": "Quy phạm do người duyệt tự thêm bằng cách bôi đen đoạn trong văn bản.",
    },
    "cue": {
        "term": "Cần bổ sung",
        "definition": "Câu có từ chỉ dấu quy phạm nhưng bộ quy tắc chưa tách được chủ thể hoặc hành vi. Hãy dùng nút Sửa và bôi đen các thành phần còn thiếu.",
    },
    "attention": {
        "term": "Cần chú ý",
        "definition": "Quy phạm có dấu hiệu cần đọc kỹ, ví dụ câu có phủ định, ngoại lệ hoặc thiếu chủ thể.",
    },
    "revision": {
        "term": "Phiên bản",
        "definition": "Mỗi lần công bố tạo một phiên bản mới của kho. Phiên bản cũ được giữ nguyên, và các cuộc trò chuyện đã bắt đầu vẫn dùng phiên bản lúc bắt đầu.",
    },
    "private": {
        "term": "Kho riêng tư",
        "definition": "Nội dung kho không bao giờ được gửi ra ngoài máy này, kể cả khi bật AI.",
    },
    "public": {
        "term": "Kho công khai",
        "definition": "Cho phép gửi nội dung kho tới dịch vụ AI khi bạn chủ động chọn dùng AI cho một lượt.",
    },
    "audit_duplicate_heading": {
        "term": "Tiêu đề trùng số",
        "definition": "Parser gặp lại một số Điều, khoản hoặc điểm đã có trong cùng cấp cha. Chữ vẫn được giữ nhưng gộp vào đơn vị trước đó, nên cần đối chiếu văn bản gốc. Thường do văn bản gốc gõ lặp, ví dụ hai điểm “d)” liền nhau hoặc hai dòng “Chương XI”.",
        "example": "d) Quyết định việc cho phép nhà thầu tuyển dụng; d) Chấp thuận vị trí công việc.",
        "highlight": "d)",
    },
    "audit_orphan_heading": {
        "term": "Tiêu đề không có cấp cha",
        "definition": "Một dòng trông như khoản (“1.”) hoặc điểm (“a)”) nhưng không nằm trong Điều hoặc khoản nào. Dòng đó được giữ là chữ của đơn vị đứng trước, không thành đơn vị riêng.",
    },
    "audit_sequence_gap": {
        "term": "Số thứ tự bị nhảy",
        "definition": "Số Điều hoặc khoản không liền nhau, ví dụ sau Điều 91 là Điều 93. Có thể văn bản gốc thiếu một tiêu đề; nếu corpus chỉ lấy một số Điều được chọn thì chỗ nhảy là bình thường.",
    },
    "audit_heading_variant": {
        "term": "Tiêu đề Điều viết sai chính tả",
        "definition": "Văn bản gốc viết sai chữ “Điều”. Lexora vẫn tách đúng Điều đó và ghi lại để bạn biết nguồn có lỗi gõ; nguyên văn không bị sửa.",
        "example": "Điêu 38. Chậm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp",
        "highlight": "Điêu",
    },
    "audit_quoted_text": {
        "term": "Trích dẫn sửa đổi",
        "definition": "Điều này sửa đổi một văn bản khác và trích nội dung mới trong dấu ngoặc kép. Các Điều, khoản, điểm bên trong trích dẫn thuộc văn bản bị sửa, nên Lexora giữ chúng là chữ của khoản đang trích dẫn và không tách thành đơn vị con. Kho tri thức chưa nhập loại Điều này.",
        "example": "Sửa đổi, bổ sung khoản 5 Điều 3 như sau: “5. Giám đốc điều hành là người đứng đầu chi nhánh.”",
        "highlight": "“5. Giám đốc điều hành là người đứng đầu chi nhánh.”",
    },
    "audit_unclosed_quote": {
        "term": "Dấu ngoặc kép không đóng",
        "definition": "Một dòng mở ngoặc kép nhưng đến hết văn bản không có dấu đóng. Lexora bỏ qua dấu này và tách bình thường; nên xem văn bản gốc có thiếu dấu không.",
    },
    "audit_appendix_start": {
        "term": "Bắt đầu phụ lục",
        "definition": "Từ dòng “Phụ lục” trở đi là biểu mẫu kèm theo văn bản. Các dòng “Điều 1.” trong mẫu quyết định không phải Điều của văn bản, nên Lexora không tách phần này và không đưa vào bản ghi truy xuất; nội dung vẫn xem được ở mục Phụ lục.",
    },
    "q_lookup": {
        "term": "Tra cứu",
        "definition": "Câu hỏi về một quy định cụ thể, trả lời được từ một hoặc vài đơn vị liền nhau.",
        "example": "Tiền lương thử việc ít nhất bằng bao nhiêu phần trăm?",
    },
    "q_synthesis": {
        "term": "Tổng hợp",
        "definition": "Câu hỏi phải ghép nhiều quy định, ở nhiều Điều hoặc nhiều văn bản, mới trả lời đủ.",
        "example": "Khi đơn phương chấm dứt hợp đồng, người lao động phải báo trước bao lâu và được trợ cấp gì?",
    },
    "q_temporal": {
        "term": "Hiệu lực, sửa đổi",
        "definition": "Câu hỏi về thời điểm áp dụng, việc văn bản còn hiệu lực hay đã bị sửa đổi, thay thế. Mặc định là từ chối, trừ khi chính nguyên văn trong corpus nêu rõ.",
        "example": "Nghị định 12/2022 còn áp dụng không?",
    },
    "q_out_of_scope": {
        "term": "Ngoài phạm vi",
        "definition": "Câu hỏi không có căn cứ trong corpus đã khóa hoặc không thuộc pháp luật lao động; hệ thống nên từ chối.",
    },
    "expect_answer": {
        "term": "Trả lời",
        "definition": "Corpus có đủ căn cứ nguyên văn để trả lời; người gán phải chọn các đơn vị chứa căn cứ đó.",
    },
    "expect_refuse": {
        "term": "Từ chối",
        "definition": "Corpus không đủ căn cứ, câu hỏi ngoài phạm vi hoặc cần xác minh hiệu lực mà corpus không chứng minh được; hệ thống trả lời đúng là từ chối.",
    },
    "relevant_units": {
        "term": "Đơn vị liên quan",
        "definition": "Các Điều, khoản, điểm thật sự chứa căn cứ cho câu trả lời; chọn đơn vị nhỏ nhất đủ căn cứ. Đây là đáp án dùng để tính Recall@K của truy xuất.",
    },
    "paraphrase_family": {
        "term": "Nhóm diễn đạt",
        "definition": "Các câu hỏi cùng ý nhưng viết khác nhau. Cả nhóm luôn rơi vào cùng tập dev hoặc held-out để kết quả không bị rò rỉ.",
    },
    "proposal_mode": {
        "term": "Chế độ gán nhãn",
        "definition": "Mỗi người chọn một lần: tự gán hoặc xem đề xuất của model. Xem cùng một đề xuất làm hai người dễ giống nhau hơn, nên chế độ được ghi lại khi báo cáo đồng thuận.",
    },
    "kappa": {
        "term": "Kappa (Cohen)",
        "definition": "Mức đồng thuận của hai người gán đã trừ phần trùng do ngẫu nhiên: 1 là hoàn toàn đồng ý, 0 là ngang ngẫu nhiên. Thường coi từ 0,6 trở lên là khá, từ 0,8 là tốt.",
    },
    "dice": {
        "term": "Hệ số Dice",
        "definition": "Mức trùng giữa hai tập đơn vị liên quan: 2 x số đơn vị chung / tổng số đơn vị của hai người. 1 là hai tập giống hệt, 0 là không có đơn vị chung.",
    },
    "full_agreement": {
        "term": "Khớp hoàn toàn",
        "definition": "Tỉ lệ câu mà hai người giống nhau ở mọi trường: loại câu, hành vi mong đợi và tập đơn vị liên quan.",
    },
    "held_out": {
        "term": "Tập held-out",
        "definition": "Phần câu hỏi giữ riêng, chỉ chạy một lần sau khi đã khóa cấu hình trên tập dev. Không dùng để chọn model, prompt hay tham số.",
    },
    "adjudication": {
        "term": "Chốt nhãn",
        "definition": "Sau khi so hai người gán, chọn hoặc sửa thành một nhãn cuối cho mỗi câu. Nhãn cuối là đáp án dùng trong thực nghiệm.",
    },
    "frozen_version": {
        "term": "Phiên bản đã khóa",
        "definition": "Bản chụp cố định các văn bản của corpus, có mã băm. Bộ câu hỏi, gold set và thực nghiệm đều gắn với một phiên bản nên văn bản không thay đổi giữa chừng.",
    },
    "leaf_unit": {
        "term": "Đơn vị lá",
        "definition": "Đơn vị nhỏ nhất không chia tiếp: Điều không có khoản, khoản không có điểm, hoặc điểm. ĐK2 truy xuất theo đơn vị này.",
    },
    "effect_status": {
        "term": "Trạng thái hiệu lực",
        "definition": "Trạng thái vbpl.vn ghi vào lúc tải văn bản. Lexora chỉ lưu lại để tham khảo, không tự xác minh hiệu lực pháp luật.",
    },
    "parser_warning": {
        "term": "Cảnh báo parser",
        "definition": "Chỗ máy tách Chương, Điều, khoản, điểm chưa chắc chắn. Mở văn bản để xem từng cảnh báo và đối chiếu với nguyên văn trước khi khóa phiên bản.",
    },
    "unassigned_text": {
        "term": "Chữ ngoài các Điều",
        "definition": "Phần đầu văn bản trước Điều đầu tiên: quốc hiệu, số hiệu, căn cứ ban hành. Được giữ nguyên nhưng không thuộc đơn vị nào.",
    },
    "f1_strict": {
        "term": "F1, khớp chặt",
        "definition": "Trung bình điều hòa của độ chính xác và độ phủ. Khớp chặt: hai cụm từ phải giống hệt sau khi bỏ khác biệt chữ hoa, khoảng trắng và dấu câu ở hai đầu.",
    },
    "f1_lenient": {
        "term": "F1, khớp lỏng",
        "definition": "Như F1 khớp chặt nhưng chấp nhận lệch ranh giới: một cụm chứa cụm kia, hoặc trùng ít nhất một nửa số tiếng.",
    },
    "dk3": {
        "term": "ĐK3",
        "definition": "Kho tri thức do LLM trích xuất theo schema, giữ nguyên mọi giá trị model trả về, chưa qua kiểm chứng.",
    },
    "dk4": {
        "term": "ĐK4",
        "definition": "Chính ĐK3 sau khi bộ kiểm chứng tự động loại các bản ghi vi phạm (sai schema, sai đơn vị, cụm không nguyên văn, từ tình thái bịa hoặc mâu thuẫn, trùng lặp).",
    },
    "modality_unverified": {
        "term": "Tính quy phạm chưa xác minh",
        "definition": "Model nêu tính quy phạm nhưng không có từ tình thái nào trong câu để kiểm, thường gặp ở các điểm liệt kê. Bản ghi vẫn được giữ.",
    },
    "planted_errors": {
        "term": "Chèn lỗi có chủ đích",
        "definition": "Lấy bản ghi sạch của ĐK4, cố ý làm hỏng theo từng loại lỗi rồi xem bộ kiểm chứng bắt được bao nhiêu. Lỗi kỹ thuật nên bị bắt; lỗi ngữ nghĩa như bỏ phủ định thì không, đó là giới hạn cần báo cáo.",
    },
    "rejected_claims": {
        "term": "Bị loại",
        "definition": "Số bản ghi của ĐK3 không vào được ĐK4 và tỉ lệ trên tổng số; lý do nằm trong phần chi tiết.",
    },
    "context": {
        "term": "Ngữ cảnh",
        "definition": "Câu dẫn của Điều hoặc khoản chứa đoạn trích. Đọc cùng để hiểu đúng phạm vi áp dụng.",
    },
    "daily_limit": {
        "term": "Hạn mức mỗi ngày",
        "definition": "Số lượt gọi model tối đa của một tính năng trong một ngày (theo giờ máy chủ). Hết hạn mức thì lượt gọi bị chặn trước khi gửi đi; để trống là không giới hạn.",
    },
    "feature_switch": {
        "term": "Công tắc tính năng",
        "definition": "Tắt một tính năng dùng model (trả lời bằng model, tách quy phạm, đề xuất nhãn, tìm theo ngữ nghĩa) ngay lập tức khi có sự cố; các phần không dùng model vẫn chạy.",
    },
    "run_budget": {
        "term": "Ngân sách lượt chạy",
        "definition": "Số lượt gọi tối đa đặt bằng cờ khi khởi động app (ví dụ --proposal-max-calls). Hết ngân sách thì phải khởi động lại app.",
    },
    "latency_p95": {
        "term": "p95",
        "definition": "95% số lượt nhanh hơn mức này. Trung vị (p50) cho biết lượt điển hình, p95 cho biết lượt chậm.",
    },
    "blocked_calls": {
        "term": "Lượt bị chặn",
        "definition": "Lượt gọi không được gửi đi vì tính năng đang tắt hoặc đã hết hạn mức mỗi ngày; không tính vào hạn mức.",
    },
    "no_evidence_rate": {
        "term": "Không tìm thấy căn cứ",
        "definition": "Tỉ lệ câu hỏi không có đoạn nguồn đã duyệt nào khớp. Cao nghĩa là kho thiếu nội dung hoặc người dùng hỏi ngoài phạm vi.",
    },
}


def bilingual():
    """{key: {"vi": entry, "en": entry}}; English keeps the Vietnamese example and highlight."""
    from legal_ai.glossary_en import GLOSSARY_EN
    result = {}
    for key, vi in GLOSSARY.items():
        en = {**{k: vi[k] for k in ("example", "highlight") if k in vi}, **GLOSSARY_EN[key]}
        result[key] = {"vi": vi, "en": en}
    return result


def glossary_json():
    """JSON safe to embed inside a <script type="application/json"> element."""
    text = json.dumps(GLOSSARY, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def embed_terms(page):
    """Inline the glossary, tooltip style and tooltip script at the page's marker."""
    if MARKER not in page:
        raise ValueError("Page has no glossary marker")
    here = Path(__file__).parent
    style = (here / "term-tip.css").read_text(encoding="utf-8")
    script = (here / "term-tip.js").read_text(encoding="utf-8")
    block = (f'<script id="lexora-glossary" type="application/json">{glossary_json()}</script>\n'
             f"<style>\n{style}</style>\n<script data-lexora-terms>\n{script}</script>")
    return page.replace(MARKER, block, 1)
