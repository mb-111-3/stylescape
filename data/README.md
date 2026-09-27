# Interior training data

Source: [House Rooms Image Dataset, robinreni, version 1](https://www.kaggle.com/datasets/robinreni/house-rooms-image-dataset).
The publisher lists the dataset as **CC0: Public Domain**. This records the publisher's declaration, not an independent audit of each image's provenance.

## Included locally

- `raw/house-rooms-v1.zip`: pinned source archive (5,250 room images).
- `interior_rooms/train/`: training PNGs and `metadata.jsonl`.
- `interior_rooms/validation/`: held-out PNGs and `metadata.jsonl`.
- `interior_rooms/manifest.jsonl`: original filenames, labels, pixel hashes and caption provenance.
- `interior_rooms/report.json`: exact counts, exclusions, dimensions and source checksum.

The five labels are bathroom, bedroom, dining room, kitchen and living room. Exact pixel duplicates are removed before a deterministic per-category 90/10 split (seed 42). Near duplicates are not detected; review related scenes before using the validation split for quality claims.

## Reproduce

From the project root:

```powershell
python scripts/prepare_dataset.py --output data/interior_rooms_copy
```

The script reuses the verified archive, validates image decoding, preserves resolution, and creates an ImageFolder dataset. It refuses to overwrite an existing prepared folder, so caption edits are preserved. Downloaded archives must match the pinned SHA-256. No API key is needed. Python 3.11+ is required by this preparation script.

For Hugging Face Datasets, install `datasets` in your training environment, then load:

```python
from datasets import load_dataset
rooms = load_dataset('imagefolder', data_dir='data/interior_rooms')
print(rooms['train'][0]['text'])
```

The `image` and `text` columns match the standard [Diffusers image-caption preparation format](https://huggingface.co/docs/diffusers/training/create_dataset). Pass `data/interior_rooms/train` as the training data directory when using a compatible Diffusers LoRA training script. Keep validation images out of training.

## Quality and training limits

These are **224 x 224 images with basic room-label captions**. This is a baseline for data-loading and training experiments, not a production-quality interior fine-tuning set. Captions are templates such as `A photograph of a bedroom interior.` They do not claim verified colors, styles, lighting or furniture. Review images and replace captions with accurate descriptions before meaningful fine-tuning.

The dataset has no paired original/redesigned rooms and cannot directly teach exact before/after redesign behavior. For high-detail interior adaptation, obtain higher-resolution licensed photographs with descriptive captions. For supervised editing, obtain aligned input/output pairs and edit instructions.

Adding this dataset does not train a model, load a LoRA into the app, change the inference backend, or remove Stability API charges. Training and local inference are separate steps. No model training was started. Dataset images are not presented as generated app results.
