function qs(k){return new URLSearchParams(location.search).get(k)}
async function loadOne(id){
  const r = await fetch(`/api/passage/${id}/variants`);
  if(!r.ok){ alert(await r.text()); return; }
  const d = await r.json();
  document.getElementById('skt').textContent = d.text || '';
  document.getElementById('norm').textContent = d.normalized || '';
  document.querySelector('.src').textContent = `(${d.pipeline.engine||''})`;
  document.getElementById('pipe').textContent = d.pipeline.translation || '';
  document.getElementById('rat').textContent  = d.pipeline.rationale || '';
  const refs = d.references || {};
  const chunks = [];
  if(refs.bori)   chunks.push(`<div><b>BORI:</b> ${escapeHtml(refs.bori)}</div>`);
  if(refs.debroy) chunks.push(`<div><b>Debroy:</b> ${escapeHtml(refs.debroy)}</div>`);
  if(refs.dutt)   chunks.push(`<div><b>Dutt:</b> ${escapeHtml(refs.dutt)}</div>`);
  if(refs.notes)  chunks.push(`<div class="muted"><b>Notes:</b> ${escapeHtml(refs.notes)}</div>`);
  document.getElementById('refs').innerHTML = chunks.join('') || '<i class="muted">No references found.</i>';
  document.getElementById('view').style.display = 'block';
}
function escapeHtml(s){return (s||'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m]))}
document.getElementById('load').onclick=()=>{
  const id = document.getElementById('pid').value.trim();
  if(id) loadOne(id);
}
const init = qs('id'); if(init){ document.getElementById('pid').value=init; loadOne(init); }
