import sys, json
sys.path.insert(0, 'src'); sys.path.insert(0, 'experiments/review-pack-2026-11-24/work')
from collections import Counter
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.gold import GoldStore, row_key
from legal_ai.evaluation import extraction_gold as eg
import gold_drafts as drafts

W = 'experiments/review-pack-2026-11-24/work/'
p = W + 'store.sqlite'
g = GoldStore(p, CorpusStore(p)); sid = 'g5c82c09634e2'
db = g._connect(); row = g._set_row(db, sid)
_, units, _ = g.corpora.bundle(row['corpus_version_id'])
rows = {row_key(r): r for r in json.loads(row['rows'])}
sample = json.load(open(W + 'sample.json', encoding='utf-8'))
missing = [s['i'] for s in sample if s['i'] not in drafts.D]
short = {'45-2019-qh14': 'BLLĐ 2019', '145-2020-nd-cp': 'NĐ 145/2020', '10-2020-tt-bldtbxh': 'TT 10/2020'}
items = []; errors = []; mods = Counter(); unsure = []
for s in sample:
    if s['i'] not in drafts.D:
        continue
    norms, reason, conf = drafts.D[s['i']]
    raw = [{"modality": m, "modality_cue": c, "slots": sl} for m, c, sl in norms]
    try:
        clean = g._clean(rows[s['key']], raw, units)
        if len(clean) != len(raw) or any(a['slots'] != b['slots'] for a, b in zip(clean, raw)):
            errors.append((s['i'], 'slots dropped'))
    except Exception as e:
        errors.append((s['i'], str(e)))
    for m, c, sl in norms:
        mods[m] += 1
    doc = short[s['article'].split('/')[0]]
    if conf == 'thấp':
        unsure.append(s['i'])
    items.append({"id": s['key'], "group": s['article'], "heading": f"{doc} - {s['path']}", "sentence": s['text'],
                  "context": s['context'] or "",
                  "draft": [{"modality": m, **({"cue": c} if c else {}), "slots": sl} for m, c, sl in norms],
                  "reason": reason, "confidence": conf})
print('missing', missing, 'errors', errors)
INSTR = ("Mỗi mục là một câu luật cần xác định quy phạm; agent đã soạn sẵn kết luận để bạn duyệt.\n"
         "Đọc câu và câu dẫn (nếu có), rồi bấm Đồng ý nếu quy phạm soạn sẵn đúng.\n"
         "Nếu sai, sửa tính quy phạm, từ tình thái hoặc các ô; mỗi ô phải là cụm chép nguyên văn từ chính câu.\n"
         "Nếu câu không nêu quy tắc xử sự (định nghĩa, tên mục, chỉ dẫn chiếu), đánh dấu Không có quy phạm.\n"
         "Ô nào chỉ có chữ ở câu dẫn thì để trống, và tính quy phạm lấy theo câu dẫn khi câu không có từ tình thái.\n"
         "Mọi gợi ý là của model, không phải kết luận pháp lý; bạn là người quyết định.")
out = {"task": "gold", "title": "Gán nhãn gold trích xuất - mẫu đồng thuận (12 Điều, 101 câu)", "instructions": INSTR,
       "drafted_by": "claude-sonnet-5-5 (agent trong phiên, 24/11/2026)", "items": items}
json.dump(out, open('experiments/review-pack-2026-11-24/data/gold.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
nn = sum(1 for i in items if i['draft'])
problems = eg.check([rows[s['key']] | {"norms": [{"modality": x["modality"], "slots": x["slots"]} for x in it["draft"]]}
                     for s, it in zip(sample, items)], units)
chk = {"sentences": len(items), "with_norms": nn, "no_norm": len(items) - nn, "norms_total": sum(mods.values()), "per_modality": dict(mods),
       "validation": {"gold_store_clean_passed": len(items) - len({e[0] for e in errors}), "gold_store_clean_failed": errors,
                      "extraction_gold_check_problems": problems},
       "confidence_counts": dict(Counter(i['confidence'] for i in items)),
       "unsure_sentence_indices_low_confidence": unsure, "unsure_count": len(unsure),
       "unsure_notes": ["0-2, 7, 9, 16-18, 27-32, 37-45, 62, 98: không có từ tình thái; khó quyết định là quy phạm (hướng dẫn cách ghi, cách tính, trình tự) hay mô tả, để chưa rõ loại",
                        "3-6, 19-21: có thể là quy phạm (phải ghi thông tin) hoặc chỉ mô tả nội dung mục; draft để trống",
                        "64-77: các trường hợp chấm dứt hợp đồng; draft để chưa rõ loại với Điều kiện, có thể coi là không quy phạm",
                        "81: tính quy phạm theo câu dẫn (Quyền) lệch nghĩa; 91: cụm 'không phải' không nằm trong bộ từ tình thái",
                        "35, 99: Quyền hay Được phép; 48, 57, 98: định nghĩa lẫn quy tắc"]}
json.dump(chk, open(W + 'gold-draft-check.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(json.dumps({k: chk[k] for k in ('sentences', 'with_norms', 'no_norm', 'norms_total', 'per_modality', 'confidence_counts', 'unsure_count')}, ensure_ascii=False))
print('check problems', problems)
