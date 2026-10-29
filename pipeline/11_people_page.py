"""Step 11: names.html - one tile per distinct person (from people.json), name field + 'not one of us'.
Optional hints and merges come from event.yaml (people.hints / people.same_as). Exports names.json."""
import json
from common import ROOT, load_json, cfg

# hints: {"p10": "Anna?"} (e.g. a name from a source file name); same_as: {"p12": "p05"} clusters that are the
# same person (check sheets/people_check.jpg: cosine similarity of SFace centroids, same-person threshold ~0.36)
HINTS = cfg("people.hints") or {}
SAME_AS = cfg("people.same_as") or {}


def main():
    ppl = [p for p in load_json("people.json") if p["id"] not in SAME_AS]
    data = [{"id": p["id"], "n": p["n_faces"], "srcs": p["n_sources"], "extras": p["extras"], "hint": HINTS.get(p["id"], "")} for p in ppl]
    (ROOT / "names.html").write_text(TEMPLATE.replace("/*DATA*/", json.dumps(data)), encoding="utf-8")
    print(len(data), "people -> names.html")


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Who's Who</title>
<style>
:root{--bg:#f4f2ee;--card:#fff;--line:#ddd8cf;--fg:#1c1d1f;--mut:#6c6f75;--ok:#1f8a5b}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:2;background:rgba(244,242,238,.96);border-bottom:1px solid var(--line);padding:14px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0}header p{margin:0;color:var(--mut);font-size:13px}
#count{font-variant-numeric:tabular-nums;color:var(--mut);font-size:13px}
#exp{margin-left:auto;font:inherit;background:var(--ok);color:#fff;border:0;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer}
main{max-width:1200px;margin:0 auto;padding:18px 20px 60px;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card.no{opacity:.4}
.face{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:#ddd}
.ex{display:flex;gap:4px;padding:4px 4px 0}.ex img{flex:1;min-width:0;aspect-ratio:1;object-fit:cover;border-radius:5px}
.b{padding:10px 12px 12px;display:flex;flex-direction:column;gap:8px}
.m{color:var(--mut);font-size:12px}
input[type=text]{width:100%;border:1px solid var(--line);border-radius:7px;padding:8px 10px;font:inherit;background:#fbfaf8}
input[type=text]:not(:placeholder-shown){border-color:var(--ok);background:#fff}
label{font-size:13px;color:var(--mut);display:flex;gap:6px;align-items:center;cursor:pointer}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1c1d1f;color:#fff;padding:8px 14px;border-radius:8px;opacity:0;transition:opacity .2s;pointer-events:none}
</style></head><body>
<header><div><h1>Who's who</h1><p>One tile per person found in the footage. The small faces are the same person in other clips.</p></div>
<span id="count"></span><button id="exp">Export names.json</button></header>
<main id="m"></main><div id="toast"></div>
<script>
const P=/*DATA*/, KEY="skiPeople.v1";
let st={};try{st=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){};count()};
const esc=s=>(s||"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");
const M=document.getElementById("m");
for(const p of P){
  const s=st[p.id]||={name:"",no:false};
  const c=document.createElement("div");c.className="card"+(s.no?" no":"");
  c.innerHTML=`<img class="face" src="people/${p.id}.jpg" alt="">
   ${p.extras?`<div class="ex">${Array.from({length:p.extras},(_,j)=>`<img src="people/${p.id}_${j}.jpg" alt="">`).join("")}</div>`:""}
   <div class="b"><span class="m">${p.id} · seen in ${p.srcs} clips/photos</span>
   <input type="text" placeholder="${p.hint?esc(p.hint):"name"}" value="${esc(s.name)}">
   <label><input type="checkbox" ${s.no?"checked":""}> not one of us / skip</label></div>`;
  c.querySelector("input[type=text]").oninput=e=>{s.name=e.target.value.trim();save()};
  c.querySelector("input[type=checkbox]").onchange=e=>{s.no=e.target.checked;c.classList.toggle("no",s.no);save()};
  M.appendChild(c)}
function count(){const n=P.filter(p=>st[p.id]?.name).length;document.getElementById("count").textContent=`${n} of ${P.length} named`}
count();
document.getElementById("exp").onclick=()=>{
  const out={exported_at:new Date().toISOString(),people:P.map(p=>({id:p.id,name:st[p.id]?.name||"",skip:!!st[p.id]?.no}))};
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{type:"application/json"}));
  a.download="names.json";a.click();const t=document.getElementById("toast");
  t.textContent="names.json downloaded: move it into the event folder";t.style.opacity=1;setTimeout(()=>t.style.opacity=0,3500)};
</script></body></html>"""

if __name__ == "__main__":
    main()
