"""Shared page and slide styling for Public Record report packs (copied per report so each repo folder stands alone)."""
import base64
from pathlib import Path
FONTS = None  # set by the build script


def font_face():
    def ff(fam, wt, file):
        b = base64.b64encode((Path(FONTS) / file).read_bytes()).decode()
        return f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b}) format('woff2');}}"
    return "".join([ff("Space Grotesk", 700, "space-grotesk-latin-700-normal.woff2"),
                    ff("Space Grotesk", 500, "space-grotesk-latin-500-normal.woff2"),
                    ff("Inter", 400, "inter-latin-400-normal.woff2"), ff("Inter", 600, "inter-latin-600-normal.woff2")])



def table(headers, body):
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f'<details class="tbl"><summary>Show the numbers</summary><div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>'



PAGE_CSS = """
:root{--bg:#0A0A0F;--panel:#0F1420;--ink:#FFFFFF;--body:#D7DEEA;--muted:#8B9DC3;--faint:#5B6B8C;--rule:#1F2937;
 --accent:#3B82F6;--amber:#D97706;--ctx:#33405E;--chip:#13203A;
 --display:'Space Grotesk',ui-sans-serif,system-ui,sans-serif;--text:'Inter',ui-sans-serif,system-ui,sans-serif;color-scheme:dark;}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#F6F7FA;--panel:#FFFFFF;--ink:#0B1220;--body:#253149;
 --muted:#4B5A78;--faint:#7A88A6;--rule:#E1E6EF;--accent:#2563EB;--amber:#B45309;--ctx:#B9C3D6;--chip:#E7EEFC;color-scheme:light;}}
:root[data-theme="light"]{--bg:#F6F7FA;--panel:#FFFFFF;--ink:#0B1220;--body:#253149;--muted:#4B5A78;--faint:#7A88A6;--rule:#E1E6EF;
 --accent:#2563EB;--amber:#B45309;--ctx:#B9C3D6;--chip:#E7EEFC;color-scheme:light;}
body{background:var(--bg);color:var(--body);font:400 17px/1.65 var(--text);margin:0;
 padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));}
main{max-width:760px;margin:0 auto;padding-block:48px 80px;display:flex;flex-direction:column;gap:22px;}
h1,h2{font-family:var(--display);color:var(--ink);text-wrap:balance;margin:0;}
h1{font-size:clamp(2.1rem,5.4vw,3.3rem);line-height:1.08;font-weight:700;letter-spacing:-.01em;}
h2{font-size:1.55rem;line-height:1.2;font-weight:700;margin-top:30px;}
p{margin:0;} strong{color:var(--ink);font-weight:600;} a{color:var(--accent);}
a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.kick{font:500 .78rem/1 var(--display);letter-spacing:.16em;text-transform:uppercase;color:var(--accent);display:flex;gap:12px;flex-wrap:wrap;align-items:center;}
.draft{background:var(--chip);color:var(--muted);padding:5px 9px;letter-spacing:.08em;}
.dek{font-size:1.2rem;line-height:1.55;} .byline{font-size:.88rem;color:var(--muted);}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin-top:8px;}
.stat{background:var(--bg);padding:18px 16px;display:flex;flex-direction:column;gap:6px;min-width:0;}
.stat b{font:700 2.2rem/1 var(--display);color:var(--ink);} .stat span{font-size:.86rem;line-height:1.4;color:var(--muted);}
figure{margin:10px 0 4px;display:flex;flex-direction:column;gap:10px;}
figcaption{font:600 .98rem/1.35 var(--text);color:var(--ink);} figure .src{font-size:.8rem;color:var(--faint);}
.note{border-left:3px solid var(--amber);padding:4px 0 4px 16px;}
.quote{font:500 1.12rem/1.5 var(--display);color:var(--ink);border-left:3px solid var(--accent);padding:2px 0 2px 16px;}
ul,ol{margin:0;padding-left:22px;display:flex;flex-direction:column;gap:8px;}
.method{background:var(--panel);border:1px solid var(--rule);padding:22px;display:flex;flex-direction:column;gap:12px;font-size:.93rem;}
.method h2{margin-top:0;font-size:1.2rem;}
code{font-size:.86em;background:var(--chip);padding:1px 5px;word-break:break-all;}
.tbl summary{cursor:pointer;font-size:.85rem;color:var(--muted);}
.tw{overflow-x:auto;} table{border-collapse:collapse;font-size:.88rem;margin-top:8px;font-variant-numeric:tabular-nums;}
th,td{text-align:left;padding:5px 14px 5px 0;border-bottom:1px solid var(--rule);} th{color:var(--muted);font-weight:600;}
.end{font-size:.9rem;color:var(--muted);border-top:1px solid var(--rule);padding-top:18px;display:flex;flex-direction:column;gap:8px;}
.brand{display:flex;align-items:center;gap:10px;font:700 1.05rem var(--display);color:var(--ink);}
.sq{width:26px;height:26px;border:2px solid var(--accent);display:grid;place-items:center;font:700 .8rem var(--display);color:var(--accent);}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--rule);padding:6px 9px;font-size:.82rem;display:none;z-index:5;}
svg text{font-family:var(--text);}
.grid{stroke:var(--rule);stroke-width:1;} .ref{stroke:var(--faint);stroke-width:1;opacity:.6;} .ref0{stroke:var(--muted);stroke-width:1.5;}
.refstrong{stroke:var(--ink);stroke-width:1.5;opacity:.7;}
.ax{fill:var(--muted);font-size:15px;} .axs{fill:var(--muted);font-size:14px;} .reflbl{fill:var(--faint);font-size:13px;} .reflbl2{fill:var(--ink);font-size:14px;}
.lbl{fill:var(--ink);font-size:16px;font-weight:600;} .lblin{fill:#fff;font-size:16px;font-weight:600;} .lbls{fill:var(--muted);font-size:14px;}
.bar{fill:var(--ctx);} .bar-hi{fill:var(--accent);} .bar-amb{fill:var(--amber);}
[data-tip]{cursor:default;} [data-tip]:hover{opacity:.85;}
@media (max-width:560px){.stats{grid-template-columns:1fr;} body{font-size:16px;}}
"""

TIP_JS = """<div id="tip" role="status"></div><script>(function(){var t=document.getElementById('tip');
function s(e,el){t.textContent=el.getAttribute('data-tip');t.style.display='block';var r=el.getBoundingClientRect(),
x=(e&&e.clientX)||r.left+r.width/2,y=(e&&e.clientY)||r.top;t.style.left=Math.min(x+12,innerWidth-t.offsetWidth-8)+'px';
t.style.top=Math.max(y-36,8)+'px';}document.querySelectorAll('[data-tip]').forEach(function(el){
el.addEventListener('mousemove',function(e){s(e,el)});el.addEventListener('focus',function(){s(null,el)});
el.addEventListener('mouseleave',function(){t.style.display='none'});el.addEventListener('blur',function(){t.style.display='none'});});})();</script>"""



def slide_css():
    return f"""{font_face()}
*{{box-sizing:border-box;margin:0;}} body{{background:#0A0A0F;}}
.s{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#0A0A0F;color:#D7DEEA;padding:96px 72px 120px;
 display:flex;flex-direction:column;gap:34px;font-family:Inter,sans-serif;page-break-after:always;
 background-image:radial-gradient(#1A2234 1.4px,transparent 1.4px);background-size:44px 44px;}}
.k{{font:500 24px/1 'Space Grotesk';letter-spacing:.18em;text-transform:uppercase;color:#3B82F6;}}
h1{{font:700 98px/1.02 'Space Grotesk';color:#fff;letter-spacing:-.01em;margin-top:200px;}}
h2{{font:700 56px/1.12 'Space Grotesk';color:#fff;}}
p{{font-size:32px;line-height:1.45;color:#B9C6DD;}} .big{{font-size:40px;color:#D7DEEA;}} .sc{{font-size:26px;color:#8B9DC3;}}
.solo p{{font-size:42px;line-height:1.45;color:#D7DEEA;}} .solo h2{{font-size:72px;margin-top:120px;}}
ul{{font-size:34px;line-height:1.45;color:#B9C6DD;display:flex;flex-direction:column;gap:18px;padding-left:34px;}}
.cta{{color:#fff;font-weight:600;border-left:4px solid #3B82F6;padding-left:20px;}}
.f{{position:absolute;left:72px;right:72px;bottom:56px;display:flex;justify-content:space-between;align-items:center;font-size:22px;color:#5B6B8C;}}
.brand{{display:flex;align-items:center;gap:14px;font:700 30px 'Space Grotesk';color:#fff;}}
.sq{{width:40px;height:40px;border:3px solid #3B82F6;display:grid;place-items:center;font:700 20px 'Space Grotesk';color:#3B82F6;}}
svg text{{font-family:Inter,sans-serif;}}
.grid{{stroke:#1F2937;stroke-width:1.5;}} .ref0{{stroke:#8B9DC3;stroke-width:2;}} .refstrong{{stroke:#fff;stroke-width:2;opacity:.7;}}
.ax{{fill:#8B9DC3;font-size:21px;}} .axs{{fill:#8B9DC3;font-size:19px;}} .reflbl2{{fill:#fff;font-size:20px;}}
.lbl{{fill:#fff;font-size:23px;font-weight:600;}} .lblin{{fill:#fff;font-size:23px;font-weight:600;}} .lbls{{fill:#8B9DC3;font-size:20px;}}
.bar{{fill:#33405E;}} .bar-hi{{fill:#3B82F6;}} .bar-amb{{fill:#D97706;}}
"""
