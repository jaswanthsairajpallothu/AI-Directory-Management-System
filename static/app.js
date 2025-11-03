const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
const list = document.getElementById('list');

ws.onmessage = e => {
  const data = JSON.parse(e.data);
  const div = document.createElement('div');
  div.className = 'suggestion';
  div.innerHTML = `<b>${data.suggested_category}</b> (conf: ${data.confidence.toFixed(2)})<br><code>${data.path}</code>`;
  const yes = document.createElement('button'); yes.textContent = 'Accept';
  const no = document.createElement('button'); no.textContent = 'Reject';
  yes.onclick = () => act(data.path, true, div);
  no.onclick = () => act(data.path, false, div);
  div.append(yes, no);
  list.prepend(div);
};

async function act(path, accept, div) {
  const url = `/api/apply?path=${encodeURIComponent(path)}&accept=${accept}`;
  const res = await fetch(url, {method: 'POST'});
  if (res.ok) div.remove();
  else alert('Error applying action.');
}
