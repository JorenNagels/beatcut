"""Step 8: build review.html (local page) from candidates.json + photos_best.json.
Each candidate: looping preview, category, score, reason, date, source file + in/out times,
keep/drop toggle and a must-have star. Choices persist in localStorage and export as selections.json."""
import json
from datetime import date
from common import ROOT, load_json, cfg

DAYNAMES = {str(k): v for k, v in (cfg("days") or {}).items()}          # event.yaml: date -> short description


def main():
    cands = load_json("candidates.json"); photos = load_json("photos_best.json")
    days = sorted({c["day"] for c in cands})
    meta = {d: {"label": date.fromisoformat(d).strftime("%a %d %b") if d != "unknown" else "Unknown day",
                "title": DAYNAMES.get(d, "")} for d in days}
    data = json.dumps({"cands": cands, "photos": photos, "days": meta}, ensure_ascii=False)
    html = TEMPLATE.replace("/*DATA*/", data)
    (ROOT / "review.html").write_text(html, encoding="utf-8")
    print("review.html written:", len(cands), "candidates,", len(photos), "photos")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ski Film Review</title>
<style>
:root{--bg:#0f1114;--card:#191c21;--line:#2a2f37;--fg:#e8eaed;--mut:#8b929c;--act:#ff7a45;--calm:#5cb8e6;--keep:#3ecf8e;--drop:#5a5f68;--star:#ffcc33}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:5;background:rgba(15,17,20,.94);backdrop-filter:blur(6px);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
h1{font-size:17px;margin:0 8px 0 0;letter-spacing:.02em}
.stats{color:var(--mut);font-variant-numeric:tabular-nums}.stats b{color:var(--fg)}
.filters{display:flex;gap:6px;flex-wrap:wrap}
button{font:inherit;color:var(--fg);background:#232830;border:1px solid var(--line);border-radius:7px;padding:5px 11px;cursor:pointer}
button:hover{border-color:#4a515c}button.on{background:#e8eaed;color:#111;border-color:#e8eaed}
#export{background:var(--keep);color:#06281a;border:0;font-weight:600;margin-left:auto}
main{padding:8px 20px 60px;max-width:1500px;margin:0 auto}
.day{margin-top:26px}.day h2{font-size:15px;margin:0 0 12px;display:flex;gap:10px;align-items:baseline}
.day h2 small{color:var(--mut);font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;transition:opacity .15s,border-color .15s}
.card.drop{opacity:.38}.card.star{border-color:var(--star);box-shadow:0 0 0 1px var(--star) inset}
.media{position:relative;background:#000;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center}
.media video,.media img{max-width:100%;max-height:100%;display:block}
.badge{position:absolute;top:8px;left:8px;font-size:11px;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:5px;color:#111}
.ACTION{background:var(--act)}.CALM{background:var(--calm)}
.cat{position:absolute;top:8px;right:8px;font-size:11px;background:rgba(0,0,0,.65);padding:2px 7px;border-radius:5px;text-transform:uppercase;letter-spacing:.05em}
.body{padding:10px 12px;display:flex;flex-direction:column;gap:5px;flex:1}
.reason{font-weight:500}.meta{color:var(--mut);font-size:12px;word-break:break-all}
.flags{display:flex;gap:5px;flex-wrap:wrap}.flag{font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:0 5px}
.row{display:flex;gap:8px;align-items:center;margin-top:auto;padding-top:6px}
.score{font-variant-numeric:tabular-nums;color:var(--mut);font-size:12px;margin-right:auto}
.score i{display:inline-block;height:5px;background:#3a414c;border-radius:3px;width:60px;vertical-align:middle;margin-left:6px;position:relative;overflow:hidden}
.score i b{position:absolute;inset:0 auto 0 0;background:var(--fg)}
.keep{min-width:72px}.keep.k{background:var(--keep);color:#06281a;border-color:var(--keep);font-weight:600}
.starbtn{font-size:16px;line-height:1;padding:4px 9px}.starbtn.s{background:var(--star);color:#111;border-color:var(--star)}
.note{width:100%;background:#12151a;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 7px;font:inherit;font-size:12px}
.hint{color:var(--mut);font-size:12px;margin:14px 0 0}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#e8eaed;color:#111;padding:8px 14px;border-radius:8px;opacity:0;transition:opacity .2s;pointer-events:none}
@media (max-width:600px){header,main{padding-left:14px;padding-right:14px}}
</style></head><body>
<header>
  <h1>Ski film: candidate review</h1>
  <span class="stats" id="stats"></span>
  <div class="filters" id="filters"></div>
  <button id="export" title="Download selections.json and save it into the ski-edit folder">Export selections.json</button>
</header>
<main id="main"></main>
<div id="toast"></div>
<script>
const D = /*DATA*/;
const KEY = "skiReview.v1";
let st = {};
try { st = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
const get = id => (st[id] ||= { keep: true, star: false, note: "" });
const fmt = s => { s = Math.round(s); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
let filter = "all";
const FILTERS = [["all","All"],["ACTION","Action"],["CALM","Calm"],["star","★ Must-have"],["kept","Kept"],["dropped","Dropped"],["photos","Photos"]];

function card(item, isPhoto) {
  const id = isPhoto ? "p:" + item.file : item.id, s = get(id);
  const el = document.createElement("div");
  el.className = "card" + (s.keep ? "" : " drop") + (s.star ? " star" : "");
  el.dataset.id = id; el.dataset.kind = isPhoto ? "PHOTO" : item.kind;
  const media = isPhoto
    ? `<img loading="lazy" src="review/photos/${item.file.replace(/\.[^.]+$/, "")}.jpg" alt="">`
    : `<video muted loop playsinline preload="none" poster="review/previews/${item.id}.jpg" data-src="review/previews/${item.id}.mp4"></video>`;
  const flags = isPhoto ? [`sharpness ${item.sharpness}`] : [
    item.day_source === "estimated" ? "date estimated" : "date from file",
    item.vertical ? "vertical" : null, item.slowmo_ok ? item.fps + " fps: slow-mo OK" : item.fps + " fps",
    ...(item.people || []).map(p => "👤 " + p)].filter(Boolean);
  el.innerHTML = `
    <div class="media">${media}
      <span class="badge ${isPhoto ? "CALM" : item.kind}">${isPhoto ? "PHOTO" : item.kind}</span>
      <span class="cat">${item.cat}</span></div>
    <div class="body">
      <div class="reason">${item.reason || item.note}</div>
      <div class="meta">${isPhoto ? item.file + (item.day !== "unknown" ? " · " + item.day : "")
        : `${item.id} · ${item.file} · ${fmt(item.start)}–${fmt(item.end)} (${item.duration}s) · ${item.day}`}</div>
      <div class="flags">${flags.map(f => `<span class="flag">${f}</span>`).join("")}</div>
      <input class="note" placeholder="note (e.g. trim, use for name card…)" value="${(s.note || "").replace(/"/g, "&quot;")}">
      <div class="row">
        <span class="score">score ${item.score.toFixed(2)}<i><b style="width:${Math.min(100, item.score * 100)}%"></b></i></span>
        <button class="keep ${s.keep ? "k" : ""}">${s.keep ? "✓ Keep" : "Dropped"}</button>
        <button class="starbtn ${s.star ? "s" : ""}" title="Must have">★</button>
      </div></div>`;
  el.querySelector(".keep").onclick = () => { s.keep = !s.keep; if (!s.keep) s.star = false; save(); refresh(el, s); };
  el.querySelector(".starbtn").onclick = () => { s.star = !s.star; if (s.star) s.keep = true; save(); refresh(el, s); };
  el.querySelector(".note").oninput = e => { s.note = e.target.value; save(); };
  return el;
}
function refresh(el, s) {
  el.classList.toggle("drop", !s.keep); el.classList.toggle("star", s.star);
  const k = el.querySelector(".keep"); k.classList.toggle("k", s.keep); k.textContent = s.keep ? "✓ Keep" : "Dropped";
  el.querySelector(".starbtn").classList.toggle("s", s.star); applyFilter(); stats();
}
function render() {
  const m = document.getElementById("main"); m.innerHTML = "";
  for (const [d, info] of Object.entries(D.days)) {
    const sec = document.createElement("section"); sec.className = "day";
    const items = D.cands.filter(c => c.day === d);
    const est = items.every(c => c.day_source === "estimated") ? " (estimated from weather & file order)" : "";
    sec.innerHTML = `<h2>${info.label} <small>${info.title} · ${items.length} clips${est}</small></h2><div class="grid"></div>`;
    items.forEach(c => sec.querySelector(".grid").appendChild(card(c, false)));
    m.appendChild(sec);
  }
  const ps = document.createElement("section"); ps.className = "day photos";
  ps.innerHTML = `<h2>Best 15 photos <small>sharp, people, scenery</small></h2><div class="grid"></div>`;
  D.photos.forEach(p => ps.querySelector(".grid").appendChild(card(p, true)));
  m.appendChild(ps);
  const h = document.createElement("p"); h.className = "hint";
  h.textContent = "Choices are saved in this browser automatically. Export downloads selections.json; move it into the ski-edit folder for phase 2.";
  m.appendChild(h);
  const io = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target;
    if (e.isIntersecting) { if (!v.src) v.src = v.dataset.src; v.play().catch(() => {}); } else v.pause();
  }), { rootMargin: "200px" });
  document.querySelectorAll("video").forEach(v => io.observe(v));
  applyFilter(); stats();
}
function applyFilter() {
  document.querySelectorAll(".card").forEach(el => {
    const s = get(el.dataset.id), k = el.dataset.kind;
    el.hidden = !(filter === "all" || filter === k || (filter === "star" && s.star) || (filter === "kept" && s.keep)
      || (filter === "dropped" && !s.keep) || (filter === "photos" && k === "PHOTO"));
  });
  document.querySelectorAll("section.day").forEach(sec => sec.hidden = !sec.querySelector(".card:not([hidden])"));
}
function stats() {
  const c = D.cands.map(x => get(x.id)), kept = D.cands.filter(x => get(x.id).keep);
  const secs = kept.reduce((a, x) => a + x.duration, 0);
  document.getElementById("stats").innerHTML =
    `<b>${kept.length}</b>/${D.cands.length} clips kept · <b>${c.filter(s => s.star).length}</b> ★ · ` +
    `${kept.filter(x => x.kind === "ACTION").length} action / ${kept.filter(x => x.kind === "CALM").length} calm · ` +
    `${Math.round(secs)}s of raw clips · <b>${D.photos.filter(p => get("p:" + p.file).keep).length}</b> photos`;
}
const fb = document.getElementById("filters");
FILTERS.forEach(([k, label]) => { const b = document.createElement("button"); b.textContent = label; b.className = k === filter ? "on" : "";
  b.onclick = () => { filter = k; fb.querySelectorAll("button").forEach(x => x.classList.remove("on")); b.classList.add("on"); applyFilter(); }; fb.appendChild(b); });
document.getElementById("export").onclick = () => {
  const out = { exported_at: new Date().toISOString(),
    clips: D.cands.map(c => ({ id: c.id, file: c.file, start: c.start, end: c.end, kind: c.kind, cat: c.cat, day: c.day,
      keep: get(c.id).keep, must_have: get(c.id).star, note: get(c.id).note || "" })),
    photos: D.photos.map(p => ({ file: p.file, keep: get("p:" + p.file).keep, must_have: get("p:" + p.file).star, note: get("p:" + p.file).note || "" })) };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" }));
  a.download = "selections.json"; a.click();
  const t = document.getElementById("toast"); t.textContent = "selections.json downloaded: move it into the ski-edit folder";
  t.style.opacity = 1; setTimeout(() => t.style.opacity = 0, 3500);
};
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
