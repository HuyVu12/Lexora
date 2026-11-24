import sys, json
sys.path.insert(0,'src')
from pathlib import Path
from legal_ai.research.corpus import CorpusStore
from legal_ai.research.gold import GoldStore, row_key
from legal_ai.indexing.records import unit_path
p='experiments/review-pack-2026-11-24/work/store.sqlite'
g=GoldStore(p,CorpusStore(p))
sid='g5c82c09634e2'
import sqlite3
db=g._connect()
row=g._set_row(db,sid); sample=g._sample(db,sid)
rows=json.loads(row['rows'])
docs,units,_=g.corpora.bundle(row['corpus_version_id'])
titles={d['document_id']:d['title'] for d in docs}
by={u['unit_id']:u for u in units}
out=[]
from legal_ai.evaluation import extraction_gold as eg
chosen=set(sample['articles'])
for r in rows:
    if eg.article_id(r['unit_id']) not in chosen: continue
    u=by[r['unit_id']]; path,_=unit_path(u,by); par=by.get(u['parent_id'])
    ctx=par['text'].strip().split("\n")[0][:600] if par is not None and par['unit_type']!='chapter' else None
    out.append(dict(i=len(out),key=row_key(r),article=eg.article_id(r['unit_id']),doc=titles[u['document_id']],path=path,text=r['text'],context=ctx))
json.dump(out,open('experiments/review-pack-2026-11-24/work/sample.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(len(out))
for o in out: print(o['i'],o['path'],'|',o['context'] and o['context'][:200],'\n   >>',o['text'])
