/* Same-origin local source library and revision-bound chat. No external browser requests. */
(() => {
  let session = null;
  const statusNames = {sources_found:'Đoạn nguồn phù hợp từ KB đã duyệt',answered:'Câu trả lời của model',
    insufficient_evidence:'Chưa tìm thấy đủ căn cứ trong tri thức đã duyệt',provider_disabled:'Model chưa bật',
    transfer_not_approved:'Chưa duyệt gửi dữ liệu',provider_error:'Model chưa trả lời được',answer_rejected:'Đầu ra model không đạt kiểm tra citation'};
  async function refreshChat(useCurrent=false) {
    const state = await api('/api/state');
    const selected = $('chatRevision').value;
    $('chatRevision').replaceChildren();
    for (const rev of state.revisions) {
      const option = el('option',`${rev.id===state.current_revision?'Hiện tại · ':''}${rev.id.slice(0,8)} · ${rev.reviewer||'KB gốc chưa duyệt nhập'}`);
      option.value=rev.id; $('chatRevision').append(option);
    }
    $('chatRevision').value = !useCurrent&&state.revisions.some(r=>r.id===selected) ? selected : state.current_revision;
    $('chatSession').replaceChildren();
    const empty=el('option','Chọn cuộc trò chuyện…');empty.value='';$('chatSession').append(empty);
    for (const chat of state.chat_sessions) {
      const option=el('option',`${chat.id.slice(0,8)} · revision ${chat.revision.slice(0,8)}`);
      option.value=chat.id;$('chatSession').append(option);
    }
    if(session)$('chatSession').value=session.id;
    $('llmOption').disabled=!state.router_enabled;
    $('llmOption').textContent=state.router_enabled?'Model 9Router (cần duyệt gửi từng lượt)':'Model 9Router (chưa bật)';
    $('routerStatus').textContent=state.router_enabled?'Có route đã cấu hình; có giới hạn số lượt.':'Tra cứu local sẵn sàng; gọi model đang tắt.';
    if(!state.router_enabled)$('chatMode').value='extractive';
    updateMode();
  }
  function updateMode(){const live=$('chatMode').value==='llm';$('transferLabel').classList.toggle('hide',!live);$('askChat').textContent=live?'Gửi lượt hỏi này sang 9Router':'Tra cứu nguồn đã duyệt';if(!live)$('publicTransfer').checked=false;}
  function renderSession(){
    $('chatTurns').replaceChildren();
    if(!session){$('askChat').disabled=true;return;}
    $('chatBinding').textContent=`Cuộc trò chuyện ${session.id.slice(0,8)} · cố định revision ${session.revision.slice(0,8)}. KB mới được gộp sẽ cần một cuộc trò chuyện mới.`;
    $('askChat').disabled=false;
    for(const turn of session.turns){
      const box=el('article',undefined,'claim');
      box.append(el('h3',turn.question),el('span',`${statusNames[turn.status]||turn.status} · revision ${turn.revision.slice(0,8)}`,'badge'),el('p',turn.note,'muted'));
      for(const statement of turn.statements){box.append(el('p',statement.text+' '+statement.citation_ids.map(id=>'['+id+']').join(' ')));}
      if(turn.error_code)box.append(el('p','Mã lỗi: '+turn.error_code,'muted'));
      for(const cite of turn.citations){
        const detail=el('details'),summary=el('summary',`[${cite.id}] ${cite.title} · ${cite.evidence.unit_id.split('/').slice(-2).join(' / ')}`);
        detail.append(summary,el('blockquote',cite.evidence.quote));
        for(const scope of cite.scope)detail.append(el('p','Ngữ cảnh cha đã lưu:','muted'),el('blockquote',scope.quote));
        detail.append(el('p',`Nguồn ${cite.evidence.unit_id} · offset [${cite.evidence.start}, ${cite.evidence.end})`,'muted'),el('code','Text hash: '+cite.evidence.normalized_sha256));
        if(cite.synthetic)detail.append(el('p','DỮ LIỆU TỔNG HỢP — KHÔNG PHẢI LUẬT THẬT','notice'));
        if(/^https:\/\//.test(cite.source_url)){const a=el('a','Xem văn bản nguồn chính thức ↗');a.href=cite.source_url;a.target='_blank';a.rel='noopener';detail.append(el('br'),a);}
        box.append(detail);
      }
      $('chatTurns').append(box);
    }
  }
  async function loadLibrary(){
    const data=await api('/api/sources');$('sourceLibrary').replaceChildren();
    if(!data.entries.length){$('sourceLibrary').append(el('p','Chưa nạp catalog nguồn. Có thể nhập TXT bên dưới.','muted'));return;}
    for(const source of data.entries){
      const row=el('div',undefined,'entity');
      row.append(el('strong',source.title),el('p',`${source.preflight.structured_claims} quy phạm tách một phần · tải ${source.downloaded_at.slice(0,10)} · chờ duyệt`,'muted'));
      const button=el('button','Tạo bản nháp để duyệt','secondary');
      button.onclick=()=>busy(button,async()=>{const draft=await api('/api/prepare-source',{source_id:source.id});await refresh();await loadDraft(draft.id);await refreshChat();});row.append(button);$('sourceLibrary').append(row);
    }
  }
  $('startChat').onclick=()=>busy($('startChat'),async()=>{session=await api('/api/chat/start',{revision:$('chatRevision').value});renderSession();await refreshChat();message('Đã tạo cuộc trò chuyện trên revision đã chọn.');});
  $('chatSession').onchange=()=>{if(!$('chatSession').value){session=null;renderSession();return;}busy($('startChat'),async()=>{session=await api('/api/chat/session?id='+encodeURIComponent($('chatSession').value));renderSession();message('Đã mở cuộc trò chuyện đã lưu.');});};
  $('chatMode').onchange=updateMode;
  $('askChat').onclick=()=>busy($('askChat'),async()=>{
    if(!session)throw Error('Hãy tạo cuộc trò chuyện trên revision đã duyệt.');
    const mode=$('chatMode').value;
    if(mode==='llm'&&!$('publicTransfer').checked)throw Error('Cần duyệt gửi câu hỏi và trích đoạn công khai cho lượt này.');
    try {await api('/api/chat/ask',{session_id:session.id,question:$('chatQuestion').value,mode,allow_public_transfer:mode==='llm'&&$('publicTransfer').checked});}
    finally {$('publicTransfer').checked=false;}
    session=await api('/api/chat/session?id='+session.id);renderSession();$('chatQuestion').value='';message('Đã lưu lượt hỏi theo revision của cuộc trò chuyện.');
  });
  // Refresh revision choices after a publish; keep the current session pinned.
  const publishButton=$('publish');
  const previousPublish=publishButton.onclick;
  publishButton.onclick=async()=>{await previousPublish();await refreshChat(true).catch(e=>message(e.message,true));};
  Promise.all([refreshChat(),loadLibrary()]).catch(e=>message(e.message,true));
})();
