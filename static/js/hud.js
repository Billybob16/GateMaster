/* ---------------------------------------------------------
   FETCH JSON CONFIG FOR PREVIEW
--------------------------------------------------------- */
async function fetchConfig() {
  try {
    const res = await fetch('/debug');
    const text = await res.text();
    const pre = document.getElementById('rtu-json-preview');
    if (pre) {
      pre.textContent = text;
    }
  } catch (e) {
    console.error("Error fetching config:", e);
  }
}


/* ---------------------------------------------------------
   CINEMATIC PUSH SEQUENCE
--------------------------------------------------------- */
function setStageActive(stageId) {
  const stages = ['stage1', 'stage2', 'stage3'];
  stages.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.toggle('active', id === stageId);
    }
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

  const bar = document.getElementById('push-progress-bar');

  // Stage 1 — Connecting
  setStageActive('stage1');
  if (bar) bar.style.width = '15%';
  await new Promise(r => setTimeout(r, 900));

  // Stage 2 — Authenticating
  setStageActive('stage2');
  if (bar) bar.style.width = '45%';
  await new Promise(r => setTimeout(r, 900));

  // Stage 3 — Uploading
  setStageActive('stage3');
  if (bar) bar.style.width = '75%';
  await new Promise(r => setTimeout(r, 900));

  // Send simulated push
  try {
    await fetch('/api/push', { method: 'POST' });
    if (bar) bar.style.width = '100%';
  } catch (e) {
    console.error("Push failed:", e);
  }

  // Finish sequence
  await new Promise(r => setTimeout(r, 900));
  hidePushModal();

  // Reset bar
  if (bar) bar.style.width = '0%';

  // Refresh JSON preview
  fetchConfig();
}


/* ---------------------------------------------------------
   AUTO-LOAD JSON PREVIEW ON PAGE LOAD
--------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  fetchConfig();
});
