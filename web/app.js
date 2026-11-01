/* Dukaan Saathi UI: photo->draft->confirm, chat/voice, approvals. No build step. */
"use strict";
const $ = (id) => document.getElementById(id);

// UI language: the #lang dropdown drives reply language + page chrome.
// Auto = Hindi chrome, agent auto-detects each message.
const I18N = {
  hi: { subtitle: "Photo → confirm → hisaab. Kuch bhi bina approval save nahi hota.",
    tab1: "📷 Bahi Photo", tab2: "🎤 Sawal", tab3: "📒 Hisaab",
    photo_label: "1. Bahi-khaate ki photo lein", extract_btn: "2. Padho (Extract)",
    draft_title: "3. Check karke sudhaarein, phir Confirm",
    th_customer: "Grahak", th_desc: "Vivaran", th_kind: "Udhaar/Vapsi",
    commit_btn: "4. Confirm & Save", ask_title: "Bolo ya likho",
    ask_hint: 'Jaise: "sabse zyada udhaar kiska hai?" ya "500 se zyada walon ko reminder banao"',
    ask_ph: "Apna sawal likhein…", ask_btn: "Poocho",
    bal_title: "Udhaar Hisaab", rem_title: "Reminder Drafts (approval chahiye)",
    week_title: "Hafte ka Summary", ans_ph: "Jawab yahan aayega…",
    no_bal: "Koi udhaar nahi.", no_rem: "Koi draft nahi.", approve: "Approve",
    total: "Kul udhaar baki", times: "baar", heard: "Suna: ",
    kind_credit: "Udhaar", kind_payment: "Vapsi" },
  te: { subtitle: "ఫోటో → confirm → లెక్క. Approval లేకుండా ఏమీ save అవ్వదు.",
    tab1: "📷 ఖాతా ఫోటో", tab2: "🎤 ప్రశ్న", tab3: "📒 లెక్క",
    photo_label: "1. ఖాతా పుస్తకం ఫోటో తీయండి", extract_btn: "2. చదవండి (Extract)",
    draft_title: "3. సరిచూసి, దిద్ది, Confirm చేయండి",
    th_customer: "కస్టమర్", th_desc: "వివరాలు", th_kind: "అప్పు/చెల్లింపు",
    commit_btn: "4. Confirm చేసి Save చేయండి", ask_title: "మాట్లాడండి లేదా రాయండి",
    ask_hint: 'ఉదా: "ఎవరికి ఎక్కువ అప్పు ఉంది?" లేదా "500 కంటే ఎక్కువ ఉన్నవారికి రిమైండర్ చేయండి"',
    ask_ph: "మీ ప్రశ్న రాయండి…", ask_btn: "అడగండి",
    bal_title: "అప్పుల లెక్క", rem_title: "రిమైండర్ డ్రాఫ్ట్‌లు (approval కావాలి)",
    week_title: "వారం సారాంశం", ans_ph: "సమాధానం ఇక్కడ వస్తుంది…",
    no_bal: "అప్పు ఏమీ లేదు.", no_rem: "డ్రాఫ్ట్‌లు లేవు.", approve: "Approve",
    total: "మొత్తం అప్పు", times: "సార్లు", heard: "విన్నది: ",
    kind_credit: "అప్పు", kind_payment: "చెల్లింపు" },
  en: { subtitle: "Photo → confirm → accounts. Nothing saves without approval.",
    tab1: "📷 Ledger Photo", tab2: "🎤 Ask", tab3: "📒 Accounts",
    photo_label: "1. Take a photo of the ledger page", extract_btn: "2. Read (Extract)",
    draft_title: "3. Review, correct, then Confirm",
    th_customer: "Customer", th_desc: "Details", th_kind: "Credit/Payment",
    commit_btn: "4. Confirm & Save", ask_title: "Speak or type",
    ask_hint: 'E.g.: "who owes me the most?" or "remind everyone owing over 500"',
    ask_ph: "Type your question…", ask_btn: "Ask",
    bal_title: "Outstanding balances", rem_title: "Reminder drafts (need approval)",
    week_title: "Weekly summary", ans_ph: "The answer appears here…",
    no_bal: "Nobody owes anything.", no_rem: "No drafts.", approve: "Approve",
    total: "Total outstanding", times: "times", heard: "Heard: ",
    kind_credit: "Credit", kind_payment: "Payment" },
};
let chromeLang = "hi";
const t = (k) => (I18N[chromeLang] && I18N[chromeLang][k]) || I18N.hi[k] || k;
function setChrome(lang) {
  chromeLang = I18N[lang] ? lang : "hi";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  if ($("answer").textContent.endsWith("…") || $("answer").textContent.endsWith("..."))
    $("answer").textContent = t("ans_ph");
  if (draft.length) renderDraft();
  if (!$("s3").hidden) refreshHisaab();
}
$("lang").onchange = () => setChrome($("lang").value === "auto" ? "hi" : $("lang").value);

// Tabs
[["t1", "s1"], ["t2", "s2"], ["t3", "s3"]].forEach(([t, s]) => {
  $(t).onclick = () => {
    ["t1", "t2", "t3"].forEach((x) => $(x).setAttribute("aria-selected", "false"));
    ["s1", "s2", "s3"].forEach((x) => ($(x).hidden = true));
    $(t).setAttribute("aria-selected", "true");
    $(s).hidden = false;
    if (s === "s3") refreshHisaab();
  };
});

// --- Photo -> draft -> confirm ---
let draft = [];
$("photo").onchange = (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const img = $("preview");
  img.src = URL.createObjectURL(f);
  img.style.display = "block";
};
$("extractBtn").onclick = async () => {
  const f = $("photo").files[0];
  if (!f) { $("exStatus").textContent = "Pehle photo chunein."; return; }
  $("extractBtn").disabled = true;
  $("exStatus").textContent = "Padh rahe hain…";
  try {
    const fd = new FormData();
    fd.append("photo", f);
    const r = await fetch("/api/ledger/extract", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    draft = (await r.json()).rows || [];
    renderDraft();
    $("draftCard").hidden = draft.length === 0;
    $("exStatus").textContent = draft.length + " panktiyan mili. Check karke Confirm dabayein.";
  } catch (e) {
    $("exStatus").innerHTML = '<span class="err">Error: ' + e.message + "</span>";
  } finally { $("extractBtn").disabled = false; }
};
function renderDraft() {
  $("draftRows").innerHTML = "";
  draft.forEach((r, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td><input value="${esc(r.customer)}" data-i="${i}" data-k="customer"></td>` +
      `<td><input value="${esc(r.description || "")}" data-i="${i}" data-k="description"></td>` +
      `<td><input type="number" value="${r.amount}" data-i="${i}" data-k="amount" style="width:80px"></td>` +
      `<td><select data-i="${i}" data-k="kind">
         <option value="credit"${r.kind === "credit" ? " selected" : ""}>${t("kind_credit")}</option>
         <option value="payment"${r.kind === "payment" ? " selected" : ""}>${t("kind_payment")}</option>
       </select></td>`;
    $("draftRows").appendChild(tr);
  });
  $("draftRows").querySelectorAll("input,select").forEach((el) => {
    el.onchange = () => {
      const i = +el.dataset.i, k = el.dataset.k;
      draft[i][k] = k === "amount" ? parseFloat(el.value) || 0 : el.value;
    };
  });
}
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;"); }
$("commitBtn").onclick = async () => {
  $("commitBtn").disabled = true;
  $("cmStatus").textContent = "Save ho raha hai…";
  try {
    const r = await fetch("/api/ledger/commit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows: draft }),
    });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    $("cmStatus").textContent = j.saved.length + " panktiyan save ho gayi. Hisaab tab me dekhein.";
    draft = [];
    $("draftCard").hidden = true;
  } catch (e) {
    $("cmStatus").innerHTML = '<span class="err">Error: ' + e.message + "</span>";
  } finally { $("commitBtn").disabled = false; }
};

// --- Chat + voice ---
const history = [];
$("askBtn").onclick = () => askText($("q").value.trim());
$("q").addEventListener("keydown", (e) => { if (e.key === "Enter") askText($("q").value.trim()); });
async function askText(msg) {
  if (!msg) return;
  $("askBtn").disabled = true;
  $("askStatus").textContent = "Soch rahe hain…";
  try {
    const r = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, history, language: $("lang").value }),
    });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    history.push({ role: "user", content: msg }, { role: "assistant", content: j.answer });
    $("answer").textContent = j.answer;
    $("askStatus").textContent = j.tool_calls?.length ? "Tools: " + j.tool_calls.map((t) => t.tool).join(", ") : "";
  } catch (e) {
    $("answer").innerHTML = '<span class="err">Error: ' + e.message + "</span>";
  } finally { $("askBtn").disabled = false; }
}
let rec = null, chunks = [];
$("micBtn").onclick = async () => {
  if (rec) { rec.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    rec = new MediaRecorder(stream);
    chunks = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = async () => {
      $("micBtn").classList.remove("live");
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
      rec = null;
      await askVoice(blob);
    };
    rec.start();
    $("micBtn").classList.add("live");
    $("askStatus").textContent = "Boliye… dobara dabane par rukega.";
  } catch (e) {
    $("askStatus").innerHTML = '<span class="err">Mic error: ' + e.message + "</span>";
  }
};
async function askVoice(blob) {
  $("askStatus").textContent = "Sun rahe hain…";
  try {
    const fd = new FormData();
    fd.append("audio", blob, "q.webm");
    fd.append("language", $("lang").value);
    const r = await fetch("/api/voice/ask", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    const j = await r.json();
    $("answer").textContent = t("heard") + j.transcript + "\n\n" + j.answer;
    $("askStatus").textContent = j.tool_calls?.length ? "Tools: " + j.tool_calls.map((t) => t.tool).join(", ") : "";
  } catch (e) {
    $("answer").innerHTML = '<span class="err">Error: ' + e.message + "</span>";
  }
}

// --- Hisaab tab ---
async function refreshHisaab() {
  try {
    const c = await (await fetch("/api/customers")).json();
    $("bals").innerHTML = c.customers.length
      ? c.customers.map((b) => `<div class="bal"><span>${esc(b.customer)}</span><span class="amt">₹${Math.round(b.balance)}</span></div>`).join("")
      : `<p class="hint">${esc(t("no_bal"))}</p>`;
  } catch { $("bals").textContent = "Load nahi hua."; }
  try {
    const m = await (await fetch("/api/reminders")).json();
    $("rems").innerHTML = m.reminders.length ? "" : `<p class="hint">${esc(t("no_rem"))}</p>`;
    m.reminders.forEach((d) => {
      const div = document.createElement("div");
      div.className = "draft";
      div.innerHTML = `<b>${esc(d.customer)}</b> [${esc(d.language)}] <i>${esc(d.status)}</i><br>${esc(d.draft_text)}`;
      if (d.status === "draft") {
        const b = document.createElement("button");
        b.textContent = t("approve");
        b.onclick = async () => {
          await fetch(`/api/reminders/${d.id}/approve`, { method: "POST" });
          refreshHisaab();
        };
        div.appendChild(document.createElement("br"));
        div.appendChild(b);
      }
      $("rems").appendChild(div);
    });
  } catch { $("rems").textContent = "Load nahi hua."; }
  try {
    const w = await (await fetch("/api/report/weekly")).json();
    $("weekly").innerHTML =
      `<div class="bal"><span>${esc(t("total"))}</span><span class="amt">₹${Math.round(w.total_outstanding)}</span></div>` +
      (w.top_items.map((it) => `<div class="bal"><span>${esc(it.item)}</span><span>${it.times} ${esc(t("times"))}</span></div>`).join("") || "");
  } catch { $("weekly").textContent = "Load nahi hua."; }
}
