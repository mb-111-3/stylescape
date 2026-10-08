"""StyleScape studio and authenticated API settings."""
import os
import secrets
from pathlib import Path
from socket import socket
from threading import Lock
import tempfile
from settings import read_env, get_admin_password, get_api_key

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
CSS = """
:root {--accent:#4f46e5; --accent-dark:#4338ca; --ink:#111827; --sub:#6b7280;}
.nav a[href="/admin"], .nav a[href="/admin/"] {display:none !important;}
body {background: #f5f6fa !important;}
.gradio-container {max-width: 1440px !important; margin: auto; background: transparent; color: var(--ink); color-scheme: light; padding: 0 32px 40px !important;}
#hero {padding: 40px 40px; margin: 24px 0 32px; border-radius: 20px; background: linear-gradient(135deg, #111827 0%, #312e81 55%, #4f46e5 100%); box-shadow: 0 12px 32px rgba(79,70,229,.25);}
#hero h1 {font-size: clamp(32px, 4vw, 52px); font-weight: 700; letter-spacing: -1.8px; line-height: 1.12; color: #ffffff; margin: 22px 0 14px;}
#hero p {color: #d7d9ff; max-width: 680px; font-size: 16px; line-height: 1.75;}
.nav {display:flex; justify-content:space-between; align-items:center; gap:16px; color:#fff; font-size:12px; letter-spacing:1.8px;}
.nav b {color:#fff;}
.nav a {color:#e4e6ff; background:rgba(255,255,255,.08); letter-spacing:0; font-weight:500; text-decoration:none; border:1px solid rgba(255,255,255,.25); border-radius:8px; padding:10px 16px; transition:background .15s, border-color .15s;}
.nav a:hover {background:rgba(255,255,255,.18); border-color:rgba(255,255,255,.5);}
.nav a:focus-visible {outline:3px solid #a5b4fc; outline-offset:3px;}
#generate {background: var(--accent); color: #fff; border:1px solid var(--accent); border-radius:12px; min-height:54px; font-weight:650; font-size:15.5px; box-shadow:0 8px 20px rgba(79,70,229,.35); transition:background .15s, transform .1s;}
#generate:hover {background:var(--accent-dark); border-color:var(--accent-dark); transform:translateY(-1px);}
.panel {background: #ffffff; border:1px solid #e4e7ec; border-radius:14px; padding:24px; box-shadow:0 3px 16px #10182805;}
.panel h3 {color:#344054; font-size:15px !important; font-weight:600; letter-spacing:.1px;}
#studio-layout {gap:24px; align-items:flex-start;}
.card-stack {gap:20px !important; background:transparent !important; border:0 !important;}
.design-card {padding:24px !important; background:#fff !important; border:1px solid #e5e7f0 !important; border-radius:18px !important; box-shadow:0 6px 24px rgba(17,24,39,.06); overflow:visible !important; transition:box-shadow .2s;}
.design-card:hover {box-shadow:0 10px 32px rgba(17,24,39,.09);}
.design-card > div {gap:16px;}
.design-card h3 {font-size:18px !important; font-weight:700; color:var(--ink) !important; margin:0 0 6px !important; display:flex; align-items:center;}
.design-card p {color:var(--sub); font-size:14px; line-height:1.6;}
.design-card label, .design-card .label {color:#344054 !important;}
.design-card input:not([type="range"]):not([type="color"]), .design-card textarea {color:var(--ink) !important; background:#fff !important; caret-color:var(--ink);}
.design-card input::placeholder, .design-card textarea::placeholder {color:#9aa3b2 !important; opacity:1;}
.design-card input:focus-visible, .design-card textarea:focus-visible, .design-card button:focus-visible {outline:2px solid var(--accent); outline-offset:2px;}
#room-upload, #interior-gallery {border:2px dashed #c7cbf5 !important; border-radius:14px; background:#f7f7ff !important;}
#interior-gallery {border-style:solid !important; border-color:#e5e7f0 !important;}
#room-upload button, #interior-gallery button {color:var(--accent);}
#generation-status {border:1px solid #e5e7f0; border-radius:10px;}
.studio-badge {font-size:12px; letter-spacing:0; font-weight:600; color:#fff; padding:8px 14px; border:1px solid rgba(255,255,255,.3); border-radius:30px; background:rgba(255,255,255,.12);}
.brand-divider {color:#a5b4fc; padding:0 8px;}
.workflow {display:flex; flex-wrap:wrap; gap:10px; margin-top:24px;}
.workflow span {padding:9px 14px; background:rgba(255,255,255,.1); color:#fff; font-size:12.5px; border:1px solid rgba(255,255,255,.25); border-radius:8px; font-weight:500;}
.step-badge {display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg, var(--accent), #7c3aed); color:#fff; font-size:13px; font-weight:700; margin-right:10px; box-shadow:0 3px 8px rgba(79,70,229,.35);}
.fine-print p {font-size:12px !important; line-height:1.6; color:#9aa3b2 !important;}
footer {display:none !important;}
#start-cta {background: #fff; color: var(--accent); border:0; border-radius:12px; min-height:50px; font-weight:650; font-size:15px; margin-top:28px; box-shadow:0 8px 20px rgba(0,0,0,.18); transition:transform .1s;}
#start-cta:hover {transform:translateY(-1px);}
.step-screen {width:100%; max-width:900px; margin:0 auto; min-height:calc(100vh - 48px); padding:40px 8px 24px; overflow:visible !important;}
.step-screen, .step-screen > div {overflow:visible !important; max-height:none !important;}
.step-header {align-items:flex-start !important; gap:8px; margin-bottom:8px;}
.step-header h3 {font-size:22px !important; font-weight:700 !important; display:flex; align-items:center; margin-top:4px !important;}
.modal-step-track {display:flex; gap:8px; margin-bottom:22px;}
.modal-step-track span {flex:1; height:4px; border-radius:4px; background:#e5e7f0;}
.modal-step-track span.active {background:var(--accent);}
.step-close {width:36px !important; height:36px !important; min-width:36px !important; padding:0 !important; border-radius:50% !important; background:#f2f2fb !important; color:#6b7280 !important; border:1px solid #e5e7f0 !important; font-size:16px !important; line-height:1 !important; box-shadow:none !important;}
.step-close:hover {background:#e5e7f0 !important; color:#111827 !important;}
#save-next-1, #save-next-2 {background:var(--accent); color:#fff; border:1px solid var(--accent); border-radius:12px; min-height:50px; font-weight:650; box-shadow:0 8px 20px rgba(79,70,229,.3); margin-top:16px;}
#save-next-1:hover, #save-next-2:hover {background:var(--accent-dark); border-color:var(--accent-dark);}
.modal-error {color:#dc2626 !important; font-size:13px !important; margin-top:-4px;}
#output-screen #interior-gallery {height:600px !important;}
.output-header {margin-bottom:4px;}
#room-upload button[aria-label="Share"], #interior-gallery button[aria-label="Share"],
#room-upload .share-button, #interior-gallery .share-button {display:none !important;}
@media (max-width: 640px) {
    .gradio-container {padding:0 16px 24px !important;}
    .panel, .design-card {padding:16px !important;}
    .nav {font-size:10px; letter-spacing:1px; flex-wrap:wrap;}
    #hero {padding:24px; margin:16px 0 20px;}
    #hero h1 {letter-spacing:-1px;}
    .step-screen {padding:20px 4px !important;}
}
"""
THEME = gr.themes.Soft(
    primary_hue='indigo', secondary_hue='violet', neutral_hue='slate', radius_size='lg',
    font=['Inter', 'Segoe UI', 'Arial', 'sans-serif'],
).set(
    body_background_fill='#f5f6fa', body_background_fill_dark='#f5f6fa',
    body_text_color='#111827', body_text_color_dark='#111827',
    body_text_color_subdued='#6b7280', body_text_color_subdued_dark='#6b7280',
    background_fill_primary='#ffffff', background_fill_primary_dark='#ffffff',
    background_fill_secondary='#f7f7ff', background_fill_secondary_dark='#f7f7ff',
    block_background_fill='#ffffff', block_background_fill_dark='#ffffff',
    block_border_color='#e5e7f0', block_border_color_dark='#e5e7f0',
    block_label_background_fill='#ffffff', block_label_background_fill_dark='#ffffff',
    block_label_text_color='#475467', block_label_text_color_dark='#475467',
    block_title_text_color='#344054', block_title_text_color_dark='#344054',
    input_background_fill='#ffffff', input_background_fill_dark='#ffffff',
    input_border_color='#d7d9ea', input_border_color_dark='#d7d9ea',
    input_placeholder_color='#9aa3b2', input_placeholder_color_dark='#9aa3b2',
    button_primary_background_fill='#4f46e5', button_primary_background_fill_dark='#4f46e5',
    button_primary_background_fill_hover='#4338ca', button_primary_background_fill_hover_dark='#4338ca',
    button_primary_text_color='#ffffff', button_primary_text_color_dark='#ffffff',
    button_secondary_background_fill='#ffffff', button_secondary_background_fill_dark='#ffffff',
    button_secondary_background_fill_hover='#f0f0ff', button_secondary_background_fill_hover_dark='#f0f0ff',
    button_secondary_text_color='#344054', button_secondary_text_color_dark='#344054',
    border_color_primary='#e5e7f0', border_color_primary_dark='#e5e7f0',
    border_color_accent='#c7cbf5', border_color_accent_dark='#c7cbf5',
    block_border_width='0px', block_border_width_dark='0px',
    block_shadow='none', block_shadow_dark='none',
)


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
        yield gallery.copy(), f'Generating concept 1 of {total}. This may take a few minutes.', paths.copy()
        for generated in iter_redesign_variations(image, prompt=brief, room_type=room, style=style, wall_color=wall,
                custom_prompt=prompt, strength=float(strength), guidance_scale=float(guidance), num_inference_steps=int(steps), count=total):
            path = save_generated_image(generated)
            paths.append(path)
            gallery.append((path, f'{style} / Concept {len(paths)}'))
            message = f'{len(paths)} of {total} concepts ready.'
            if len(paths) < total:
                message += f' Generating concept {len(paths) + 1}...'
            yield gallery.copy(), message, paths.copy()
        if not paths:
            raise RuntimeError('The generator returned no images. Please try again.')
        yield gallery.copy(), f'{len(paths)} concepts ready. Select an image to explore the details.', paths.copy()
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
        yield gallery.copy(), message, paths.copy()


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
            gr.HTML('<div id="hero"><div class="nav"><b>STYLESCAPE <span class="brand-divider">/</span> INTERIOR STUDIO</b><span class="studio-badge">Your personal design studio</span></div><h1>Reimagine your space.</h1><p>A room you know. A look you love. Bring your interior ideas to life with a photo, a palette, and a little inspiration.</p><div class="workflow"><span>01 &nbsp; Upload a room</span><span>02 &nbsp; Define your style</span><span>03 &nbsp; Explore your design</span></div></div>')
            start = gr.Button('Start designing →', elem_id='start-cta')

        with gr.Column(elem_id='step1-screen', elem_classes='step-screen', visible=False) as step1_modal:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="modal-step-track"><span class="active"></span><span></span><span></span></div>')
                    gr.Markdown('### <span class="step-badge">1</span>Your room\nStart with a clear, well-lit photo of your space.')
                with gr.Column(scale=1, min_width=48):
                    close_1 = gr.Button('✕', elem_classes='step-close')
            image = gr.Image(label='Room photo', type='pil', sources=['upload'], height=420, elem_id='room-upload')
            step1_error = gr.Markdown('', elem_classes='modal-error')
            save_next_1 = gr.Button('Save & next →', variant='primary', elem_id='save-next-1')

        with gr.Column(elem_id='step2-screen', elem_classes='step-screen', visible=False) as step2_modal:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="modal-step-track"><span class="active"></span><span class="active"></span><span></span></div>')
                    gr.Markdown('### <span class="step-badge">2</span>Style & color\nSet the mood with a style, palette and finishing touches.')
                with gr.Column(scale=1, min_width=48):
                    close_2 = gr.Button('✕', elem_classes='step-close')
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
            step2_error = gr.Markdown('', elem_classes='modal-error')
            save_next_2 = gr.Button('Save & next →', variant='primary', elem_id='save-next-2')

        with gr.Column(elem_id='output-screen', elem_classes='step-screen', visible=False) as output_screen:
            with gr.Row(elem_classes='step-header'):
                with gr.Column(scale=10, min_width=200):
                    gr.HTML('<div class="output-header"><span class="studio-badge" style="background:#f0f0ff;color:#4338ca;border-color:#d7d9ea;">03 / Your design</span></div>')
                    gr.Markdown('### Your interior concepts\nYour finished designs appear here as soon as they are ready.')
                with gr.Column(scale=1, min_width=48):
                    close_3 = gr.Button('✕', elem_classes='step-close')
            gallery = gr.Gallery(label='Generated interiors', columns=2, object_fit='contain', height=560, interactive=False, format='png', preview=True, selected_index=0, elem_id='interior-gallery')
            status = gr.Textbox(value='Generating your concepts...', label='Generation status', interactive=False, lines=2, elem_id='generation-status')
            downloads = gr.File(label='Your generated files', file_count='multiple', interactive=False)

        start.click(goto_step1, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_1.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_2.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        close_3.click(goto_hero, None, [hero_screen, step1_modal, step2_modal, output_screen], api_name=False)
        save_next_1.click(step1_next, [image], [step1_modal, step2_modal, step1_error], api_name=False)
        save_next_2.click(
            step2_next, [image, room, style, wall], [step2_modal, output_screen, step2_error], api_name=False
        ).success(
            stream_redesign, [image, room, style, wall, prompt, secondary, accent, strength, guidance, steps, count],
            [gallery, status, downloads], concurrency_limit=1, api_name=False,
        )
    return demo


def admin_auth(username, password):
    return secrets.compare_digest(username.encode(), b'admin') and secrets.compare_digest(password.encode(), get_admin_password().encode())

def create_app():
    server = FastAPI()
    with gr.Blocks(title='StyleScape | Admin') as admin:
        gr.HTML('<div id="hero"><div class="nav"><b>STYLESCAPE / ADMIN</b><a href="/">Back to studio ↗</a></div><h1>Studio settings.</h1><p>Manage your generation connection securely.</p></div>')
        gr.Markdown('### Stability AI API key\nThe saved key is never displayed. Replacing it updates future cloud requests without restarting. Local GPU generation takes priority when available.')
        key = gr.Textbox(label='New API key', type='password', placeholder='Paste your Stability AI key')
        save = gr.Button('Save API key', variant='primary')
        status = gr.Textbox(label='Settings status', interactive=False)
        admin.load(admin_settings_status, outputs=status, api_name=False, queue=False)
        save.click(save_api_key, key, [key, status], api_name=False, queue=False)
        key.submit(save_api_key, key, [key, status], api_name=False, queue=False)
        gr.HTML('<a href="/admin/logout">Sign out</a>')
    server = gr.mount_gradio_app(server, admin, path='/admin', auth=admin_auth, auth_message='StyleScape Admin - sign in with your admin username and password.', css=CSS, theme=THEME, blocked_paths=[str(ENV_PATH.parent / '.settings-private'), str(ENV_PATH), str(ENV_PATH.with_suffix('.env.tmp'))], max_file_size='20mb')
    studio = build_interface()
    studio.queue(max_size=5, default_concurrency_limit=1)
    return gr.mount_gradio_app(server, studio, path='/', css=CSS, theme=THEME, blocked_paths=[str(ENV_PATH.parent / '.settings-private'), str(ENV_PATH), str(ENV_PATH.with_suffix('.env.tmp'))], max_file_size='20mb')

if __name__ == '__main__':
    import uvicorn
    port = find_available_port()
    print(f'StyleScape: http://127.0.0.1:{port} | Admin: http://127.0.0.1:{port}/admin/')
    uvicorn.run(create_app(), host='127.0.0.1', port=port)
