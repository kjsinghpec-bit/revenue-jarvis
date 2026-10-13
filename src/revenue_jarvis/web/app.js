// Revenue Jarvis front-end. No build step, no external CDN: works offline on localhost.
const $ = (id) => document.getElementById(id);
const COLORS = { idle: [59, 232, 255], listening: [77, 255, 166], thinking: [255, 181, 71], speaking: [120, 200, 255], error: [255, 93, 108] };
let mode = "idle", level = 0, voiceOn = true, status = null, lastEvidence = [];

// ---------------- Arc reactor orb ----------------
function drawOrb(canvas, t, m, lvl) {
  const c = canvas.getContext("2d"), W = canvas.width, H = canvas.height, cx = W / 2, cy = H / 2, R = W * 0.42;
  const [r, g, b] = COLORS[m] || COLORS.idle, col = (a) => `rgba(${r},${g},${b},${a})`;
  c.clearRect(0, 0, W, H);
  const pulse = m === "speaking" ? 0.08 * Math.sin(t / 90) + lvl * 0.25 : m === "listening" ? lvl * 0.35 : m === "thinking" ? 0.05 * Math.sin(t / 160) : 0.03 * Math.sin(t / 700);
  // glow
  const grd = c.createRadialGradient(cx, cy, 0, cx, cy, R * (0.55 + pulse));
  grd.addColorStop(0, col(0.95)); grd.addColorStop(0.25, col(0.55)); grd.addColorStop(1, col(0));
  c.fillStyle = grd; c.beginPath(); c.arc(cx, cy, R * (0.6 + pulse), 0, 7); c.fill();
  // core
  c.fillStyle = "rgba(230,252,255,.95)"; c.beginPath(); c.arc(cx, cy, R * (0.12 + pulse * 0.4), 0, 7); c.fill();
  c.lineWidth = 2;
  // rings
  const rings = [[0.30, 0.0009, 10, 0.55], [0.48, -0.0006, 24, 0.45], [0.66, 0.0004, 3, 0.35], [0.86, -0.00025, 60, 0.25]];
  rings.forEach(([rr, sp, seg, a], k) => {
    const speed = m === "thinking" ? sp * 5 : sp;
    for (let i = 0; i < seg; i++) {
      const a0 = (i / seg) * Math.PI * 2 + t * speed, len = (Math.PI * 2 / seg) * (k === 2 ? 0.8 : 0.55);
      c.strokeStyle = col(a + (m !== "idle" ? 0.2 : 0)); c.beginPath(); c.arc(cx, cy, R * rr, a0, a0 + len); c.stroke();
    }
  });
  // waveform ring
  c.strokeStyle = col(0.7); c.beginPath();
  for (let i = 0; i <= 180; i++) {
    const a = (i / 180) * Math.PI * 2, n = Math.sin(a * 8 + t / 120) * Math.sin(a * 3 - t / 300);
    const rr = R * (0.76 + (m === "idle" ? 0.006 : 0.03 + lvl * 0.12) * n);
    const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr; i ? c.lineTo(x, y) : c.moveTo(x, y);
  }
  c.stroke();
  // ticks
  for (let i = 0; i < 72; i++) {
    const a = (i / 72) * Math.PI * 2, r1 = R * 0.95, r2 = R * (i % 6 ? 0.98 : 1.02);
    c.strokeStyle = col(i % 6 ? 0.25 : 0.6); c.beginPath(); c.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); c.lineTo(cx + Math.cos(a) * r2, cy + Math.sin(a) * r2); c.stroke();
  }
}
function loop(t) { level *= 0.92; drawOrb($("orb"), t, mode, level); requestAnimationFrame(loop); }
function setMode(m, label) { mode = m; $("state").textContent = label || { idle: "STANDBY", listening: "LISTENING", thinking: "ANALYSING SOURCES", speaking: "SPEAKING", error: "FAULT" }[m]; }

// ---------------- Boot sequence ----------------
async function boot() {
  const log = $("bootLog"), lines = [];
  let raf; const spin = (t) => { drawOrb($("bootOrb"), t, "thinking", 0.2); raf = requestAnimationFrame(spin); }; raf = requestAnimationFrame(spin);
  const say = async (s, d = 260) => { lines.push("> " + s); log.textContent = lines.join("\n"); await new Promise((r) => setTimeout(r, d)); };
  await say("J.A.R.V.I.S. revenue core v1.0");
  try { status = await (await fetch("/api/status")).json(); } catch (e) { await say("knowledge base offline: " + e, 1500); }
  if (status) {
    await say(`Bhumbak corpus .......... ${status.book_pages_indexed} pages indexed`);
    await say(`Statutes & rules ........ ${status.laws.length} instruments`);
    await say(`Reasoning engine ........ ${status.backend}`);
    await say(`Voice ................... ${status.stt_engine} / system voice`);
    await say("All systems local. No data leaves this Mac except the question to your own subscription.", 500);
  }
  cancelAnimationFrame(raf);
  $("boot").style.opacity = 0; setTimeout(() => $("boot").remove(), 800);
  renderStatus(); greet();
}
function greet() {
  const h = new Date().getHours(), part = h < 12 ? "morning" : h < 17 ? "afternoon" : "evening", title = status?.title || "sir";
  const text = `Good ${part}, ${title}. Your revenue library is ready. Ask me about partition, consolidation, mutations or village common land.`;
  addJarvis({ spoken: text, claims: [], law_support: [], conflicts: [], evidence: [], warnings: [], status: "greeting", language: "en" });
  speak(text, "en");
}

// ---------------- Panels ----------------
function renderStatus() {
  if (!status) return;
  const pct = Math.round((100 * status.book_pages_indexed) / Math.max(1, status.book_pages));
  $("chips").innerHTML = [
    `BOOK ${status.book_pages_indexed}/${status.book_pages} PAGES`, `${status.laws.length} ACTS & RULES`, `ENGINE: ${status.backend.toUpperCase()}`, status.restart_required ? "RESTART REQUIRED" : "LOCAL · 127.0.0.1",
  ].map((s, i) => `<span class="chip ${i === 2 && status.backend === "sources-only" ? "warn" : ""}">${s}</span>`).join("");
  $("library").innerHTML = `<div class="lib-item"><b>Zameen Di Guide</b> — S. L. Bhumbak<span class="tag">PRIMARY</span>
      <div class="bar"><i style="width:${pct}%"></i></div><span class="muted">${pct}% of pages searchable · ${status.book_pages_scan_verified || 0} pages verified against scans. Searchable text may contain OCR errors.</span></div>` +
    status.laws.map((l) => `<div class="lib-item">${l.short_name || l.title}<span class="tag">${l.jurisdiction === "Central" ? "CENTRAL" : "PUNJAB"}${l.complete ? "" : " · PART"}</span></div>`).join("");
  refreshHistory();
  $("send").disabled = !!status.restart_required;
  if (status.restart_required) setMode("error", "RESTART JARVIS TO LOAD UPDATES");
}
async function refreshHistory() {
  try {
    const h = await (await fetch("/api/history?limit=12")).json();
    $("history").innerHTML = h.map((r) => `<li title="${r.ts}">${esc(r.question).slice(0, 70)}</li>`).join("");
    [...$("history").children].forEach((li, i) => (li.onclick = () => { $("q").value = h[i].question; $("q").focus(); }));
  } catch (_) {}
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function ocrLabel(e) {
  if (e.source_type !== "book") return "";
  return e.scan_verified ? "Text verified against scan · legal applicability still needs checking" :
    e.ocr_status === "needs_review" ? "OCR needs review · check numbers and officer powers against the scan" :
    "OCR extracted · unverified against scan";
}
function citeChips(ids, evidence = []) {
  return ids.map((i) => {
    const e = evidence.find((e) => e.sid === i);
    const scan = e?.source_type === "book" ? `<button type="button" class="cite scan" data-sid="${esc(i)}" title="${esc(ocrLabel(e))}">Compare scan p.${esc(e.pdf_page)}</button>` : "";
    return `<span class="cite ${i[0] === "L" ? "law" : ""}" data-sid="${esc(i)}">${esc(i)}</span>${scan}`;
  }).join("");
}
function addUser(text) { const d = document.createElement("div"); d.className = "msg user"; d.innerHTML = `<span class="who">YOU</span>${esc(text)}`; $("transcript").append(d); scrollDown(); }
function addJarvis(a) {
  const d = document.createElement("div"); d.className = "msg jarvis";
  d.dataset.answerId = a.answer_id || "";
  const answerEvidence = a.evidence || [];
  const list = (label, items, cls = "") => items?.length ? `<div class="sec-label">${label}</div><ul>${items.map((c) => `<li class="${cls}">${esc(c.text)} ${citeChips(c.source_ids, answerEvidence)}</li>`).join("")}</ul>` : "";
  let html = `<span class="who">JARVIS</span><div class="spoken">${esc(a.spoken)}</div>`;
  html += list("FROM THE BOOK", a.claims) + list("STATUTORY SUPPORT", a.law_support) + list("ACT vs BOOK", a.conflicts, "conflict");
  if (a.missing_facts?.length) html += `<div class="sec-label">FACTS I NEED</div><ul>${a.missing_facts.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>`;
  if (["sources_only", "not_found", "insufficient"].includes(a.status) && a.evidence?.length)
    html += `<div class="sec-label">MOST RELEVANT PAGES</div><ul>${a.evidence.map((e) => `<li>${esc(e.citation)} ${citeChips([e.sid], answerEvidence)}</li>`).join("")}</ul>`;
  (a.caveats || []).concat(a.warnings || []).forEach((w) => (html += `<div class="warnline">⚠ ${esc(w)}</div>`));
  d.innerHTML = html; $("transcript").append(d);
  d.querySelectorAll(".cite").forEach((el) => (el.onclick = () => openEvidence(el.dataset.sid, answerEvidence)));
  scrollDown();
}
function scrollDown() { const t = $("transcript"); t.scrollTop = t.scrollHeight; }
function renderEvidence(evs) {
  lastEvidence = evs || [];
  $("evidence").innerHTML = lastEvidence.length ? "" : '<p class="muted">No sources.</p>';
  lastEvidence.forEach((e, i) => {
    const c = document.createElement("div"); c.className = "card " + e.source_type; c.style.animationDelay = i * 70 + "ms";
    c.innerHTML = `<div class="hdr"><span>${esc(e.sid)} · ${e.source_type === "book" ? "BOOK" : "LAW"}</span><span>${esc(e.citation)}</span></div>` +
      (e.source_type === "book" ? `<div class="ocr-label ${e.scan_verified ? "reviewed" : "warnline"}">${esc(ocrLabel(e))} · Click to compare scan</div>` : "") + `<div class="body">${esc(e.text)}</div>`;
    c.onclick = () => openEvidence(e.sid, evs); $("evidence").append(c);
  });
}
async function openEvidence(sid, evidence = lastEvidence) {
  const e = evidence.find((x) => x.sid === sid); if (!e) return;
  $("modalTitle").textContent = `${e.sid} ${e.citation}`;
  $("modalReview").textContent = ocrLabel(e);
  $("modalText").textContent = e.text + (e.neighbors ? "\n\n— continues —\n" + e.neighbors : "");
  const img = $("modalImg");
  img.removeAttribute("src");
  img.onerror = () => { img.style.display = "none"; $("modalReview").textContent = "Original scan unavailable. The extracted text remains unverified unless separately reviewed."; };
  if (e.source_type === "book" && status?.page_images) { img.style.display = ""; img.src = `/api/page/${e.pdf_page}.png`; }
  else {
    img.style.display = "none";
    if (e.source_type === "book") $("modalReview").textContent += " · Original PDF unavailable; configure JARVIS_BOOK_PDF with the indexed original.";
  }
  $("modal").classList.remove("hidden");
}
$("closeModal").onclick = () => $("modal").classList.add("hidden");
$("modal").onclick = (ev) => { if (ev.target.id === "modal") $("modal").classList.add("hidden"); };

// ---------------- Ask ----------------
async function ask(text) {
  text = (text || "").trim(); if (!text) return;
  if (status?.restart_required) {
    setMode("error", "RESTART JARVIS TO LOAD UPDATES");
    return;
  }
  addUser(text); $("q").value = ""; setMode("thinking"); stopSpeaking();
  try {
    const started = performance.now();
    const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text }) });
    if (!r.ok) throw new Error(await r.text());
    const a = await r.json();
    renderEvidence(a.evidence); addJarvis(a); refreshHistory();
    console.info("Jarvis timing (ms)", { ...a.timings, browser_to_render: performance.now() - started, answer_id: a.answer_id });
    speak(a.spoken, a.language);
  } catch (e) { setMode("error"); addJarvis({ spoken: "Sir, something failed: " + e.message, evidence: [], warnings: [] }); setTimeout(() => setMode("idle"), 2500); }
}
$("send").onclick = () => ask($("q").value);
$("q").addEventListener("keydown", (e) => { if (e.key === "Enter") ask($("q").value); });
$("voiceToggle").onclick = () => { voiceOn = !voiceOn; $("voiceToggle").classList.toggle("on", voiceOn); if (!voiceOn) stopSpeaking(); };

// ---------------- Speech out ----------------
function pickVoice(lang) {
  const vs = speechSynthesis.getVoices(), want = { en: ["en-GB", "en-IN", "en"], hinglish: ["en-IN", "en-GB"], hi: ["hi-IN"], pa: ["pa-IN", "pa"] }[lang] || ["en-GB"];
  for (const w of want) {
    const pref = vs.find((v) => v.lang.startsWith(w) && /Daniel|Arthur|Rishi|Lekha|Google/i.test(v.name)) || vs.find((v) => v.lang.startsWith(w));
    if (pref) return pref;
  }
  return null;
}
let useNeural = true, currentAudio = null;
async function speak(text, lang) {
  if (!voiceOn || !text) { setMode("idle"); return; }
  if (useNeural) {   // free neural voice from the local server (British "Ryan" for English, Hindi/Punjabi voices)
    try {
      const r = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang }) });
      if (r.ok) {
        const au = new Audio(URL.createObjectURL(await r.blob())); currentAudio = au; setMode("speaking");
        const iv = setInterval(() => (level = 0.3 + Math.random() * 0.5), 110);
        au.onended = () => { clearInterval(iv); setMode("idle"); }; await au.play(); return;
      }
      if (r.status === 503) useNeural = false;   // offline: stop trying, use the system voice
    } catch (_) { useNeural = false; }
  }
  const v = pickVoice(lang);
  const u = new SpeechSynthesisUtterance(text); if (v) { u.voice = v; u.lang = v.lang; }
  u.rate = 1.0; u.pitch = 0.95;
  u.onstart = () => setMode("speaking"); u.onend = () => setMode("idle"); u.onboundary = () => (level = 0.6 + Math.random() * 0.4);
  speechSynthesis.speak(u);
}
function stopSpeaking() { speechSynthesis.cancel(); if (currentAudio) { currentAudio.pause(); currentAudio = null; } }
speechSynthesis?.addEventListener?.("voiceschanged", () => {});

// ---------------- Speech in ----------------
let rec = null, chunks = [], stream = null, analyser = null, recording = false;
async function startRec() {
  if (recording) return; recording = true; stopSpeaking();
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const ctx = new AudioContext(), src = ctx.createMediaStreamSource(stream); analyser = ctx.createAnalyser(); src.connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    const meter = () => { if (!recording) return; analyser.getByteTimeDomainData(buf); let m = 0; for (const x of buf) m = Math.max(m, Math.abs(x - 128)); level = Math.min(1, m / 60); requestAnimationFrame(meter); };
    rec = new MediaRecorder(stream); chunks = []; rec.ondataavailable = (e) => chunks.push(e.data); rec.start(); meter();
    setMode("listening"); $("mic").classList.add("live");
  } catch (e) { recording = false; addJarvis({ spoken: "Sir, I can't access the microphone: " + e.message, evidence: [], warnings: [] }); }
}
async function stopRec() {
  if (!recording || !rec) return; recording = false; $("mic").classList.remove("live");
  await new Promise((r) => { rec.onstop = r; rec.stop(); }); stream.getTracks().forEach((t) => t.stop());
  setMode("thinking", "TRANSCRIBING");
  const fd = new FormData(); fd.append("audio", new Blob(chunks, { type: "audio/webm" }), "speech.webm");
  try {
    const r = await fetch("/api/transcribe", { method: "POST", body: fd });
    if (r.status === 501) return browserSTT();
    if (!r.ok) throw new Error(await r.text());
    const { text } = await r.json(); if (text) ask(text); else setMode("idle");
  } catch (e) { setMode("idle"); addJarvis({ spoken: "Sir, I didn't catch that. " + e.message, evidence: [], warnings: [] }); }
}
function browserSTT() {     // fallback: the browser's own recogniser (Chrome/Safari), supports pa-IN and hi-IN
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SR) { setMode("idle"); return; }
  const r = new SR(), l = $("lang").value; r.lang = { pa: "pa-IN", hi: "hi-IN", en: "en-IN" }[l] || "en-IN";
  setMode("listening", "LISTENING (BROWSER)"); r.onresult = (e) => ask(e.results[0][0].transcript); r.onend = () => mode === "listening" && setMode("idle"); r.start();
}
$("mic").onmousedown = startRec; $("mic").onmouseup = stopRec; $("mic").onmouseleave = () => recording && stopRec();
document.addEventListener("keydown", (e) => { if (e.code === "Space" && document.activeElement !== $("q") && !e.repeat) { e.preventDefault(); startRec(); } if (e.key === "Escape") { stopSpeaking(); setMode("idle"); } });
document.addEventListener("keyup", (e) => { if (e.code === "Space" && document.activeElement !== $("q")) { e.preventDefault(); stopRec(); } });

setInterval(() => ($("clock").textContent = new Date().toLocaleString("en-IN", { weekday: "short", hour: "2-digit", minute: "2-digit" })), 1000);
requestAnimationFrame(loop); boot();
setInterval(async () => {
  if (mode === "thinking" || mode === "listening" || mode === "speaking") return;
  try {
    const next = await (await fetch("/api/status")).json();
    if (next.restart_required !== status?.restart_required) { status = next; renderStatus(); }
  } catch (_) {}
}, 15000);
