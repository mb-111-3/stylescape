"""Download and prepare the pinned House Rooms dataset; no training is started."""
import argparse
from collections import Counter, defaultdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import zipfile

from PIL import Image, ImageOps, UnidentifiedImageError
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.kaggle.com/datasets/robinreni/house-rooms-image-dataset'
URL = 'https://www.kaggle.com/api/v1/datasets/download/robinreni/house-rooms-image-dataset?datasetVersionNumber=1'
SHA256 = '37f131d9183749e5a4d14fd03838f19eb1e272151fc3ab44a8d181852b9ea013'
LABELS = {'Bathroom': 'bathroom', 'Bedroom': 'bedroom', 'Dinning': 'dining room', 'Kitchen': 'kitchen', 'Livingroom': 'living room'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and digest(path) == SHA256:
        return
    partial = path.with_suffix('.part')
    with requests.get(URL, stream=True, timeout=(15, 60)) as response:
        response.raise_for_status()
        with partial.open('wb') as stream:
            for chunk in response.iter_content(1024 * 1024):
                stream.write(chunk)
    if digest(partial) != SHA256:
        raise ValueError('Dataset checksum differs from the reviewed version. Archive not installed.')
    partial.replace(path)


def prepare(archive, output, min_size=224):
    if output.exists():
        raise ValueError(f'{output} already exists. Choose a new --output folder to preserve existing captions.')
    if digest(archive) != SHA256:
        raise ValueError('Source archive checksum mismatch.')
    groups = defaultdict(list)
    seen = set()
    rejected = Counter()
    sizes = Counter()
    with zipfile.ZipFile(archive) as source:
        for name in sorted(source.namelist()):
            parts = Path(name).parts
            if len(parts) != 3 or parts[1] not in LABELS:
                rejected['unknown_category'] += 1
                continue
            try:
                with Image.open(BytesIO(source.read(name))) as original:
                    im = ImageOps.exif_transpose(original).convert('RGB')
                    im.load()
                if min(im.size) < min_size:
                    rejected['too_small'] += 1
                    continue
                pixel_hash = hashlib.sha256(str(im.size).encode() + im.tobytes()).hexdigest()
                if pixel_hash in seen:
                    rejected['exact_duplicate'] += 1
                    continue
                seen.add(pixel_hash)
                sizes[f'{im.width}x{im.height}'] += 1
                groups[LABELS[parts[1]]].append((name, pixel_hash))
            except (UnidentifiedImageError, OSError):
                rejected['unreadable'] += 1
        if not groups:
            raise ValueError('No images passed the resolution filter; no prepared folder created.')
        output.mkdir(parents=True)
        counts = {}
        manifest = []
        split_rows = {'train': [], 'validation': []}
        for label, records in sorted(groups.items()):
            random.Random(42).shuffle(records)
            validation_count = max(1, round(len(records) * .1))
            counts[label] = {'train': len(records) - validation_count, 'validation': validation_count}
            for index, (name, pixel_hash) in enumerate(records):
                split = 'validation' if index < validation_count else 'train'
                filename = label.replace(' ', '_') + '_' + pixel_hash[:16] + '.png'
                folder = output / split
                folder.mkdir(exist_ok=True)
                with Image.open(BytesIO(source.read(name))) as im:
                    ImageOps.exif_transpose(im).convert('RGB').save(folder / filename)
                caption = f'A photograph of a {label} interior.'
                split_rows[split].append({'file_name': filename, 'text': caption})
                manifest.append({'file_name': f'{split}/{filename}', 'source_file': name, 'room_type': label, 'pixel_sha256': pixel_hash, 'caption_method': 'room-label template, not manually reviewed'})
        for split, rows in split_rows.items():
            (output / split / 'metadata.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        (output / 'manifest.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in manifest), encoding='utf-8')
        report = {'source': SOURCE, 'source_version': 1, 'archive_sha256': SHA256, 'publisher_license': 'CC0: Public Domain', 'seed': 42, 'counts': counts, 'rejected': dict(rejected), 'image_sizes': dict(sizes), 'total_prepared': len(manifest), 'limitations': ['Low-resolution baseline dataset; not suitable for high-detail SDXL training.', 'Room-label captions only; no verified style or color annotations.', 'No paired before/after redesigns.', 'Exact pixel duplicates removed; near-duplicate scenes may remain.']}
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'interior_rooms')
    parser.add_argument('--min-size', type=int, default=224)
    args = parser.parse_args()
    archive = ROOT / 'data' / 'raw' / 'house-rooms-v1.zip'
    download(archive)
    prepare(archive, args.output, args.min_size)
