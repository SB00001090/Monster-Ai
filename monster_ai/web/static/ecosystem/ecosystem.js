const API = "/api/ecosystem";
const CONSENT_KEY = "monster_ecosystem_consent_v1";
let selectedBundle = "full";
let pollTimer = null;

async function apiGet(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function $(id) {
  return document.getElementById(id);
}

function renderBundles(bundles) {
  const grid = $("bundleGrid");
  grid.innerHTML = "";
  bundles.forEach((b) => {
    const card = document.createElement("div");
    card.className = "bundle-card" + (b.id === selectedBundle ? " selected" : "");
    card.dataset.id = b.id;
    card.innerHTML = `
      <div class="label">${b.label || b.id}</div>
      <div class="meta">~${b.estimated_minutes || "?"} 分鐘 · ${b.step_count || 0} 步驟</div>
    `;
    card.addEventListener("click", () => {
      selectedBundle = b.id;
      renderBundles(bundles);
    });
    grid.appendChild(card);
  });
}

function renderStatus(st) {
  const pct = st.progress_pct ?? 0;
  $("progressBar").style.width = pct + "%";
  $("progressPct").textContent = pct.toFixed(1) + "%";
  $("currentStep").textContent = st.running
    ? `執行中: ${st.current_step || "…"}`
    : st.bundle_id
      ? `完成: ${st.bundle_id}`
      : "待機";
  const lines = (st.log || []).map((e) => {
    const mark = e.ok ? "✓" : "✗";
    return `${mark} ${e.step}: ${(e.detail || "").slice(0, 80)}`;
  });
  if (st.errors?.length) {
    lines.push("--- 錯誤 ---", ...st.errors.slice(-5));
  }
  $("installLog").textContent = lines.join("\n") || "尚無日誌";
}

function renderInfo(info) {
  const c = info.consent || {};
  const st = info.status || {};
  $("statusBox").textContent = [
    `產品: ${info.product || "Monster AI"}`,
    `開發者: ${info.developer || "Suckbob"}`,
    `同意狀態: ${c.consented ? "已同意" : "未同意"}`,
    `R18+: ${c.allow_r18 ? "允許" : "禁止"}`,
    `下載: ${c.allow_downloads ? "允許" : "禁止"}`,
    `安裝中: ${st.running ? "是" : "否"}`,
    `Bundle: ${st.bundle_id || "—"}`,
    `進度: ${st.completed_steps || 0}/${st.total_steps || 0}`,
  ].join("\n");
  renderStatus(st);
}

async function refresh() {
  const info = await apiGet("/info");
  renderInfo(info);
  if (info.status?.running) {
    startPoll();
  }
}

function startPoll() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    try {
      const st = await apiGet("/status");
      renderStatus(st);
      if (!st.running) {
        clearInterval(pollTimer);
        pollTimer = null;
        await refresh();
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
}

async function grantConsent() {
  await apiPost("/consent", {
    grant: true,
    allow_r18: $("agreeR18").checked,
    allow_downloads: $("agreeDownloads").checked,
  });
  localStorage.setItem(CONSENT_KEY, "1");
  $("consentModal").classList.add("hidden");
}

async function startInstall(bundle) {
  const result = await apiPost("/install", { bundle });
  renderStatus(result.status || {});
  startPoll();
}

function setupConsentModal() {
  const terms = $("agreeTerms");
  const btn = $("btnConsent");
  terms.addEventListener("change", () => {
    btn.disabled = !terms.checked;
  });
  btn.addEventListener("click", () => grantConsent().catch(alert));

  apiGet("/privacy?locale=zh-TW")
    .then((d) => {
      $("privacyText").textContent = d.text || "";
    })
    .catch(() => {});

  if (localStorage.getItem(CONSENT_KEY)) {
    apiGet("/info")
      .then((info) => {
        if (info.consent?.consented) {
          $("consentModal").classList.add("hidden");
        }
      })
      .catch(() => {});
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupConsentModal();

  $("btnInstallFull").addEventListener("click", async () => {
    try {
      const info = await apiGet("/info");
      if (!info.consent?.consented) {
        $("consentModal").classList.remove("hidden");
        return;
      }
      await startInstall(selectedBundle);
    } catch (e) {
      alert(e.message || e);
    }
  });

  $("btnStop").addEventListener("click", () => {
    apiPost("/stop").then(refresh).catch(alert);
  });

  $("btnRefresh").addEventListener("click", () => refresh().catch(alert));

  apiGet("/bundles")
    .then((d) => renderBundles(d.bundles || []))
    .catch(() => {});

  refresh().catch((e) => {
    $("statusBox").textContent = "無法連接 API: " + e.message;
  });
});