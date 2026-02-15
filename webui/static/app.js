async function postJSON(url, payload) {
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  if(!res.ok) throw new Error(await res.text());
  return await res.json();
}

const $ = (id)=>document.getElementById(id);
$('btnAnalyze').onclick = async () => {
  const text = $('input').value.trim();
  if(!text) return;
  try {
    const data = await postJSON('/api/analyze', {text});
    $('norm').textContent = JSON.stringify(data.normalized, null, 2);
    $('sandhi').textContent = JSON.stringify(data.sandhi.splits || data.sandhi, null, 2);
    $('morph').textContent = JSON.stringify(data.morph, null, 2);

    // Entities
    const ent = await postJSON('/api/entities', {text});
    $('entities').textContent = JSON.stringify(ent.entities || ent, null, 2);
  } catch(err) {
    alert(err);
  }
};

$('btnTranslate').onclick = async () => {
  const text = $('input').value.trim();
  if(!text) return;
  try {
    const data = await postJSON('/api/translate?explain=true', {text});
    $('translation').textContent = JSON.stringify(data, null, 2);
  } catch(err) {
    alert(err);
  }
};

async function doTranslateExplain(text) {
  const r = await fetch('/api/translate?explain=true', {
    method:'POST',
    headers:{'Content-Type':'application/json;charset=utf-8'},
    body: JSON.stringify({ text })
  });
  const data = await r.json();

  // Show translation prominently
  const card = document.getElementById('translation-card');
  const t = document.getElementById('translation-text');
  const meta = document.getElementById('translation-meta');
  const btn = document.getElementById('copy-translation');

  const engine = data.engine || (data.evidence && data.evidence.engine) || 'unknown';
  const rationale = (data.evidence && data.evidence.rationale) ? data.evidence.rationale : '';
  const translation = data.translation || (data.error ? `[error] ${data.error}` : '');

  t.textContent = translation;
  meta.textContent = `engine: ${engine}${rationale ? ' — ' + rationale : ''}`;
  card.style.display = 'block';

  btn.onclick = () => navigator.clipboard.writeText(translation);
}
