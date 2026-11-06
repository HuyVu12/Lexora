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
        "cues": "phải, có nghĩa vụ, có trách nhiệm, bắt buộc",
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
        "cues": "có quyền, được quyền",
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
    "context": {
        "term": "Ngữ cảnh",
        "definition": "Câu dẫn của Điều hoặc khoản chứa đoạn trích. Đọc cùng để hiểu đúng phạm vi áp dụng.",
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
