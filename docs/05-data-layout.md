# Data Directory Layout

All runtime data lives under the path configured by `LYW_DATA_DIR`
(default: `./data`). Access it exclusively through `lyw_core.storage.DataDir`.

## Structure

```
$LYW_DATA_DIR/
├── sources/    # original source PDFs, keyed by filename
├── lessons/    # derived lesson JSON snapshots
├── assets/     # content-addressed derived assets (images, chunks, etc.)
│   └── <xx>/  # two-char SHA-256 prefix shard
│       └── <full-sha256>[.ext]
└── indexes/    # BM25 and other serialised index files
```

## Usage

```python
from lyw_core.settings import Settings
from lyw_core.storage import DataDir

dd = DataDir(Settings().data_dir)
dd.bootstrap()                           # idempotent; call once at startup

path = dd.write_source("chapter.pdf", pdf_bytes)
asset_path = dd.write_asset(image_bytes, suffix=".png")
```

## Path safety

`DataDir` resolves all paths and rejects any name that would escape the
root (e.g. `../../etc/passwd`). A `ValueError` is raised on violation.

## Content-addressed assets

`write_asset` computes `sha256(data)` and stores the file at
`assets/<first2>/<full_digest>[suffix]`. Writing the same bytes twice
returns the same path without overwriting.
