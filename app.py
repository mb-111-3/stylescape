"""StyleScape studio and authenticated API settings."""
import os
import secrets
from pathlib import Path
from socket import socket
from threading import Lock
import tempfile
from urllib.parse import quote
from settings import read_env, get_admin_password, get_api_key
import key_pool

import gradio as gr
from fastapi import FastAPI
from PIL import Image

ENV_PATH = Path(__file__).with_name('.env')

def load_dotenv():
    for name, value in read_env(ENV_PATH).items():
        os.environ.setdefault(name, value)

load_dotenv()
from generate import iter_redesign_variations, get_runtime_defaults
from utils import ROOM_TYPES, STYLES, ValidationError, build_prompt, save_generated_image, save_uploaded_image, validate_inputs

SETTINGS_LOCK = Lock()

# ---------------------------------------------------------------------------
# UI: icons (inline SVG -> CSS masks, so no external files or CDNs are needed)
# ---------------------------------------------------------------------------
ICONS = {
    'sparkles': "<path d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/><path d='M5 3v4'/><path d='M19 17v4'/><path d='M3 5h4'/><path d='M17 19h4'/>",
    'image': "<rect width='18' height='18' x='3' y='3' rx='2' ry='2'/><circle cx='9' cy='9' r='2'/><path d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/>",
    'upload': "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/><polyline points='17 8 12 3 7 8'/><line x1='12' x2='12' y1='3' y2='15'/>",
    'download': "<path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/><polyline points='7 10 12 15 17 10'/><line x1='12' x2='12' y1='15' y2='3'/>",
    'palette': "<circle cx='13.5' cy='6.5' r='.5' fill='black'/><circle cx='17.5' cy='10.5' r='.5' fill='black'/><circle cx='8.5' cy='7.5' r='.5' fill='black'/><circle cx='6.5' cy='12.5' r='.5' fill='black'/><path d='M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z'/>",
    'wand': "<path d='m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72'/><path d='m14 7 3 3'/><path d='M5 6v4'/><path d='M19 14v4'/><path d='M10 2v2'/><path d='M7 8H3'/><path d='M21 16h-4'/><path d='M11 3H9'/>",
    'arrow-right': "<path d='M5 12h14'/><path d='m12 5 7 7-7 7'/>",
    'arrow-up-right': "<path d='M7 7h10v10'/><path d='M7 17 17 7'/>",
    'x': "<path d='M18 6 6 18'/><path d='m6 6 12 12'/>",
    'layers': "<path d='m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z'/><path d='m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65'/><path d='m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65'/>",
    'columns': "<rect width='18' height='18' x='3' y='3' rx='2'/><path d='M12 3v18'/>",
    'key': "<path d='m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4'/><path d='m21 2-9.6 9.6'/><circle cx='7.5' cy='15.5' r='5.5'/>",
    'database': "<ellipse cx='12' cy='5' rx='9' ry='3'/><path d='M3 5V19A9 3 0 0 0 21 19V5'/><path d='M3 12A9 3 0 0 0 21 12'/>",
    'shield-check': "<path d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/><path d='m9 12 2 2 4-4'/>",
    'log-out': "<path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/><polyline points='16 17 21 12 16 7'/><line x1='21' x2='9' y1='12' y2='12'/>",
    'save': "<path d='M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z'/><path d='M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7'/><path d='M7 3v4a1 1 0 0 0 1 1h7'/>",
    'sun': "<circle cx='12' cy='12' r='4'/><path d='M12 2v2'/><path d='M12 20v2'/><path d='m4.93 4.93 1.41 1.41'/><path d='m17.66 17.66 1.41 1.41'/><path d='M2 12h2'/><path d='M20 12h2'/><path d='m6.34 17.66-1.41 1.41'/><path d='m19.07 4.93-1.41 1.41'/>",
    'maximize': "<path d='M8 3H5a2 2 0 0 0-2 2v3'/><path d='M21 8V5a2 2 0 0 0-2-2h-3'/><path d='M3 16v3a2 2 0 0 0 2 2h3'/><path d='M16 21h3a2 2 0 0 0 2-2v-3'/>",
    'camera': "<path d='M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z'/><circle cx='12' cy='13' r='3'/>",
}


def _icon_css():
    """Build CSS custom properties and .ico-* helper classes from the ICONS table."""
    root, helpers = [], []
    for name, body in ICONS.items():
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' "
               "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + body + '</svg>')
        root.append(f'--i-{name}:url("data:image/svg+xml,{quote(svg, safe="")}");')
        helpers.append(f'.ico-{name}{{--mask:var(--i-{name});}}')
    return ':root{' + ''.join(root) + '}\n' + '\n'.join(helpers) + '\n'


_BASE_CSS = """
:root {
    --accent:#6d5dfc; --accent-dark:#5846e8; --ink:#16132e; --sub:#5b5877;
    --pink:#ec4899; --cyan:#06b6d4; --amber:#f59e0b; --emerald:#10b981;
    --grad:linear-gradient(135deg,#6366f1 0%,#8b5cf6 38%,#d946ef 72%,#fb7185 100%);
    --grad-cool:linear-gradient(135deg,#06b6d4,#3b82f6 55%,#6366f1);
    --grad-warm:linear-gradient(135deg,#f59e0b,#f97316 55%,#ec4899);
    --glass:rgba(255,255,255,.52); --glass-strong:rgba(255,255,255,.74); --glass-border:rgba(255,255,255,.78);
    --glass-shadow:0 24px 60px rgba(79,70,229,.18), inset 0 1px 0 rgba(255,255,255,.95);
}

/* ---------- Backdrop: vibrant mesh + soft drifting colour ---------- */
html, body {min-height:100%;}
body {background:linear-gradient(125deg,#c7d2fe 0%,#e9d5ff 28%,#fbcfe8 58%,#fed7aa 100%) fixed !important; color-scheme:light;}
body::before {content:""; position:fixed; inset:-15%; z-index:0; pointer-events:none; filter:blur(34px);
    background:
        radial-gradient(circle at 12% 18%, rgba(139,92,246,.62), transparent 38%),
        radial-gradient(circle at 88% 14%, rgba(236,72,153,.52), transparent 36%),
        radial-gradient(circle at 80% 88%, rgba(251,146,60,.52), transparent 38%),
        radial-gradient(circle at 18% 86%, rgba(34,211,238,.55), transparent 36%);
    animation:ss-drift 28s ease-in-out infinite alternate;}
body::after {content:""; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.45;
    background-image:radial-gradient(rgba(255,255,255,.55) 1px, transparent 1px); background-size:28px 28px;}
@keyframes ss-drift {0% {transform:translate3d(-2%,-1%,0) scale(1);} 100% {transform:translate3d(2%,2%,0) scale(1.08);}}
@keyframes ss-float {0%,100% {transform:translateY(0);} 50% {transform:translateY(-9px);}}
@media (prefers-reduced-motion: reduce) {
    body::before, .chip {animation:none !important;}
    * {transition-duration:.01ms !important;}
}
gradio-app, .gradio-container {background:transparent !important;}
.gradio-container {position:relative; z-index:1; width:100% !important; max-width:1560px !important; margin:auto; color:var(--ink); color-scheme:light; padding:12px 24px 24px !important; min-height:100vh; box-sizing:border-box;}
footer {display:none !important;}
.nav a[href="/admin"], .nav a[href="/admin/"] {display:none !important;}

/* ---------- Icons ---------- */
.ico {display:inline-block; width:1.15em; height:1.15em; flex:none; vertical-align:-.2em; background-color:currentColor;
    -webkit-mask:var(--mask) center/contain no-repeat; mask:var(--mask) center/contain no-repeat;}

/* ---------- Hero ---------- */
#hero {position:relative; overflow:hidden; padding:32px 48px 44px; margin:16px auto 20px; max-width:1440px; border-radius:32px;
    background:linear-gradient(135deg, rgba(23,18,66,.80) 0%, rgba(76,29,149,.70) 48%, rgba(219,39,119,.58) 100%);
    -webkit-backdrop-filter:blur(26px) saturate(170%); backdrop-filter:blur(26px) saturate(170%);
    border:1px solid rgba(255,255,255,.38); box-shadow:0 34px 80px rgba(76,29,149,.38), inset 0 1px 0 rgba(255,255,255,.4);}
#hero::before {content:""; position:absolute; width:560px; height:560px; right:-150px; top:-200px; border-radius:50%; pointer-events:none;
    background:radial-gradient(circle, rgba(34,211,238,.55), transparent 66%);}
#hero::after {content:""; position:absolute; width:520px; height:520px; left:-160px; bottom:-260px; border-radius:50%; pointer-events:none;
    background:radial-gradient(circle, rgba(251,191,36,.42), transparent 66%);}
#hero > * {position:relative; z-index:1;}
#hero h1 {font-size:clamp(38px,4.6vw,68px) !important; font-weight:800 !important; letter-spacing:-2px; line-height:1.06 !important; color:#fff !important; margin:26px 0 16px !important; text-shadow:0 6px 30px rgba(0,0,0,.25);}
#hero p {color:#e3e4ff !important; max-width:600px; font-size:17px; line-height:1.75;}
.hero-grid {display:grid; grid-template-columns:1.1fr .9fr; gap:56px; align-items:center; margin-top:18px;}
.nav {display:flex; justify-content:space-between; align-items:center; gap:16px; color:#fff; font-size:14px;}
.nav b {color:#fff; display:inline-flex; align-items:center; gap:12px; font-weight:700; font-size:16px; letter-spacing:.2px;}
.logo {display:inline-grid; place-items:center; width:38px; height:38px; border-radius:12px; background:var(--grad); box-shadow:0 8px 20px rgba(217,70,239,.5), inset 0 1px 0 rgba(255,255,255,.5);}
.logo .ico {width:20px; height:20px; color:#fff;}
.brand-divider {color:#a5b4fc; padding:0 2px;}
.nav a {display:inline-flex; align-items:center; gap:8px; color:#fff !important; background:rgba(255,255,255,.12); font-weight:600; text-decoration:none; border:1px solid rgba(255,255,255,.32); border-radius:12px; padding:10px 16px; transition:background .15s, border-color .15s;}
.nav a:hover {background:rgba(255,255,255,.24); border-color:rgba(255,255,255,.6);}
.nav a:focus-visible {outline:3px solid #a5b4fc; outline-offset:3px;}
.studio-badge {display:inline-flex; align-items:center; gap:8px; font-size:13px; font-weight:600; color:#fff; padding:9px 16px; border:1px solid rgba(255,255,255,.35); border-radius:30px; background:rgba(255,255,255,.14);}
.studio-badge .ico {color:#fde68a;}
.workflow {display:flex; flex-wrap:wrap; gap:12px; margin-top:28px;}
.workflow span {display:inline-flex; align-items:center; gap:9px; padding:11px 18px; background:rgba(255,255,255,.13); color:#fff; font-size:14px; border:1px solid rgba(255,255,255,.3); border-radius:999px; font-weight:600;}
.workflow span:nth-child(1) .ico {color:#67e8f9;}
.workflow span:nth-child(2) .ico {color:#f9a8d4;}
.workflow span:nth-child(3) .ico {color:#fde68a;}

/* hero illustration */
.hero-art {position:relative; padding:18px 18px 30px;}
.room-card {border-radius:26px; padding:10px; background:rgba(255,255,255,.2); border:1px solid rgba(255,255,255,.5); box-shadow:0 26px 56px rgba(0,0,0,.32); transform:rotate(1.6deg); overflow:hidden;}
.room-card svg {display:block; width:100%; height:auto; border-radius:18px;}
.chip {position:absolute; display:flex; align-items:center; gap:11px; padding:10px 15px 10px 10px; border-radius:18px; background:rgba(255,255,255,.9); color:#1e1b4b; font-size:13.5px; font-weight:700; line-height:1.25; border:1px solid #fff; box-shadow:0 14px 30px rgba(0,0,0,.24); animation:ss-float 6s ease-in-out infinite;}
.chip small {display:block; font-size:11.5px; font-weight:500; color:#6b6890;}
.chip-ico {display:grid; place-items:center; width:34px; height:34px; border-radius:11px; color:#fff; flex:none;}
.chip-a {left:-14px; top:6px;}
.chip-b {right:-8px; bottom:46px; animation-delay:-2s;}
.chip-c {left:26px; bottom:-6px; animation-delay:-4s;}
.dots {display:flex;}
.dots i {width:22px; height:22px; border-radius:50%; border:2px solid #fff; margin-left:-7px; box-shadow:0 2px 6px rgba(0,0,0,.2);}
.dots i:first-child {margin-left:0;}

/* ---------- Buttons ---------- */
#start-cta, #generate, #save-next-1, #save-next-2, .gradio-container button.primary {
    position:relative; display:inline-flex !important; align-items:center; justify-content:center; gap:11px;
    background:linear-gradient(135deg, #2563eb 0%, #4f46e5 55%, #6366f1 100%) !important;
    background-size:170% 170% !important; background-position:0% 50% !important;
    color:#fff !important; border:1px solid rgba(255,255,255,.5) !important; border-radius:16px !important;
    min-height:56px; font-weight:700; font-size:16px; letter-spacing:.2px;
    box-shadow:0 16px 34px rgba(37,99,235,.42), inset 0 1px 0 rgba(255,255,255,.5) !important;
    transition:transform .15s, box-shadow .2s, background-position .45s;}
#start-cta:hover, #generate:hover, #save-next-1:hover, #save-next-2:hover, .gradio-container button.primary:hover {
    transform:translateY(-2px); background-position:100% 50% !important; box-shadow:0 22px 44px rgba(37,99,235,.55), inset 0 1px 0 rgba(255,255,255,.55) !important;}
#start-cta:focus-visible, #save-next-1:focus-visible, #save-next-2:focus-visible, .gradio-container button.primary:focus-visible {outline:3px solid #fff; outline-offset:3px; box-shadow:0 0 0 6px rgba(37,99,235,.55) !important;}
#start-cta {align-self:center; width:min(460px,100%) !important; min-height:64px; font-size:17.5px; margin:6px auto 28px; background:linear-gradient(135deg, #2563eb 0%, #4f46e5 55%, #6366f1 100%) !important; color:#fff !important;}
#save-next-1, #save-next-2 {align-self:flex-end; width:min(320px,100%) !important; margin-top:20px;}
#start-cta::before, #save-next-2::before, #save-next-1::after, #save-next-2::after, #start-cta::after,
#save-key-btn::before, #save-pool-btn::before, .step-close::before {
    content:""; display:inline-block; flex:none; width:20px; height:20px; background-color:currentColor;
    -webkit-mask:var(--bi) center/contain no-repeat; mask:var(--bi) center/contain no-repeat; transition:transform .2s;}
#start-cta {--bi:var(--i-sparkles);}
#start-cta::after, #save-next-1::after, #save-next-2::after {--bi:var(--i-arrow-right);}
#save-next-2::before {--bi:var(--i-wand);}
#save-key-btn {--bi:var(--i-save);}
#save-pool-btn {--bi:var(--i-database);}
#start-cta:hover::after, #save-next-1:hover::after, #save-next-2:hover::after {transform:translateX(4px);}
#save-key-btn, #save-pool-btn {min-height:52px;}
.step-close {--bi:var(--i-x); display:inline-flex !important; align-items:center; justify-content:center; width:44px !important; height:44px !important; min-width:44px !important; padding:0 !important;
    border-radius:14px !important; background:rgba(255,255,255,.78) !important; color:#6b6890 !important; border:1px solid #fff !important; font-size:0 !important; line-height:1 !important;
    box-shadow:0 6px 16px rgba(79,70,229,.14) !important; transition:transform .25s, background .2s, color .2s;}
.step-close::before {width:18px; height:18px;}
.step-close:hover {background:linear-gradient(135deg,#fb7185,#f97316) !important; color:#fff !important; transform:rotate(90deg);}

/* ---------- Glass panels ---------- */
.step-screen {width:100% !important; max-width:1440px !important; margin:6px auto 18px !important; min-height:calc(100vh - 44px); padding:26px 36px 24px !important; position:relative;
    background:var(--glass) !important; -webkit-backdrop-filter:blur(30px) saturate(175%); backdrop-filter:blur(30px) saturate(175%);
    border:1px solid var(--glass-border) !important; border-radius:30px !important; box-shadow:var(--glass-shadow); overflow:visible !important;
    display:flex !important; flex-direction:column !important; justify-content:space-between !important; box-sizing:border-box !important;}
.step-screen::before {content:""; position:absolute; left:44px; right:44px; top:0; height:4px; border-radius:0 0 6px 6px; background:var(--grad); opacity:.95;}
.step-screen, .step-screen > div {overflow:visible !important; max-height:none !important;}
.glass-card {padding:30px !important; background:var(--glass) !important; -webkit-backdrop-filter:blur(30px) saturate(175%); backdrop-filter:blur(30px) saturate(175%);
    border:1px solid var(--glass-border) !important; border-radius:28px !important; box-shadow:var(--glass-shadow); overflow:visible !important; gap:16px;}
.split-row {display:flex !important; gap:26px !important; align-items:stretch !important; flex:1 1 auto !important; width:100% !important;}
.split-row > div {display:flex !important; flex-direction:column !important;}
.media-col, .controls-col {justify-content:flex-start !important;}
.tips-col {justify-content:stretch !important;}
.controls-col {padding:22px 24px !important; border-radius:24px; background:rgba(255,255,255,.68); border:1px solid rgba(255,255,255,.9); box-shadow:0 12px 32px rgba(79,70,229,.12); box-sizing:border-box !important; justify-content:space-between !important;}
.step-header {align-items:flex-start !important; gap:8px; margin-bottom:10px;}
.step-header h3, .glass-card h3 {font-size:24px !important; font-weight:800 !important; color:var(--ink) !important; display:flex; align-items:center; gap:12px; margin:4px 0 6px !important; letter-spacing:-.4px;}
.step-header p, .glass-card p {color:var(--sub) !important; font-size:14.5px; line-height:1.65;}
.title-ico {color:var(--accent); width:24px; height:24px;}
.step-badge {display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:12px; flex:none;
    background:var(--grad); color:#fff; font-size:15px; font-weight:800; box-shadow:0 8px 18px rgba(139,92,246,.42), inset 0 1px 0 rgba(255,255,255,.5);}
.step-badge .ico {width:18px; height:18px;}
.modal-step-track {display:flex; gap:10px; margin-bottom:16px; max-width:420px;}
.modal-step-track span {flex:1; height:6px; border-radius:6px; background:rgba(99,102,241,.15);}
.modal-step-track span.active {background:var(--grad); box-shadow:0 2px 10px rgba(139,92,246,.45);}
.modal-error {color:#dc2626 !important; font-size:13.5px !important; font-weight:600; margin:0 !important;}
.output-header {margin-bottom:4px;}
#output-screen #interior-gallery {height:490px !important;}

/* side cards & equal height balance */
.side-card {height:100% !important; min-height:100% !important; box-sizing:border-box !important; display:flex !important; flex-direction:column !important; justify-content:space-between !important; padding:22px 24px !important; border-radius:24px; background:rgba(255,255,255,.68); border:1px solid rgba(255,255,255,.9); box-shadow:0 12px 32px rgba(79,70,229,.12);}
.side-card h4 {margin:0 0 4px; font-size:16px; font-weight:800; color:var(--ink); display:flex; align-items:center; gap:10px;}
.side-card h4 .ico {color:var(--accent); width:20px; height:20px;}
.side-card .lead {margin:0 0 6px; font-size:13px; color:var(--sub); line-height:1.5;}
.tips-group {display:flex !important; flex-direction:column !important; justify-content:space-between !important; flex:1 1 auto !important; gap:8px !important;}
.tip {display:flex; gap:12px; align-items:center; padding:10px 0; border-top:1px solid rgba(99,102,241,.14);}
.tip-ico {display:grid; place-items:center; width:38px; height:38px; border-radius:12px; color:#fff; flex:none; box-shadow:0 8px 16px rgba(0,0,0,.14);}
.tip b {display:block; font-size:14px; color:var(--ink);}
.tip span {font-size:12.5px; color:var(--sub); line-height:1.5;}
.g1 {background:var(--grad-warm);}
.g2 {background:var(--grad-cool);}
.g3 {background:linear-gradient(135deg,#10b981,#14b8a6 60%,#06b6d4);}
.g4 {background:var(--grad);}
.step-footer {display:flex !important; justify-content:space-between !important; align-items:center !important; width:100% !important; margin-top:18px !important; padding-top:14px !important; border-top:1px solid rgba(99,102,241,.14) !important;}
.step-footer .modal-error {flex:1;}
#save-next-1, #save-next-2 {width:min(280px,100%) !important; min-height:52px !important; margin:0 !important; margin-left:auto !important;}
.sec-title {display:flex; align-items:center; gap:10px; margin:6px 0 2px; font-size:17px; font-weight:800; color:var(--ink); letter-spacing:-.2px;}
.sec-icon {display:grid; place-items:center; width:34px; height:34px; border-radius:11px; color:#fff; box-shadow:0 8px 16px rgba(99,102,241,.3);}
.sec-icon .ico {width:18px; height:18px;}

/* ---------- Gradio component polish ---------- */
.gradio-container .block, .gradio-container .form {box-shadow:none;}
.gradio-container span[data-testid="block-info"], .gradio-container .block-title {font-weight:650 !important; color:#2b2750 !important;}
.gradio-container input::placeholder, .gradio-container textarea::placeholder {color:#9aa3b2 !important; opacity:1;}
.gradio-container input:not([type="range"]):not([type="color"]), .gradio-container textarea {color:var(--ink) !important; caret-color:var(--accent);}
.gradio-container .wrap:focus-within, .gradio-container textarea:focus-visible {border-color:var(--accent) !important; box-shadow:0 0 0 4px rgba(99,102,241,.2) !important;}
.gradio-container ul.options {background:rgba(255,255,255,.97) !important; -webkit-backdrop-filter:blur(18px); backdrop-filter:blur(18px); border:1px solid rgba(99,102,241,.22) !important; border-radius:16px !important; box-shadow:0 22px 48px rgba(49,46,129,.26) !important; overflow:auto;}
.gradio-container ul.options li:hover, .gradio-container ul.options li.active {background:rgba(99,102,241,.12) !important;}
.gradio-container label.selected {background:var(--grad) !important; color:#fff !important; border-color:rgba(255,255,255,.7) !important; box-shadow:0 8px 20px rgba(139,92,246,.4);}
.gradio-container label.selected span {color:#fff !important;}
#room-upload, #interior-gallery {border-radius:24px !important; overflow:hidden;}
#room-upload {border:2px dashed rgba(139,92,246,.6) !important; background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(237,233,254,.62)) !important; transition:border-color .2s, box-shadow .2s;}
#room-upload:hover {border-color:var(--accent) !important; box-shadow:0 0 0 6px rgba(99,102,241,.14);}
#room-upload button {color:var(--accent);}
#interior-gallery {border:1px solid rgba(255,255,255,.9) !important; background:rgba(255,255,255,.6) !important; box-shadow:0 14px 36px rgba(79,70,229,.14);}
#generation-status {border:1px solid rgba(255,255,255,.9); border-radius:16px; background:rgba(255,255,255,.6);}
#generation-status textarea {font-weight:600; color:var(--accent-dark) !important;}
#before-after {gap:24px;}
#before-after .block {border-radius:22px !important; overflow:hidden; background:rgba(255,255,255,.55) !important; border:1px solid rgba(255,255,255,.9) !important; box-shadow:0 12px 30px rgba(79,70,229,.12);}
.gradio-container .table-wrap {border-radius:16px; overflow:hidden; border:1px solid rgba(99,102,241,.16);}
.gradio-container th {background:rgba(99,102,241,.12) !important;}
#room-upload button[aria-label="Share"], #interior-gallery button[aria-label="Share"],
#room-upload .share-button, #interior-gallery .share-button {display:none !important;}
.signout {display:inline-flex; align-items:center; gap:10px; padding:12px 20px; border-radius:14px; font-weight:700; text-decoration:none;
    color:#4338ca !important; background:rgba(255,255,255,.78); border:1px solid #fff; box-shadow:0 10px 24px rgba(79,70,229,.16); transition:transform .15s, background .2s, color .2s;}
.signout:hover {transform:translateY(-2px); background:linear-gradient(135deg,#fb7185,#f97316); color:#fff !important;}
.signout:focus-visible {outline:3px solid var(--accent); outline-offset:3px;}

/* ---------- Responsive ---------- */
@media (max-width: 1100px) {
    .hero-grid {grid-template-columns:1fr; gap:36px;}
    .hero-art {max-width:520px;}
    .step-screen {padding:28px 24px 32px !important;}
}
@media (max-width: 640px) {
    .gradio-container {padding:0 16px 24px !important;}
    .glass-card {padding:18px !important;}
    .nav {flex-wrap:wrap;}
    #hero {padding:24px; margin:16px 0 20px; border-radius:26px;}
    #hero h1 {letter-spacing:-1px;}
    .step-screen {padding:22px 14px !important; border-radius:24px !important;}
    #save-next-1, #save-next-2 {align-self:stretch; width:100% !important;}
}
"""

CSS = _icon_css() + _BASE_CSS

THEME = gr.themes.Soft(
    primary_hue='indigo', secondary_hue='violet', neutral_hue='slate', radius_size='lg',
    font=[gr.themes.GoogleFont('Plus Jakarta Sans'), 'Inter', 'Segoe UI', 'Arial', 'sans-serif'],
).set(
    body_background_fill='#eceaff', body_background_fill_dark='#eceaff',
    body_text_color='#16132e', body_text_color_dark='#16132e',
    body_text_color_subdued='#5b5877', body_text_color_subdued_dark='#5b5877',
    background_fill_primary='#ffffff', background_fill_primary_dark='#ffffff',
    background_fill_secondary='#f7f7ff', background_fill_secondary_dark='#f7f7ff',
    block_background_fill='transparent', block_background_fill_dark='transparent',
    block_border_color='rgba(255,255,255,.8)', block_border_color_dark='rgba(255,255,255,.8)',
    block_label_background_fill='rgba(255,255,255,.85)', block_label_background_fill_dark='rgba(255,255,255,.85)',
    block_label_text_color='#475467', block_label_text_color_dark='#475467',
    block_title_text_color='#2b2750', block_title_text_color_dark='#2b2750',
    input_background_fill='rgba(255,255,255,.82)', input_background_fill_dark='rgba(255,255,255,.82)',
    input_border_color='rgba(99,102,241,.28)', input_border_color_dark='rgba(99,102,241,.28)',
    input_placeholder_color='#9aa3b2', input_placeholder_color_dark='#9aa3b2',
    checkbox_label_background_fill='rgba(255,255,255,.82)', checkbox_label_background_fill_dark='rgba(255,255,255,.82)',
    checkbox_label_background_fill_hover='#ffffff', checkbox_label_background_fill_hover_dark='#ffffff',
    checkbox_label_background_fill_selected='#6d5dfc', checkbox_label_background_fill_selected_dark='#6d5dfc',
    checkbox_label_text_color_selected='#ffffff', checkbox_label_text_color_selected_dark='#ffffff',
    button_primary_background_fill='#6d5dfc', button_primary_background_fill_dark='#6d5dfc',
    button_primary_background_fill_hover='#5846e8', button_primary_background_fill_hover_dark='#5846e8',
    button_primary_text_color='#ffffff', button_primary_text_color_dark='#ffffff',
    button_secondary_background_fill='rgba(255,255,255,.82)', button_secondary_background_fill_dark='rgba(255,255,255,.82)',
    button_secondary_background_fill_hover='#ffffff', button_secondary_background_fill_hover_dark='#ffffff',
    button_secondary_text_color='#344054', button_secondary_text_color_dark='#344054',
    border_color_primary='rgba(99,102,241,.22)', border_color_primary_dark='rgba(99,102,241,.22)',
    border_color_accent='#c7cbf5', border_color_accent_dark='#c7cbf5',
    block_border_width='0px', block_border_width_dark='0px',
    block_shadow='none', block_shadow_dark='none',
)

# ---------------------------------------------------------------------------
# UI: static markup blocks (presentation only)
# ---------------------------------------------------------------------------
ROOM_SVG = """<svg viewBox="0 0 420 290" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustrated living room">
<defs>
<linearGradient id="ssw" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fde7d4"/><stop offset="1" stop-color="#f9c6e6"/></linearGradient>
<linearGradient id="sss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#67e8f9"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
<linearGradient id="ssf" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#6366f1"/></linearGradient>
<linearGradient id="ssg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3d5b5"/><stop offset="1" stop-color="#e2b78c"/></linearGradient>
</defs>
<rect width="420" height="290" fill="url(#ssw)"/>
<rect y="212" width="420" height="78" fill="url(#ssg)"/>
<rect x="48" y="36" width="132" height="130" rx="10" fill="url(#sss)" stroke="#fff" stroke-width="6"/>
<path d="M114 36v130M48 101h132" stroke="#fff" stroke-width="4"/>
<circle cx="86" cy="70" r="14" fill="#fde68a"/>
<rect x="222" y="40" width="74" height="56" rx="6" fill="#fff" opacity=".72"/>
<circle cx="248" cy="62" r="12" fill="#f472b6"/><circle cx="272" cy="70" r="10" fill="#fbbf24"/>
<path d="M230 90l18-13 14 9 20-15 8 9v10z" fill="#34d399" opacity=".85"/>
<ellipse cx="256" cy="252" rx="150" ry="20" fill="#ec4899" opacity=".32"/>
<rect x="164" y="212" width="8" height="16" rx="3" fill="#4c1d95"/><rect x="340" y="212" width="8" height="16" rx="3" fill="#4c1d95"/>
<rect x="170" y="124" width="178" height="62" rx="20" fill="#7c5cf0"/>
<rect x="156" y="150" width="206" height="62" rx="20" fill="url(#ssf)"/>
<rect x="148" y="138" width="34" height="78" rx="16" fill="#7c5cf0"/><rect x="334" y="138" width="34" height="78" rx="16" fill="#7c5cf0"/>
<rect x="196" y="138" width="46" height="40" rx="12" fill="#f472b6" transform="rotate(-6 219 158)"/>
<rect x="288" y="140" width="44" height="38" rx="12" fill="#fbbf24" transform="rotate(6 310 159)"/>
<path d="M396 224V120" stroke="#4c1d95" stroke-width="4" stroke-linecap="round"/><path d="M380 120l8-28h16l8 28z" fill="#fde68a"/>
<path d="M92 236h34l-4 30h-26z" fill="#f97316"/>
<ellipse cx="109" cy="208" rx="10" ry="26" fill="#10b981"/>
<ellipse cx="93" cy="216" rx="9" ry="22" fill="#34d399" transform="rotate(-28 93 216)"/>
<ellipse cx="125" cy="216" rx="9" ry="22" fill="#059669" transform="rotate(28 125 216)"/>
</svg>"""

HERO_HTML = f"""<div id="hero">
<div class="nav"><b><span class="logo"><i class="ico ico-sparkles"></i></span>StyleScape <span class="brand-divider">/</span> Interior Studio</b><span class="studio-badge"><i class="ico ico-wand"></i>Your personal design studio</span></div>
<div class="hero-grid">
<div class="hero-copy">
<h1>Reimagine your space.</h1>
<p>A room you know. A look you love. Bring your interior ideas to life with a photo and a little inspiration.</p>
<div class="workflow"><span><i class="ico ico-upload"></i>01 &nbsp; Upload a room</span><span><i class="ico ico-palette"></i>02 &nbsp; Define your style</span><span><i class="ico ico-sparkles"></i>03 &nbsp; Explore your design</span></div>
</div>
<div class="hero-art">
<div class="room-card">{ROOM_SVG}</div>
<div class="chip chip-a"><span class="chip-ico g2"><i class="ico ico-layers"></i></span><span>Up to 4 concepts<small>Compare side by side</small></span></div>
<div class="chip chip-b"><span class="chip-ico g4"><i class="ico ico-columns"></i></span><span>Before / after<small>See the transformation</small></span></div>
<!-- <div class="chip chip-c"><span class="dots"><i style="background:#E8DDCC"></i><i style="background:#A87652"></i><i style="background:#536451"></i></span><span>Your palette</span></div> -->
</div>
</div>
</div>"""

TIPS_HTML = """<div class="side-card"><div><h4><i class="ico ico-camera"></i>Photo tips</h4><p class="lead">Better photos make better concepts.</p></div>
<div class="tips-group">
<div class="tip"><span class="tip-ico g1"><i class="ico ico-sun"></i></span><div><b>Use natural light</b><span>Daylight shows true colors and textures.</span></div></div>
<div class="tip"><span class="tip-ico g2"><i class="ico ico-maximize"></i></span><div><b>Capture the full room</b><span>Step back so walls and furniture fit in frame.</span></div></div>
<div class="tip"><span class="tip-ico g3"><i class="ico ico-camera"></i></span><div><b>Shoot straight on</b><span>Hold your camera level for cleaner results.</span></div></div>
<div class="tip"><span class="tip-ico g4"><i class="ico ico-sparkles"></i></span><div><b>Clear the clutter</b><span>A tidy room gives the design more space to shine.</span></div></div>
</div></div>"""

STYLE_TIPS_HTML = """<div class="side-card"><div><h4><i class="ico ico-sparkles"></i>Style tips</h4><p class="lead">How our AI personalizes your room.</p></div>
<div class="tips-group">
<div class="tip"><span class="tip-ico g1"><i class="ico ico-layers"></i></span><div><b>Preserves room architecture</b><span>Core walls, windows, and layout remain in place.</span></div></div>
<div class="tip"><span class="tip-ico g2"><i class="ico ico-wand"></i></span><div><b>Curated authentic aesthetics</b><span>Handcrafted Indian heritage and modern finishes.</span></div></div>
<div class="tip"><span class="tip-ico g3"><i class="ico ico-columns"></i></span><div><b>Compare multiple concepts</b><span>Generate 1 to 4 distinct variations side by side.</span></div></div>
<div class="tip"><span class="tip-ico g4"><i class="ico ico-download"></i></span><div><b>High-resolution downloads</b><span>Download your favorites in crisp PNG quality.</span></div></div>
</div></div>"""

# PALETTE_HTML = """<div class="side-card"><h4><i class="ico ico-palette"></i>Color palette</h4><p class="lead">Your concepts are designed around this palette.</p>
# <div class="palette-row"><span class="swatch" style="background:#E8DDCC"></span><div><b>Wall</b><span><code>#E8DDCC</code> warm sand</span></div></div>
# <div class="palette-row"><span class="swatch" style="background:#A87652"></span><div><b>Secondary</b><span><code>#A87652</code> walnut</span></div></div>
# <div class="palette-row"><span class="swatch" style="background:#536451"></span><div><b>Accent</b><span><code>#536451</code> sage</span></div></div></div>"""
PALETTE_HTML = ""

ADMIN_HERO_HTML = """<div id="hero"><div class="nav"><b><span class="logo"><i class="ico ico-sparkles"></i></span>StyleScape <span class="brand-divider">/</span> Admin</b><a href="/">Back to studio <i class="ico ico-arrow-up-right"></i></a></div><h1>Studio settings.</h1><p>Manage your generation connection securely.</p></div>"""

SIGNOUT_HTML = '<a class="signout" href="/admin/logout"><i class="ico ico-log-out"></i>Sign out</a>'


def section_title(icon, text, gradient='g4'):
    return f'<div class="sec-title"><span class="sec-icon {gradient}"><i class="ico ico-{icon}"></i></span>{text}</div>'


def find_available_port(start_port=7860, attempts=20):
    for port in range(start_port, start_port + attempts):
        with socket() as sock:
            if sock.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError('No available application port.')

def preview(room, style, wall, prompt, secondary, accent):
    try:
        return build_prompt(room, style, wall, prompt, secondary, accent)
    except ValidationError as exc:
        return str(exc)

def stream_redesign(image, room, style, wall, prompt, secondary, accent, strength, guidance, steps, count):
    """Publish completed PNGs immediately and retain them if a later request fails."""
    gallery, paths = [], []
    try:
        validate_inputs(image, room, style, wall)
        brief = build_prompt(room, style, wall, prompt, secondary, accent)
        save_uploaded_image(image)
        total = max(1, min(4, int(count)))
        yield gallery.copy(), f'Generating concept 1 of {total}. This may take a few minutes.', paths.copy(), image, None
        for generated in iter_redesign_variations(image, prompt=brief, room_type=room, style=style, wall_color=wall,
                custom_prompt=prompt, strength=float(strength), guidance_scale=float(guidance), num_inference_steps=int(steps), count=total):
            path = save_generated_image(generated)
            paths.append(path)
            gallery.append((path, f'{style} / Concept {len(paths)}'))
            message = f'{len(paths)} of {total} concepts ready.'
            if len(paths) < total:
                message += f' Generating concept {len(paths) + 1}...'
            yield gallery.copy(), message, paths.copy(), image, path
        if not paths:
            raise RuntimeError('The generator returned no images. Please try again.')
        yield gallery.copy(), f'{len(paths)} concepts ready. Select an image to explore the details.', paths.copy(), image, paths[0]
    except Exception as exc:
        import requests
        if isinstance(exc, (ValidationError, RuntimeError)):
            message = str(exc)
        elif isinstance(exc, requests.Timeout):
            message = 'The image provider timed out. Please try again.'
        elif isinstance(exc, requests.ConnectionError):
            message = 'Cannot connect to the image provider. Check your internet connection and try again.'
        else:
            message = f'Generation could not finish ({type(exc).__name__}). Please try again or check your local runtime.'
        if paths:
            message = f'{len(paths)} concepts saved and available below. Remaining generation stopped: ' + message
        yield gallery.copy(), message, paths.copy(), image, (paths[0] if paths else None)


def run_redesign(*args, **kwargs):
    """Return the final state for non-streaming callers."""
    return list(stream_redesign(*args, **kwargs))[-1]


def save_api_key(key):
    key = (key or '').strip()
    if not key or len(key) < 10 or any(c.isspace() for c in key) or any(c in key for c in "'\"#="):
        return '', 'Enter a valid API key without spaces or quotes. The existing key was kept.'
    with SETTINGS_LOCK:
        temporary = None
        try:
            lines = ENV_PATH.read_text(encoding='utf-8-sig').splitlines() if ENV_PATH.exists() else []
            lines = [line for line in lines if line.split('=', 1)[0].strip().removeprefix('export ').strip() != 'STABILITY_API_KEY']
            lines.append('STABILITY_API_KEY=' + key)
            private_dir = ENV_PATH.parent / '.settings-private'
            private_dir.mkdir(exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=private_dir, prefix='.stylescape-key-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write('\n'.join(lines) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(ENV_PATH)
            os.environ['STABILITY_API_KEY'] = key
        except OSError:
            return '', 'Settings could not be saved. Check server file permissions. The active key was not changed.'
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink(missing_ok=True)
    return '', 'API key saved to .env. The next cloud request uses the new key without restarting. Saving does not add provider credits.'


def admin_settings_status():
    return 'API key is configured. Enter a new key to replace it.' if get_api_key() else 'No API key configured. Enter a Stability AI key and save.'


MAX_KEY_FIELDS = 20


def show_key_fields(count):
    count = max(0, min(MAX_KEY_FIELDS, int(count or 0)))
    return [gr.update(visible=i < count, value='' if i < count else None) for i in range(MAX_KEY_FIELDS)]


def add_pool_keys(*key_values):
    keys_text = '\n'.join(v for v in key_values if v and v.strip())
    message = key_pool.add_keys(keys_text)
    cleared = [gr.update(value='') for _ in key_values]
    return [*cleared, keys_table_rows(), message]


def keys_table_rows():
    return [[entry['masked'], entry['used_count'], entry['status']] for entry in key_pool.list_keys()]


def goto_step1():
    return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

def goto_hero():
    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

def step1_next(image):
    if image is None:
        return gr.update(visible=True), gr.update(visible=False), '### Please upload a room photo to continue.'
    return gr.update(visible=False), gr.update(visible=True), ''

def step2_next(image, room, style, wall):
    try:
        validate_inputs(image, room, style, wall)
    except ValidationError as exc:
        raise gr.Error(str(exc))
    return gr.update(visible=False), gr.update(visible=True), ''


def build_interface():
    defaults = get_runtime_defaults()
    with gr.Blocks(title='StyleScape | Interior Studio') as demo:
        with gr.Column(elem_id='hero-screen', visible=True) as hero_screen:
            gr.HTML(HERO_HTML)
            start = gr.Button('Start designing', variant='primary', elem_id='start-cta')

        with gr.Column(elem_id='step1-screen', elem_classes='step-screen', visible=False) as step1_modal:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="modal-step-track"><span class="active"></span><span></span><span></span></div>')
                    gr.Markdown('### <span class="step-badge">1</span>Your room <span class="ico ico-image title-ico"></span>\nStart with a clear, well-lit photo of your space.')
                with gr.Column(scale=1, min_width=48):
                    close_1 = gr.Button('✕', elem_classes='step-close')
            with gr.Row(elem_classes='split-row'):
                with gr.Column(scale=3, min_width=380, elem_classes='media-col'):
                    image = gr.Image(label='Room photo', type='pil', sources=['upload'], height=410, elem_id='room-upload')
                with gr.Column(scale=2, min_width=300, elem_classes='tips-col'):
                    gr.HTML(TIPS_HTML)
            with gr.Row(elem_classes='step-footer'):
                step1_error = gr.Markdown('', elem_classes='modal-error')
                save_next_1 = gr.Button('Save & next', variant='primary', elem_id='save-next-1')

        with gr.Column(elem_id='step2-screen', elem_classes='step-screen', visible=False) as step2_modal:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="modal-step-track"><span class="active"></span><span class="active"></span><span></span></div>')
                    gr.Markdown('### <span class="step-badge">2</span>Style & space <span class="ico ico-palette title-ico"></span>\nSelect your room type, interior aesthetic, and concept count.')
                with gr.Column(scale=1, min_width=48):
                    close_2 = gr.Button('✕', elem_classes='step-close')
            with gr.Row(elem_classes='split-row'):
                with gr.Column(scale=3, min_width=380, elem_classes='controls-col'):
                    with gr.Row():
                        room = gr.Dropdown(ROOM_TYPES, value=ROOM_TYPES[0], label='Room type')
                        style = gr.Dropdown(STYLES, value=STYLES[0], label='Interior style')
                    count = gr.Radio([1, 2, 3, 4], value=2, label='Number of design concepts', info='Each option is a different generated design for you to compare.')
                    # Fixed, code-level defaults (not shown to the user): free-text prompt is left blank,
                    # colors use the default palette, and generation quality settings use the runtime defaults below.
                    wall = gr.Textbox(value='#E8DDCC', visible=False)
                    secondary = gr.Textbox(value='#A87652', visible=False)
                    accent = gr.Textbox(value='#536451', visible=False)
                    prompt = gr.Textbox(value='', visible=False)
                    strength = gr.Number(value=.55, visible=False)
                    guidance = gr.Number(value=12, visible=False)
                    steps = gr.Number(value=max(20, defaults['num_inference_steps']), visible=False)
                with gr.Column(scale=2, min_width=300, elem_classes='tips-col'):
                    gr.HTML(STYLE_TIPS_HTML)
            with gr.Row(elem_classes='step-footer'):
                step2_error = gr.Markdown('', elem_classes='modal-error')
                save_next_2 = gr.Button('Save & next', variant='primary', elem_id='save-next-2')

        with gr.Column(elem_id='output-screen', elem_classes='step-screen', visible=False) as output_screen:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="output-header"><span class="studio-badge" style="background:linear-gradient(135deg,#6366f1,#d946ef);border-color:rgba(255,255,255,.7);box-shadow:0 8px 20px rgba(139,92,246,.4);"><i class="ico ico-sparkles"></i>03 / Your design</span></div>')
                    gr.Markdown('### Your interior concepts <span class="ico ico-sparkles title-ico"></span>\nYour finished designs appear here as soon as they are ready.')
                with gr.Column(scale=1, min_width=48):
                    close_3 = gr.Button('✕', elem_classes='step-close')
            with gr.Row(elem_classes='split-row'):
                with gr.Column(scale=3, min_width=420):
                    gallery = gr.Gallery(label='Generated interiors', columns=2, object_fit='contain', height=490, interactive=False, format='png', preview=True, selected_index=0, elem_id='interior-gallery')
                with gr.Column(scale=2, min_width=300, elem_classes='tips-col'):
                    gr.HTML(section_title('wand', 'Progress', 'g2'))
                    status = gr.Textbox(value='Generating your concepts...', label='Generation status', interactive=False, lines=2, elem_id='generation-status')
                    gr.HTML(section_title('download', 'Downloads', 'g3'))
                    downloads = gr.File(label='Your generated files', file_count='multiple', interactive=False)
            gr.HTML(section_title('columns', 'Before / after', 'g4'))
            with gr.Row(elem_id='before-after'):
                original_view = gr.Image(label='Original room', interactive=False, height=320)
                generated_view = gr.Image(label='Generated design', interactive=False, height=320)

        start.click(goto_step1, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_1.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_2.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_3.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        save_next_1.click(step1_next, [image], [step1_modal, step2_modal, step1_error], api_name=False)
        save_next_2.click(
            step2_next, [image, room, style, wall], [step2_modal, output_screen, step2_error], api_name=False
        ).success(
            stream_redesign, [image, room, style, wall, prompt, secondary, accent, strength, guidance, steps, count],
            [gallery, status, downloads, original_view, generated_view], concurrency_limit=1, api_name=False,
        )
    return demo


def admin_auth(username, password):
    return secrets.compare_digest(username.encode(), b'admin') and secrets.compare_digest(password.encode(), get_admin_password().encode())

def create_app():
    server = FastAPI()
    with gr.Blocks(title='StyleScape | Admin') as admin:
        gr.HTML(ADMIN_HERO_HTML)
        with gr.Row(elem_classes='split-row'):
            with gr.Column(scale=2, min_width=340, elem_classes='glass-card'):
                gr.Markdown('### <span class="step-badge"><span class="ico ico-key"></span></span>Stability AI API key\nThe saved key is never displayed. Replacing it updates future cloud requests without restarting. Local GPU generation takes priority when available.')
                key = gr.Textbox(label='New API key', type='password', placeholder='Paste your Stability AI key')
                save = gr.Button('Save API key', variant='primary', elem_id='save-key-btn')
                status = gr.Textbox(label='Settings status', interactive=False)

            with gr.Column(scale=3, min_width=420, elem_classes='glass-card'):
                gr.Markdown('### <span class="step-badge"><span class="ico ico-database"></span></span>API key pool\nChoose how many keys you want to add, paste each one into its own field, then save them all at once. The studio uses one key at a time; once the provider reports it as invalid/expired, the next one takes over automatically.')
                key_count = gr.Number(label='Number of keys to add', value=1, precision=0, minimum=0, maximum=MAX_KEY_FIELDS)
                key_fields = [gr.Textbox(label=f'Key {i + 1}', type='password', visible=i == 0) for i in range(MAX_KEY_FIELDS)]
                save_keys_btn = gr.Button('Save keys to pool', variant='primary', elem_id='save-pool-btn')
                pool_status = gr.Textbox(label='Pool status', interactive=False)
                keys_table = gr.Dataframe(headers=['Key', 'Used', 'Status'], value=keys_table_rows(), interactive=False, row_count=(0, 'dynamic'))

        admin.load(admin_settings_status, outputs=status, api_name=False, queue=False)
        save.click(save_api_key, key, [key, status], api_name=False, queue=False)
        key.submit(save_api_key, key, [key, status], api_name=False, queue=False)
        key_count.change(show_key_fields, key_count, key_fields, api_name=False, queue=False)
        save_keys_btn.click(add_pool_keys, key_fields, [*key_fields, keys_table, pool_status], api_name=False, queue=False)
        admin.load(keys_table_rows, outputs=keys_table, api_name=False, queue=False)

        gr.HTML(SIGNOUT_HTML)
    server = gr.mount_gradio_app(server, admin, path='/admin', auth=admin_auth, auth_message='StyleScape Admin - sign in with your admin username and password.', css=CSS, theme=THEME, blocked_paths=[str(ENV_PATH.parent / '.settings-private'), str(ENV_PATH), str(ENV_PATH.with_suffix('.env.tmp'))], max_file_size='20mb')
    studio = build_interface()
    studio.queue(max_size=5, default_concurrency_limit=1)
    return gr.mount_gradio_app(server, studio, path='/', css=CSS, theme=THEME, blocked_paths=[str(ENV_PATH.parent / '.settings-private'), str(ENV_PATH), str(ENV_PATH.with_suffix('.env.tmp'))], max_file_size='20mb')

if __name__ == '__main__':
    import uvicorn
    port = find_available_port()
    print(f'StyleScape: http://127.0.0.1:{port} | Admin: http://127.0.0.1:{port}/admin/')
    uvicorn.run(create_app(), host='127.0.0.1', port=port)