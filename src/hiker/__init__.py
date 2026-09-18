"""hiker: agentic novelty search over a finite archive of satellite image chips.

The package is organised as a four-step pipeline (ingest -> embed -> index -> hike)
plus a farthest-point-sampling baseline. Each step reads the previous step's files
from disk and is skipped when its output already exists, so nothing is recomputed.

Where things live:

- ``datasets/``  archive adapters. Adding a new archive means adding one file here.
- ``encoders/``  image encoders behind a tiny ``Encoder`` protocol.
- ``ingest.py``  adapter -> chips on disk + ``manifest.parquet``.
- ``embed.py``   manifest -> ``embeddings.npy`` (+ ``embed_meta.json``).
- ``index.py``   embeddings -> exact cosine FAISS index.
- ``scoring.py`` the novelty score and the softmax choice. Pure numpy, unit tested.
- ``agent.py``   one hiker: its private history and one step of the walk.
- ``hike.py``    runs all agents and writes the run directory.
- ``baseline.py`` farthest-point sampling, same log schema.
- ``io.py``      run directories, JSONL, geo/time helpers.
- ``viz.py``     novelty curve and sequence images.
"""

__version__ = "0.1.0"
