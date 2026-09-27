# StyleScape Interior Studio

Upload a room photo and explore interior concepts guided by your chosen style, color palette, and written brief.

## Run

```powershell
pip install -r requirements.txt
python app.py
```

Open the localhost URL printed in the terminal (normally http://127.0.0.1:7860).

## Design your room

1. Upload a well-lit room photo. It appears once, in the upload panel.
2. Choose a room type and interior style.
3. Select a coordinated palette or edit the wall, furniture, and accent colors with the color pickers.
4. Write optional instructions for furniture, materials, lighting, or details to preserve. Inspect the assembled prompt to see the design brief.
5. Choose one, two, or four concepts and generate. Each completed interior appears immediately in the results gallery with a PNG download. If a later request fails, completed concepts remain available.

Creative freedom controls how much the design changes. Lower values favor preservation. Quality steps and prompt guidance apply to local generation; cloud generation uses the provider's own quality settings. Each cloud concept makes a separate paid API request.

All variations follow the selected style and palette with different seeds. The input is resized without center-cropping, retaining the full room frame. Local SDXL uses edge and depth controls; cloud generation uses Stability AI structure control. These improve structural consistency but cannot guarantee exact geometry, furniture placement, or color matching. A photo remains required; the written prompt guides its redesign.

## Separate admin login

Visit `/admin/` on the same server.

- Username: `admin`
- Password: `123456`

Enter a Stability AI API key and select **Save API key**. Settings are stored in the local `.env` file and applied to subsequent cloud requests without restarting. The saved key is never returned to the browser. Saving checks formatting; the provider checks validity during generation. Sign out using the admin page's sign-out link.

The requested default password is intended for this local setup. Set `STYLESCAPE_ADMIN_PASSWORD` in your environment or `.env` to change it before sharing access. The app binds to localhost. `.env` is excluded from version control and blocked from Gradio file serving.

Cloud generation is selected on CPU when a key exists. Available CUDA or Apple MPS hardware takes priority and uses the local model. Cloud generation sends the uploaded photo and prompt to Stability AI. Local GPU setup is described in [GPU_SETUP.md](GPU_SETUP.md).

## Files

- `app.py`: studio interface, separate authenticated admin app, settings persistence.
- `generate.py`: local SDXL ControlNet and cloud structure generation.
- `utils.py`: palettes, prompt assembly, validation, image resizing and storage.
- `uploads/`: saved input photos.
- `outputs/`: generated PNGs.

## Verification

```powershell
python -m unittest test_app -v
```

Tests cover prompt and palette propagation into mocked provider requests, full-frame resizing, API key persistence, input validation, and HTTP admin authentication. They do not spend API credits or run local model inference. Actual output quality depends on the input photograph, model, provider availability, and generation settings.

## Interior training dataset

A downloaded room-image dataset and reproducible preparation script are included locally. See [data/README.md](data/README.md) for the source, train/validation layout, caption format and quality limitations. This is a low-resolution training baseline; adding it does not train a model or replace the paid generation backend.


Admin key updates are now read from `.env` on every cloud request, including across updated server processes. A saved key overrides an inherited environment key. The admin Save action runs immediately, and the password field clears after saving. Visit `/admin/` directly (the studio intentionally has no admin button). Username is `admin`; the default password is `123456` unless `STYLESCAPE_ADMIN_PASSWORD` overrides it. An empty password setting falls back to the default. Restart older app processes once to load this code change; subsequent key updates need no restart.


Architecture preservation is the default: decor change intensity is limited to 0.25?0.45 (default 0.35), cloud structure control stays at 0.85?1.0, and local edge/depth conditioning is strengthened. Variation count is under Advanced quality settings. These controls reduce structural drift but do not guarantee exact architectural preservation; no live output quality claim has been verified.
