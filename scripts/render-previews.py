"""Render GIFs and an offline, alpha-preserving atlas player for one pet."""
import argparse
import html
import json

from PIL import Image

from pet_format import STATES, frame, pet_directory


def save_gif(frames, destination, durations):
    indexed = []
    for rgba in frames:
        palette = rgba.convert('RGB').quantize(colors=255)
        palette.paste(255, mask=rgba.getchannel('A').point(lambda a: 255 if a < 128 else 0))
        indexed.append(palette)
    indexed[0].save(destination, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, transparency=255, disposal=2, optimize=False)


def render(pet_id, preserve_gifs=False):
    pet = pet_directory(pet_id)
    manifest = json.loads((pet / 'pet/pet.json').read_text(encoding='utf-8-sig'))
    atlas = Image.open(pet / 'pet/spritesheet.webp').convert('RGBA')
    preview = pet / 'previews'
    preview.mkdir(exist_ok=True)
    labels = ['安静待机', '向右移动', '向左移动', '打招呼', '跳跃', '失落与恢复', '等待输入', '专注思考', '审查确认', '十六方向观察']
    animations = []
    timings = {}
    summary = pet / 'source/qa/qa-summary.json'
    if summary.exists():
        timings = json.loads(summary.read_text(encoding='utf-8-sig')).get('standardRows', {}).get('previewTimingMs', {})
    for row, (name, count) in enumerate((*STATES, ('look-directions', 16))):
        coordinates = [(row, i) for i in range(count)] if row < 9 else [(9+i//8, i%8) for i in range(16)]
        durations = timings.get(name, [140 if name.startswith('running-') else 180] * count)
        if len(durations) != count:
            raise ValueError(f'Invalid timing count for {name}')
        if not preserve_gifs or not (preview / f'{name}.gif').exists():
            save_gif([frame(atlas, r, c) for r, c in coordinates], preview / f'{name}.gif', durations)
        else:
            # Existing previews are the timing authority when preserving their bytes.
            with Image.open(preview / f'{name}.gif') as gif:
                durations = []
                for index in range(gif.n_frames):
                    gif.seek(index)
                    durations.append(gif.info['duration'])
            if len(durations) != count:
                raise ValueError(f'Invalid preserved GIF frame count for {name}')
        animations.append({'id': name, 'label': labels[row], 'cells': coordinates, 'durations': durations})
    cards = ''.join(f'<article><div class="stage"><canvas width="192" height="208" aria-label="{item["label"]}"></canvas></div><h2>{item["label"]}</h2><p>{item["id"]}</p></article>' for item in animations)
    template = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__ · 动画预览</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf2f8;color:#22334d;font:16px/1.7 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:42px 24px}header{margin-bottom:28px}small{letter-spacing:.18em;color:#526b8e;font-weight:700}
h1{font-size:clamp(26px,4vw,40px);line-height:1.3;margin:12px 0}header p{max-width:650px;color:#52637a}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-bottom:26px}
button,select{font:inherit;padding:8px 16px;border:1px solid #c3cedf;border-radius:12px;background:white;color:#22334d;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(204px,1fr));gap:18px}
article{border-radius:20px;background:white;border:1px solid #dde5f0;overflow:hidden;padding-bottom:14px}
.stage{display:grid;place-items:center;height:244px;background:var(--stage,#f8fafc)}canvas{width:192px;height:208px}
h2{font-size:17px;margin:14px 18px 0}article p{font:12px/1.5 ui-monospace,monospace;color:#6c7e98;margin:4px 18px}
a{color:#315e9d}footer{margin-top:30px;font-size:14px;color:#61738c}.dark{--stage:#182332}.checker{--stage:repeating-conic-gradient(#e4e9f1 0% 25%,#fafbfc 0% 50%) 0 0/20px 20px}
@media(prefers-color-scheme:dark){body{background:#111a29;color:#e2eaf7}header p,footer,small{color:#a7b6cd}article{background:#1b2940;border-color:#2b3b54}a{color:#9ec0fa}}
</style></head><body><main><header><small>CODEX PETS / V2</small><h1>__NAME__</h1><p>__DESCRIPTION__</p></header>
<div class="controls"><button id="pause">暂停动画</button><label>背景 <select id="background"><option value="">浅色</option><option value="dark">深色</option><option value="checker">透明检查</option></select></label><label>速度 <select id="speed"><option value="1">正常</option><option value="2">慢速 ½</option><option value="0.5">快速 2×</option></select></label></div>
<div class="grid">__CARDS__</div><footer>按实际桌宠尺寸 192 × 208 播放，直接读取最终 WebP 图集。<br><a href="../README.md">角色说明与许可</a> · <a href="../assets/contact-sheet-extended.png">完整联系表</a> · <a href="../assets/look-directions.png">观察方向</a> · <a href="../source/qa/visual-qa.json">视觉验收记录</a><p id="status" role="status">正在加载图集…</p></footer></main>
<script>
const animations=__ANIMATIONS__;
const image=new Image(); const canvases=[...document.querySelectorAll('canvas')];
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches; let speed=1; let elapsed=0; let last=null;
const pause=document.querySelector('#pause');
function syncPause(){pause.textContent=paused?'播放动画':'暂停动画';pause.setAttribute('aria-pressed',String(paused));}
syncPause(); pause.onclick=()=>{paused=!paused;syncPause();};
document.querySelector('#background').onchange=e=>document.body.className=e.target.value;
document.querySelector('#speed').onchange=e=>speed=Number(e.target.value);
function paint(){animations.forEach((a,i)=>{let t=elapsed%a.durations.reduce((s,d)=>s+d,0);let n=0;while(t>=a.durations[n]&&n<a.cells.length-1){t-=a.durations[n++];}const [r,c]=a.cells[n];const ctx=canvases[i].getContext('2d');ctx.clearRect(0,0,192,208);ctx.drawImage(image,c*192,r*208,192,208,0,0,192,208);});}
function tick(now){if(last!==null&&!paused&&!document.hidden)elapsed+=Math.min(now-last,100)/speed;last=now;paint();requestAnimationFrame(tick);}
image.onload=()=>{document.querySelector('#status').textContent='图集已加载 · 9 种状态 + 16 方向';requestAnimationFrame(tick);};
image.onerror=()=>document.querySelector('#status').textContent='无法读取图集，请保留完整目录结构后重新打开。';
image.src='../pet/spritesheet.webp';
</script></body></html>'''
    page = template.replace('__NAME__', html.escape(manifest['displayName'])).replace('__DESCRIPTION__', html.escape(manifest['description']))
    page = page.replace('__CARDS__', cards).replace('__ANIMATIONS__', json.dumps(animations, ensure_ascii=False))
    (preview / 'index.html').write_text(page, encoding='utf-8')
    readme = f'# {manifest["displayName"]} · 动画预览\n\n[浅深背景播放](index.html) · [角色说明](../README.md)\n\n'
    readme += '| 状态 | 预览 |\n| --- | --- |\n'
    readme += ''.join(f'| {a["label"]} | ![{a["label"]}]({a["id"]}.gif) |\n' for a in animations)
    (preview / 'README.md').write_text(readme, encoding='utf-8')
    print(f'Rendered previews: {pet_id}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pet-id', required=True)
    parser.add_argument('--preserve-gifs', action='store_true')
    args = parser.parse_args()
    render(args.pet_id, args.preserve_gifs)
