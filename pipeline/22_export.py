"""Step 22: export the cut for an editor: DaVinci Resolve (.otio), Premiere (.xml), Final Cut Pro (.fcpxml).
   22_export [--edl <name>]

Same shots, same source in/out points, same timing as the render, pointing at the original files:
  V1   every shot (slow motion as a speed effect, the reason in the clip name/notes)
  A1   camera sound where the film plays it (level in the metadata)
  A2/3 the music cues (alternating tracks, so the overlaps under talking clips survive)
  markers at every section start
Not carried over: grade, letterbox, blurred fills/crops, title, credits, subtitles (burn those in Resolve, or use the
.srt next to the render). Resolve: File > Import > Timeline > pick the .otio (Resolve 18.5+); relink the media if
the footage moved. Output: render/<name>.otio (+ .xml/.fcpxml when the adapters are installed)."""
import opentimelineio as otio
from common import ROOT, SRC, load_json, edl_file, out_name, event_path, cfg, ffprobe

E = load_json(edl_file()); FPS = E["fps"]
inv = {r["file"]: r for r in load_json("inventory.json")}
RT = lambda s, rate=FPS: otio.opentime.RationalTime(round(s * rate), rate)
TR = lambda a, d, rate=FPS: otio.opentime.TimeRange(RT(a, rate), RT(d, FPS))


def ref(path, dur=None):
    r = otio.schema.ExternalReference(target_url=path.resolve().as_uri())
    if dur: r.available_range = TR(0, dur)
    return r


def gap_to(track, t):
    """pad a track with a gap up to timeline second t"""
    end = track.duration().to_seconds()
    if t - end > 0.5 / FPS: track.append(otio.schema.Gap(source_range=TR(0, t - end)))


tl = otio.schema.Timeline(name=E.get("title") or cfg("name", "beatcut"), global_start_time=RT(0))
V = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
A1 = otio.schema.Track(name="A1 camera", kind=otio.schema.TrackKind.Audio)
AM = [otio.schema.Track(name=f"A{k} music", kind=otio.schema.TrackKind.Audio) for k in (2, 3)]
for s in E["segments"]:
    note = f"{s['section']}: {s.get('why', '')}".strip(": ")
    if s["type"] == "photo":
        c = otio.schema.Clip(name=s["src"], media_reference=ref(SRC / s["src"], s["dur"]), source_range=TR(0, s["dur"]))
        c.metadata["beatcut"] = {"why": note}; V.append(c); continue
    parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": s.get("slowmo", 1.0)}]
    t = s["t0"]
    for p in parts:
        r = inv[p["src"]]; rate = round(r["fps"], 3) or FPS; sp = p.get("slowmo", 1.0)
        c = otio.schema.Clip(name=f"{p['src']} @{p['in']:.1f}s", media_reference=ref(SRC / p["src"], r["duration"]),
                             source_range=otio.opentime.TimeRange(RT(p["in"], rate), RT(p["dur"], FPS)))
        if sp != 1: c.effects.append(otio.schema.LinearTimeWarp(name="slow motion", time_scalar=sp))
        c.metadata["beatcut"] = {"why": note, "camera_sound": s.get("cam_audio", 0), "slowmo": sp}
        V.append(c)
        if s.get("cam_audio") and sp == 1 and r.get("has_audio"):
            gap_to(A1, t)
            a = otio.schema.Clip(name=f"{p['src']} sound", media_reference=ref(SRC / p["src"], r["duration"]),
                                 source_range=otio.opentime.TimeRange(RT(p["in"], rate), RT(p["dur"], FPS)))
            a.metadata["beatcut"] = {"level": s["cam_audio"], "bite": bool(s.get("bite"))}
            A1.append(a)
        t += p["dur"]
for k, c in enumerate(E["music"]["cues"]):
    tr = AM[k % 2]; path = event_path(E["music"]["tracks"][c["track"]])
    at, frm = c["at"], c["from"]
    if frm < 0: at, frm = at - frm, 0.0                              # a negative "from" = silence first
    gap_to(tr, at)
    m = otio.schema.Clip(name=f"{c['track']}: {path.stem}", media_reference=ref(path, float(ffprobe(path)["format"]["duration"])),
                         source_range=TR(frm, c["to"] - frm))
    m.metadata["beatcut"] = {k2: c[k2] for k2 in ("fade_in", "fade_out", "fade_curve") if k2 in c}
    tr.append(m)
last = None
for s in E["segments"]:
    if s["section"] != last:
        V.markers.append(otio.schema.Marker(name=s["section"], marked_range=TR(s["t0"], 0), color=otio.schema.MarkerColor.BLUE))
        last = s["section"]
tl.tracks.extend([V, A1] + AM)

out = ROOT / "render" / out_name("edit")
out.parent.mkdir(exist_ok=True)
otio.adapters.write_to_file(tl, str(out.with_suffix(".otio")))
written = [out.with_suffix(".otio").name]
for ext, adapter in ((".xml", "fcp_xml"), (".fcpxml", "fcpx_xml")):
    try:
        otio.adapters.write_to_file(tl, str(out.with_suffix(ext)), adapter_name=adapter); written.append(out.with_suffix(ext).name)
    except Exception as e:
        print(f"{ext}: skipped ({type(e).__name__}: {str(e)[:80]})")
print(f"{len(V)} clips, {len(A1)} camera-sound clips, {len(E['music']['cues'])} music cues -> render/" + ", ".join(written))
