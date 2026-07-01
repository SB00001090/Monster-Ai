const API = "/api/mini";
const AGREE_KEY = "mini_monster_disclaimer_v1";

async function jget(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function jpost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

function showImage(res) {
  const img = document.getElementById("preview");
  const src = res.url || res.path;
  if (!src) return;
  img.src = src.startsWith("http") ? src : (src.startsWith("/") ? src : "/" + src.replace(/^\.?\//, ""));
  img.classList.remove("hidden");
}

function fillRefSelects(refs) {
  for (const id of ["referenceId", "mmRef", "voiceRef"]) {
    const sel = document.getElementById(id);
    const cur = sel.value;
    sel.innerHTML = '<option value="">— 選擇 —</option>';
    refs.forEach((r) => {
      const o = document.createElement("option");
      o.value = r.id;
      o.textContent = `${r.name} (${r.id.slice(0, 6)})`;
      sel.appendChild(o);
    });
    if (cur) sel.value = cur;
  }
}

async function refreshSuccess() {
  const s = await jget("/success");
  const pct = ((s.success_rate || 0) * 100).toFixed(1);
  const sim = s.avg_likeness_similarity != null ? (s.avg_likeness_similarity * 100).toFixed(1) : "—";
  setStatus(
    `圖像成功率 ${pct}% / 目標 98%\n` +
      `Likeness 相似度 ${sim}% / 目標 98%\n` +
      `記錄 ${s.total_recorded || 0} · 截止 ${s.target_deadline || "2026-09-01"}`
  );
}

async function loadInfo() {
  const info = await jget("/info");
  fillRefSelects(info.references || []);
  document.getElementById("network").textContent = JSON.stringify(info.network, null, 2);
  const tplSel = document.getElementById("template");
  const def = info.default_template || "stable";
  if (tplSel && info.templates?.length) {
    const cur = tplSel.value;
    tplSel.innerHTML = "";
    info.templates.forEach((t) => {
      const o = document.createElement("option");
      o.value = t.id;
      o.textContent = t.label_zh || t.label;
      if (t.id === def) o.selected = true;
      tplSel.appendChild(o);
    });
    if (cur) tplSel.value = cur;
  }
}

// Tabs
document.querySelectorAll(".tab").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.dataset.tab;
    if (id === "network") document.getElementById("panel-network").classList.add("active");
    else document.getElementById(`panel-${id}`).classList.add("active");
  };
});

// Disclaimer
(async function initDisclaimer() {
  const d = await jget("/disclaimer?locale=zh-TW");
  document.getElementById("disclaimerText").textContent = d.text;
  if (localStorage.getItem(AGREE_KEY) === "1") {
    document.getElementById("disclaimerModal").classList.add("hidden");
    return;
  }
  const chk = document.getElementById("agreeCheck");
  const btn = document.getElementById("btnAgree");
  chk.onchange = () => { btn.disabled = !chk.checked; };
  btn.onclick = () => {
    localStorage.setItem(AGREE_KEY, "1");
    document.getElementById("disclaimerModal").classList.add("hidden");
  };
})();

document.getElementById("simScore").oninput = (e) => {
  document.getElementById("simLabel").textContent = (e.target.value / 100).toFixed(2);
};

document.getElementById("btnOptimize").onclick = async () => {
  const res = await jpost("/optimize", {
    prompt: document.getElementById("prompt").value.trim(),
    locale: document.getElementById("locale").value,
  });
  document.getElementById("optimized").textContent = res.optimized || "";
};

document.getElementById("btnGenerate").onclick = async () => {
  setStatus("生成中…");
  const res = await jpost("/generate", {
    prompt: document.getElementById("prompt").value.trim(),
    template_id: document.getElementById("template").value,
    locale: document.getElementById("locale").value,
  });
  showImage(res);
  await refreshSuccess();
};

document.getElementById("btnUploadRef").onclick = async () => {
  const img = document.getElementById("refImage").files[0];
  if (!img) return alert("請選擇參考臉圖");
  const fd = new FormData();
  fd.append("name", document.getElementById("refName").value || "character");
  fd.append("image", img);
  const voice = document.getElementById("refVoice").files[0];
  if (voice) fd.append("voice", voice);
  const r = await fetch(API + "/reference/upload", { method: "POST", body: fd });
  if (!r.ok) return alert(await r.text());
  const res = await r.json();
  await loadInfo();
  document.getElementById("referenceId").value = res.reference_id;
  alert(`參考已上傳: ${res.reference_id}`);
};

document.getElementById("btnLikeness").onclick = async () => {
  const ref = document.getElementById("referenceId").value;
  if (!ref) return alert("請先上傳參考");
  setStatus("Likeness 生成中…");
  const res = await jpost("/generate/likeness", {
    prompt: document.getElementById("likenessPrompt").value.trim(),
    reference_id: ref,
    template_id: "idol_likeness",
    locale: document.getElementById("locale").value,
  });
  showImage(res);
  await refreshSuccess();
};

document.getElementById("btnMultimodal").onclick = async () => {
  const ref = document.getElementById("mmRef").value;
  if (!ref) return alert("請選擇參考");
  setStatus("多模態生成中…");
  const res = await jpost("/generate/multimodal", {
    prompt: document.getElementById("mmPrompt").value.trim(),
    reference_id: ref,
    voice_text: document.getElementById("mmVoiceText").value.trim() || null,
    template_id: "idol_likeness",
  });
  if (res.image) showImage(res.image);
  if (res.voice && res.voice.url) {
    const a = document.getElementById("audioPreview");
    a.src = res.voice.url;
    a.classList.remove("hidden");
  }
  await refreshSuccess();
};

document.getElementById("btnVoice").onclick = async () => {
  const ref = document.getElementById("voiceRef").value;
  if (!ref) return alert("請選擇參考");
  const res = await jpost("/voice/clone", {
    text: document.getElementById("voiceText").value.trim(),
    reference_id: ref,
  });
  const a = document.getElementById("voicePreview");
  a.src = res.url;
  a.classList.remove("hidden");
};

async function sendFeedback(ok) {
  const sim = document.getElementById("simScore").value / 100;
  const tpl = document.getElementById("template").value || "idol_likeness";
  await jpost("/feedback", { ok, template_id: tpl, similarity_score: sim });
  await refreshSuccess();
}

document.getElementById("btnGood").onclick = () => sendFeedback(true);
document.getElementById("btnBad").onclick = () => sendFeedback(false);

document.getElementById("btnConsent").onclick = async () => {
  const res = await jpost("/network/consent", { grant: true, downloads: false, metrics: true });
  document.getElementById("network").textContent = JSON.stringify(res, null, 2);
};

document.getElementById("btnRevoke").onclick = async () => {
  const res = await jpost("/network/consent", { grant: false });
  document.getElementById("network").textContent = JSON.stringify(res, null, 2);
};

refreshSuccess().catch((e) => setStatus(String(e)));
loadInfo().catch(() => {});