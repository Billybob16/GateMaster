async function fetchConfig() {
  try {
    const res = await fetch('/debug');
    const text = await res.text();
    const pre = document.getElementById('rtu-json-preview');
    if (pre) {
      pre.textContent = text;
    }
  } catch (e) {
    console.error(e);
  }
}

function setStageActive(stageId) {
  ['stage1', 'stage2', 'stage3'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('active', id === stageId);
  });
}

function showPushModal() {
  const modal = document.getElementById('push-modal');
  if (modal) modal.style.display = 'flex';
}

function hidePushModal() {
  const modal = document.getElementById('push-modal');
  if (modal) modal.style.display = 'none';
}

async function pushToDevice() {
  showPushModal();
  setStageActive('stage1');
  const bar = document.getElementById('push-progress-bar');
  if (bar) bar.style.width = '10%';

  await new Promise(r => setTimeout(r, 800));
  setStageActive('stage2');
  if (bar) bar.style.width = '40%';

  await new Promise(r => setTimeout(r, 800));
  setStageActive('stage3');
  if (bar) bar.style.width = '75%';

  try {
    await fetch('/api/push', { method: 'POST' });
    await new Promise(r => setTimeout(r, 800));
    if (bar) bar.style.width = '100%';
  } catch (e) {
    console.error(e);
  }

  await new Promise(r => setTimeout(r, 800));
  hidePushModal();
  if (bar) bar.style.width = '0%';
  fetchConfig();
}

document.addEventListener('DOMContentLoaded', () => {
  fetchConfig();
});
