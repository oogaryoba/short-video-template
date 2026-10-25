#!/usr/bin/env python3
"""依 spec.json 產生 HyperFrames 直式短影音專案（1080x1920／30fps）。
用法：python3 build.py spec.json [--font 字型檔] [--src 原片資料夾] [--out 專案資料夾]
"""
from pathlib import Path
import json, html, math, os, sys, shutil, subprocess, wave, argparse
import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont

SKILL = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('spec'); ap.add_argument('--font'); ap.add_argument('--src'); ap.add_argument('--out')
A = ap.parse_args()
SPECF = Path(A.spec).resolve(); S = json.loads(SPECF.read_text())
base = SPECF.parent
SRC = Path(A.src or S.get('source_dir', '.')); SRC = SRC if SRC.is_absolute() else base / SRC
P = Path(A.out or S.get('out_dir', S.get('id', 'project'))); P = P if P.is_absolute() else base / P
R = float(S.get('rate', 1.13)); MAXD = float(S.get('max_duration', 59))
EXT = S.get('source_ext', '.MOV')
FONT_CANDIDATES = [A.font, os.environ.get('SHORTVIDEO_FONT'), S.get('font'),
  '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
  '/usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc', '/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc',
  '/System/Library/Fonts/STHeiti Medium.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc',
  'C:/Windows/Fonts/msjhbd.ttc', 'C:/Windows/Fonts/msjh.ttc']
FONT = next((f for f in FONT_CANDIDATES if f and Path(f).exists()), None)
if not FONT: sys.exit('找不到中文字型：用 --font 指定，或安裝 fonts-noto-cjk')
SPK = S.get('speakers', {})  # {代號: {label, color}}

def run(*a): subprocess.run([str(x) for x in a], check=True)
def srcfile(src):
  f = SRC / f'{src}{EXT}'
  if not f.exists(): sys.exit(f'找不到原片 {f}')
  return f

# 20ms RMS 音量包絡，用來把剪點／字幕邊界吸到最安靜的位置，避免切在字中間。
_ENV = {}
def env(src):
  if src not in _ENV:
    w = P/'work/audio'/f'{src}.wav'
    if not w.exists():
      w.parent.mkdir(parents=True, exist_ok=True)
      run('ffmpeg', '-v', 'error', '-y', '-i', srcfile(src), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', w)
    x = wave.open(str(w)); a = np.frombuffer(x.readframes(x.getnframes()), np.int16).astype(float)
    n = len(a)//320; _ENV[src] = np.sqrt((a[:n*320].reshape(n, 320)**2).mean(1)+1)
  return _ENV[src]
def snap(src, t, win=.35):
  e = env(src); i0 = max(0, int((t-win)*50)); i1 = min(len(e), int((t+win)*50)+1)
  if i1 <= i0: return round(t, 2)
  sm = np.convolve(e, np.ones(5)/5, 'same')
  return round((i0+int(np.argmin(sm[i0:i1])))/50, 2)

def is_hdr(f):
  o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=color_transfer', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout
  return any(k in o for k in ('arib-std-b67', 'smpte2084'))
HAS_ZSCALE = 'zscale' in subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True).stdout
def cut(src, a, b, dst):
  if dst.exists(): return
  f = srcfile(src); vf = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30'
  if is_hdr(f):
    if HAS_ZSCALE:
      vf = 'zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,' + vf
    else:
      print(f'⚠️ {src} 是 HDR，但 ffmpeg 沒有 zscale：請先用 scripts/to_sdr.sh 轉 SDR，否則顏色會偏灰', file=sys.stderr)
  run('ffmpeg', '-v', 'error', '-ss', a, '-i', f, '-t', b-a, '-map', '0:v:0', '-map', '0:a:0', '-vf', vf,
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-g', '30', '-keyint_min', '30', '-pix_fmt', 'yuv420p',
      '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
      '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-y', dst)

def sfx(name):
  # 合成音效（無版權疑慮），音量另由 data-volume 控制。
  d = P/'assets'/f'{name}.mp3'
  if d.exists(): return
  expr = {'pop': 'sine=f=880:d=0.12,afade=t=out:st=0.02:d=0.10',
          'error': 'sine=f=220:d=0.3,volume=0.8,afade=t=out:st=0.15:d=0.15',
          'whoosh': 'anoisesrc=d=0.38:c=pink:a=0.5,highpass=f=600,lowpass=f=5000,afade=t=in:d=0.18,afade=t=out:st=0.2:d=0.18'}[name]
  run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', expr, '-ar', '48000', '-ac', '2', '-b:a', '128k', d)

css = (SKILL/'references/style.css').read_text()
font = '@font-face{font-family:"CapFont";src:url("assets/font-subset.otf") format("opentype");font-weight:900;}'
spkcss = ''.join(f'.{k} .text{{color:{v["color"]}}}' for k, v in SPK.items())
rootcss = 'html,body{width:1080px;height:1920px;overflow:hidden;background:#211b12}#root{position:relative;width:100%;height:100%;overflow:hidden}#background{position:absolute;inset:0;background:#211b12}.camera{position:absolute;inset:0;width:100%;height:100%;transform-origin:50% 35%;overflow:hidden}.footage{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}#progress{position:absolute;left:0;top:0;width:100%;height:8px;background:#ffe052;transform-origin:left center;z-index:91}'
WHIP = '''<!doctype html><html lang="zh-Hant"><body><template><style>#ID-root{position:absolute;inset:0;width:100%;height:100%;overflow:hidden;}#ID-strip{position:absolute;inset:0;width:100%;height:100%;filter:url(#ID-blur);}.ID-panel{position:absolute;top:0;width:1080px;height:1920px;object-fit:cover;}</style><div id="ID-root" data-composition-id="ID" data-width="1080" data-height="1920" data-duration="0.38"><svg width="0" height="0" aria-hidden="true" data-layout-ignore="true"><defs><filter id="ID-blur" x="-40%" y="-10%" width="180%" height="120%"><feGaussianBlur id="ID-blur-node" stdDeviation="0 0"/></filter></defs></svg><div id="ID-strip"><img class="ID-panel" src="assets/ID-before.jpg" style="left:0" alt=""/><img class="ID-panel" src="assets/ID-after.jpg" style="left:1080px" alt=""/></div></div><script>const tl=gsap.timeline({paused:true});const proxy={v:0};const blur=document.getElementById("ID-blur-node");function writeBlur(){blur.setAttribute("stdDeviation",proxy.v+" 0");}tl.fromTo("#ID-strip",{x:0},{x:-1080,duration:.38,ease:"power3.inOut"},0);tl.fromTo(proxy,{v:0},{v:10,duration:.19,ease:"power3.in",onUpdate:writeBlur},0);tl.to(proxy,{v:0,duration:.19,ease:"power3.out",onUpdate:writeBlur},.19);window.__timelines["ID"]=tl;</script></template></body></html>'''

clips = [tuple(c) for c in S['clips']]; capsin = [tuple(c) for c in S.get('captions', [])]
if S.get('snap', True):
  clips = [(s, snap(s, a), snap(s, b)) for s, a, b in clips]
  out = []; prev = {}
  for s, a, b, txt, who in capsin:
    w = min(.35, (b-a)/3); a2 = max(snap(s, a, w), prev.get(s, 0)); b2 = max(snap(s, b, w), a2+.3)
    out.append((s, a2, b2, txt, who)); prev[s] = b2
  capsin = out
for d in ['assets', 'compositions', 'edits', 'renders']: (P/d).mkdir(parents=True, exist_ok=True)
for f in ['package.json', 'hyperframes.json']:
  t = (SKILL/'references/project'/f).read_text().replace('__NAME__', P.name); (P/f).write_text(t)
for n in ['pop', 'error', 'whoosh']: sfx(n)

els = []; js = []; over = []; overjs = []; edl = []; caps = []; t = 0
for k, (src, a, b) in enumerate(clips):
  cut(src, a, b, P/f'assets/c{k}.mp4')
  dur = math.ceil((b-a)/R*30-1e-6)/30
  els.append(f'<div id="cam{k}" class="camera"><video id="footage{k}" class="clip footage" src="assets/c{k}.mp4" data-start="{t:.6f}" data-duration="{dur:.6f}" data-media-start="0" data-playback-rate="{R}" data-track-index="0" data-has-audio="true" data-volume="1" playsinline></video></div>')
  edl.append(dict(id=f'c{k}', source=src, source_start=a, source_end=b, start=t, duration=dur)); t += dur
D = round(t, 6)
if D >= MAXD: sys.exit(f'總長 {D:.2f}s 超過上限 {MAXD}s，請刪減 clips')
def at(src, s):
  for c in edl:
    if c['source'] == src and c['source_start'] <= s < c['source_end']: return c['start']+(s-c['source_start'])/R
  sys.exit(f'{src} {s}s 不在任何保留片段內')

for src, ca, cb, txt, who in capsin:
  for c in [c for c in edl if c['source'] == src and cb > c['source_start'] and ca < c['source_end']]:
    x = max(ca, c['source_start']); y = min(cb, c['source_end'])
    st = c['start']+(x-c['source_start'])/R; du = min((y-x)/R, c['start']+c['duration']-st); cid = f'cap{len(caps)}'
    size = 60 if len(txt) > 13 else 70
    lab = SPK.get(who, {}).get('label', '')
    wh = f'<div class="who">{html.escape(lab)}</div>' if lab else ''
    over.append(f'<div id="{cid}" class="clip cap {who}" data-start="{st:.6f}" data-duration="{du:.6f}" data-track-index="3">{wh}<div class="text" style="font-size:{size}px">{html.escape(txt)}</div></div>')
    overjs.append(f'tl.fromTo("#{cid} .text",{{scale:.94,y:10}},{{scale:1,y:0,duration:.14,ease:"power3.out"}},{st:.6f});')
    caps.append(dict(start=round(st, 3), end=round(st+du, 3), text=txt, speaker=who, source=src, source_start=x))
for j, (src, s, txt, fx) in enumerate(S.get('moments', [])):
  st = at(src, s)
  over.append(f'<div id="react{j}" class="clip react" data-start="{st:.6f}" data-duration="1.5" data-track-index="4"><div class="reactbox">{html.escape(txt)}</div></div>')
  overjs.append(f'tl.fromTo("#react{j} .reactbox",{{scale:.75,y:15}},{{scale:1,y:0,duration:.22,ease:"power3.out"}},{st:.6f});')
  if fx: els.append(f'<audio id="sfx{j}" class="clip" src="assets/{fx}.mp3" data-start="{st:.6f}" data-duration=".38" data-media-start="0" data-track-index="6" data-volume=".14"></audio>')
if S.get('next'):
  st = D-1.6
  over.append(f'<div id="next" class="clip react" data-start="{st:.6f}" data-duration="1.6" data-track-index="4"><div class="reactbox" style="font-size:44px">{html.escape(S["next"])}</div></div>')
  overjs.append(f'tl.fromTo("#next .reactbox",{{scale:.94,y:10}},{{scale:1,y:0,duration:.2,ease:"power3.out"}},{st:.6f});')
# 只在換原片、或同一支跳超過 3 秒時加甩鏡轉場。
for j in range(1, len(edl)):
  pv, cu = edl[j-1], edl[j]
  if pv['source'] == cu['source'] and cu['source_start']-pv['source_end'] < 3: continue
  cid = f'whip{j}'; ct = cu['start']
  for side, c, sec in [('before', pv, pv['source_end']-pv['source_start']-.08), ('after', cu, .08)]:
    run('ffmpeg', '-v', 'error', '-y', '-ss', max(0, sec), '-i', P/f'assets/{c["id"]}.mp4', '-frames:v', '1', '-q:v', '2', P/f'assets/{cid}-{side}.jpg')
  (P/f'compositions/{cid}.html').write_text(WHIP.replace('ID', cid))
  els.append(f'<div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" data-start="{max(0,ct-.19):.6f}" data-duration=".38" data-track-index="1" data-width="1080" data-height="1920"></div>')
  els.append(f'<audio id="whoosh{j}" class="clip" src="assets/whoosh.mp3" data-start="{max(0,ct-.19):.6f}" data-duration=".38" data-media-start="0" data-track-index="6" data-volume=".13"></audio>')
js.append('const tl=gsap.timeline({paused:true});')
for src, s in S.get('punch', []):
  st = at(src, s); k = next(i for i, c in enumerate(edl) if c['source'] == src and c['source_start'] <= s < c['source_end'])
  js.append(f'tl.fromTo("#cam{k}",{{scale:1}},{{scale:1.08,duration:.16,ease:"power3.out",immediateRender:false}},{st:.6f});tl.to("#cam{k}",{{scale:1,duration:.2,ease:"power2.out"}},{st+1.4:.6f});')
js.append(f'tl.fromTo("#progress",{{scaleX:0}},{{scaleX:1,duration:{D},ease:"none"}},0);window.__timelines["main"]=tl;')
overlay = f'<!doctype html><html lang="zh-Hant"><body><template><style>{font}{css}{spkcss}#overlay-root{{position:absolute;inset:0;width:100%;height:100%;}}</style><div id="overlay-root" data-composition-id="overlay" data-width="1080" data-height="1920" data-duration="{D}">{"".join(over)}</div><script>const tl=gsap.timeline({{paused:true}});{"".join(overjs)}window.__timelines["overlay"]=tl;</script></template></body></html>'
(P/'compositions/overlay.html').write_text(overlay)
els.append(f'<div id="overlay" data-composition-id="overlay" data-composition-src="compositions/overlay.html" data-start="0" data-duration="{D}" data-track-index="3" data-width="1080" data-height="1920" style="z-index:20"></div>')
page = f'<!doctype html><html lang="zh-Hant"><head><meta charset="UTF-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{font}{rootcss}</style></head><body><div id="root" data-composition-id="main" data-width="1080" data-height="1920" data-duration="{D}"><div id="background"></div>{"".join(els)}<div id="progress"></div></div><script>{"".join(js)}</script></body></html>'
(P/'index.html').write_text(page)
# .ttc 字型集優先選繁中（TC）字面；可用 FONT_INDEX 指定。
def face_index(path):
  if 'FONT_INDEX' in os.environ: return int(os.environ['FONT_INDEX'])
  from fontTools.ttLib import TTCollection
  for i, f in enumerate(TTCollection(path).fonts):
    if any(k in str(f['name'].getDebugName(4) or '') for k in (' TC', 'TC ', 'TC-', 'JhengHei')): return i
  return 0
fo = TTFont(FONT, fontNumber=face_index(FONT)) if FONT.lower().endswith('.ttc') else TTFont(FONT)
need = {ch for t in [c['text'] for c in caps]+[m[2] for m in S.get('moments', [])]+[S.get('next', '')]+[v.get('label', '') for v in SPK.values()] for ch in t if not ch.isspace()}
miss = sorted(ch for ch in need if ord(ch) not in fo.getBestCmap())
if miss: print(f'⚠️ 字型 {Path(FONT).name} 缺字：{"".join(miss)}，畫面會出現方框；請用 --font 換字型', file=sys.stderr)
ss = subset.Subsetter(options=subset.Options()); ss.populate(text=page+overlay); ss.subset(fo); fo.save(P/'assets/font-subset.otf')
(P/'edits/captions.json').write_text(json.dumps(caps, ensure_ascii=False, indent=2))
(P/'edits/edl.json').write_text(json.dumps(dict(duration=D, clips=edl), ensure_ascii=False, indent=2))
(P/'meta.json').write_text(json.dumps(dict(id=P.name, name=S.get('title', P.name)), ensure_ascii=False))
print(f'完成：{P}  長度 {D:.2f}s  字幕 {len(caps)} 段  字型 {Path(FONT).name}')
