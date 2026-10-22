(() => {
  const $ = id => document.getElementById(id);
  let documents = [], artifact = null;
  function node(tag, text, parent) {const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (parent) parent.append(el); return el;}
  function status(text) {$("status").textContent = text;}
  function studyStatus(text, error = false) {
    const element = $("study-status");
    element.textContent = text;
    element.setAttribute("role", error ? "alert" : "status");
    element.className = error ? "study-error" : "study-progress";
    if (error) element.scrollIntoView({behavior: "smooth", block: "nearest"});
  }
  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form values.");
    return data;
  }
  const post = body => ({method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  function selected() {return [...document.querySelectorAll("input[name=source]:checked")].map(el=>el.value);}
  function sources(items, parent) {
    const details = node("details", undefined, parent); node("summary", "Source references", details);
    items.forEach((s,i) => node("p", `[Source ${i+1}] ${s.document_name} · ${s.page ? `page ${s.page}` : `${s.section || "text"}, chunk ${s.chunk_index}`}\n${s.text_snippet}`, details));
  }
  function renderLibrary() {
    const checked = new Set(selected());
    $("library").replaceChildren();
    const visible = documents.filter(d=>d.filename.toLowerCase().includes($("library-filter").value.toLowerCase()));
    if (!visible.length) node("p", "No matching documents. Upload a source to get started.", $("library"));
    visible.forEach(doc => {
      const row = node("div", undefined, $("library")); row.className="library-row";
      const label = node("label", undefined, row), check = node("input", undefined, label);
      check.type="checkbox"; check.name="source"; check.value=doc.id; check.disabled=doc.status!=="ready"; check.checked=checked.has(doc.id);
      node("span", doc.filename, label);
      node("p", `${doc.source_type.toUpperCase()} · ${doc.chunk_count} chunks · ${doc.status}`, row).className="hint";
      if (doc.error_message) node("p", doc.error_message, row);
      const actions=node("div",undefined,row); actions.className="row-actions";
      const chat=node("a","Chat",actions);chat.href=`/chat?document_id=${encodeURIComponent(doc.id)}`;
      const download=node("a","Download",actions);download.href=`/api/documents/${doc.id}/download`;
      const summary=node("button","Summary",actions);summary.className="btn btn-secondary btn-sm";summary.disabled=doc.status!=="ready";
      summary.onclick=async()=>{summary.disabled=true; status("Generating summary…");try{const data=await api(`/api/documents/${doc.id}/summary`,post({}));node("p",`${data.title}\n${data.overview}\n${data.key_points.join("\n")}`,row);status("Summary ready.");}catch(e){status(e.message);}finally{summary.disabled=false;}};
      const retry=node("button","Reindex / retry",actions);retry.className="btn btn-secondary btn-sm";retry.onclick=async()=>{retry.disabled=true;status("Reindexing?");try{await api(`/api/documents/${doc.id}/reindex`,post({}));await load();status("Index is up to date.");}catch(e){status(e.message);}finally{retry.disabled=false;}};
      const del=node("button","Delete",actions);del.className="btn btn-secondary btn-sm";del.onclick=async()=>{if(!confirm(`Delete ${doc.filename}?`))return;try{await api(`/api/documents/${doc.id}`,{method:"DELETE"});await load();status("Document deleted.");}catch(e){status(e.message);}};
    });
  }
  async function saved() {
    const items=await api("/api/learning");$("saved").replaceChildren();
    if(!items.length)node("p","Your generated materials will appear here.",$("saved"));
    items.forEach(item=>{const row=node("div",undefined,$("saved"));row.className="row-actions";const button=node("button",`${item.kind} · ${new Date(item.created_at+"Z").toLocaleDateString()}`,row);button.className="btn btn-secondary btn-sm";button.onclick=async()=>{try{renderArtifact(await api(`/api/learning/${item.id}`));}catch(e){status(e.message);}};const del=node("button","Delete",row);del.className="btn btn-secondary btn-sm";del.onclick=async()=>{try{await api(`/api/learning/${item.id}`,{method:"DELETE"});await saved();}catch(e){status(e.message);}};});
  }
  async function load(){documents=(await api("/api/documents")).documents;renderLibrary();await saved();}
  $("library-filter").oninput=renderLibrary;
  $("search-form").onsubmit=async event=>{
    event.preventDefault();const button=event.target.querySelector("button");button.disabled=true;status("Searching…");
    try{const ids=selected();const data=await api("/api/search",post({query:$("query").value,mode:$("mode").value,document_ids:ids.length?ids:null}));$("search-results").replaceChildren();if(data.sources.length)sources(data.sources,$("search-results"));else node("p","No supporting passages found.",$("search-results"));status("Search complete.");}catch(e){status(e.message);}finally{button.disabled=false;}
  };
  $("study-form").onsubmit=async event=>{
    event.preventDefault();const ids=selected();if(!ids.length){studyStatus("Select at least one ready document.", true);return;}
    const kind=$("kind").value;
    const button=event.target.querySelector("button"), originalLabel=button.textContent;
    button.disabled=true;button.textContent="Generating…";event.target.setAttribute("aria-busy","true");
    studyStatus(`Generating ${kind} from your selected documents…`);
    try{
      const data=await api(`/api/learning/generate/${kind}`,post({document_ids:ids,topic:$("topic").value,count:Number($("count").value),difficulty:$("difficulty").value,style:$("style").value}));
      renderArtifact(data);studyStatus("Study materials ready.");
      try{await saved();}catch(e){studyStatus("Materials are ready below. The saved list could not refresh; reload the page to reopen them.");}
    }catch(e){studyStatus(e.message,true);}finally{button.disabled=false;button.textContent=originalLabel;event.target.removeAttribute("aria-busy");}
  };
  function evidence(item,parent){node("p",`[Source ${item.source_number}] “${item.quote}”`,parent).className="hint";}
  function renderArtifact(data){
    artifact=data;const target=$("study-results");target.replaceChildren();node("h3",data.content.title,target);
    if(data.kind==="flashcards")data.content.cards.forEach(card=>{const box=node("div",undefined,target);box.className="study-item";node("p",card.front,box);const details=node("details",undefined,box);node("summary","Reveal answer",details);node("p",card.back,details);evidence(card.evidence,details);});
    if(data.kind==="notes")data.content.notes.forEach(note=>{const box=node("div",undefined,target);box.className="study-item";node("h3",note.concept,box);node("p",`Definition: ${note.definition}\n${note.explanation}\nTakeaway: ${note.takeaway}`,box);evidence(note.evidence,box);});
    if(data.kind==="quiz"){
      const form=node("form",undefined,target);
      data.content.questions.forEach((q,i)=>{const field=node("fieldset",undefined,form);field.className="study-item";node("legend",`${i+1}. ${q.question}`,field);q.options.forEach((option,j)=>{const label=node("label",undefined,field),radio=node("input",undefined,label);radio.type="radio";radio.name=`q${i}`;radio.value=j;radio.required=true;node("span",option,label);});});
      const submit=node("button","Submit quiz",form);submit.className="btn btn-primary";
      form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;try{const answers=data.content.questions.map((_,i)=>Number(new FormData(form).get(`q${i}`)));const result=await api(`/api/learning/${data.id}/submit`,post({answers}));node("h3",`Score: ${result.score}/${result.total} (${result.percentage}%)`,target);result.questions.forEach((q,i)=>{node("p",`${i+1}. ${q.options[q.correct_answer]} — ${q.explanation}`,target);evidence(q.evidence,target);});submit.remove();}catch(e){status(e.message);submit.disabled=false;}};
    }
    sources(data.sources,target);target.scrollIntoView({behavior:"smooth",block:"nearest"});
  }
  $("evaluation-button").onclick=async()=>{
    try{const report=await api("/api/evaluation");const target=$("evaluation-results");target.replaceChildren();node("p",`Measured: ${report.measured_at} ? K=${report.k}`,target);const table=node("table",undefined,target);const header=node("tr",undefined,node("thead",undefined,table));["Mode","Hit Rate@K","MRR@K","Support@K","Mean ms"].forEach(text=>node("th",text,header));const body=node("tbody",undefined,table);Object.entries(report.results).forEach(([mode,r])=>{const row=node("tr",undefined,body);[mode,r.hit_rate_at_k.toFixed(3),r.mrr_at_k.toFixed(3),r.support_rate_at_k.toFixed(3),r.mean_retrieval_latency_ms.toFixed(3)].forEach(value=>node("td",value,row));});node("p",report.generation_note,target);}catch(e){status(e.message);}
  };
  window.researchAuth.ready.then(user=>{if(user)load().catch(e=>status(e.message));});
})();
