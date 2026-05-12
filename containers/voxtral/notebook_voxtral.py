"""
notebook_voxtral.py — Benchmark: Voxtral
========================================
Run:
    docker compose run voxtral
"""

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import pipeline

sys.path.insert(0, "/app/src")

from metrics import BenchmarkMetrics
from normalizer import MedicalNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

MODEL_NAME = "mistralai/Voxtral-Mini-3B-2507"

DATASET_PATH = Path("dataset/test_set_frozen.json")
AUDIO_BASE_DIR = Path("audio")

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

RESULTS_PATH = RESULTS_DIR / "results_voxtral.csv"

# ─────────────────────────────────────────────────────────────
# Load dataset
# ─────────────────────────────────────────────────────────────

with open(DATASET_PATH, encoding="utf-8") as f:
    dataset = json.load(f)

segments = dataset["segments"]
fingerprint = dataset["dataset_fingerprint"]

log.info(f"Dataset fingerprint: {fingerprint}")
log.info(f"Segments: {len(segments)}")
log.info(f"Total audio: {dataset['total_duration_s']:.1f}s")

# ─────────────────────────────────────────────────────────────
# Device
# ─────────────────────────────────────────────────────────────

if torch.cuda.is_available():
    device = 0
    dtype = torch.float16
    device_name = "cuda"
    log.info("Using GPU")
else:
    device = -1
    dtype = torch.float32
    device_name = "cpu"
    log.info("Using CPU")

# ─────────────────────────────────────────────────────────────
# Load model
# ─────────────────────────────────────────────────────────────

log.info(f"Loading {MODEL_NAME}...")

pipe = pipeline(
    task="automatic-speech-recognition",
    model=MODEL_NAME,
    torch_dtype=dtype,
    device=device,
)

log.info("Model loaded ✓")

# ─────────────────────────────────────────────────────────────
# Benchmark helpers
# ─────────────────────────────────────────────────────────────

norm = MedicalNormalizer()
metrics = BenchmarkMetrics()

# ─────────────────────────────────────────────────────────────
# Transcription
# ─────────────────────────────────────────────────────────────

def transcribe(audio_path: Path):

    t0 = time.perf_counter()

    result = pipe(
        str(audio_path),
        generate_kwargs={
            "language": "fr",
        }
    )

    latency = time.perf_counter() - t0

    text = result["text"].strip()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return text, latency

# ─────────────────────────────────────────────────────────────
# Run benchmark
# ─────────────────────────────────────────────────────────────

records = []

for idx, seg in enumerate(segments):

    seg_id = seg["segment_id"]
    audio_path = AUDIO_BASE_DIR / seg["audio_file"]
    duration_s = seg["duration_s"]
    gt_norm = seg["ground_truth_normalized"]

    log.info(f"[{idx+1}/{len(segments)}] {seg_id}")

    if not audio_path.exists():
        log.warning(f"Audio not found: {audio_path}")
        continue

    try:
        raw_text, latency = transcribe(audio_path)

    except Exception as e:
        log.error(f"Failed: {e}")
        raw_text = "[ERROR]"
        latency = -1.0

    hyp_norm = norm.normalize(raw_text)

    result = metrics.compute(
        ref=gt_norm,
        hyp=hyp_norm,
        latency_s=latency,
        audio_duration_s=duration_s,
        cost_per_minute=0.0,
    )

    log.info(
        f"WER={result.wer:.3f} | "
        f"CER={result.cer:.3f} | "
        f"RTF={result.rtf:.3f}"
    )

    if result.med_critical_errors:
        for err in result.med_critical_errors:
            log.warning(f"⚠️ {err}")

    log.info(f"REF: {gt_norm[:120]}")
    log.info(f"HYP: {hyp_norm[:120]}")

    records.append({
        "model": "voxtral",
        "device": device_name,
        "compute_type": str(dtype),
        "segment_id": seg_id,
        "audio_file": seg["audio_file"],
        "duration_s": duration_s,
        "hypothesis_raw": raw_text,
        "hypothesis_norm": hyp_norm,
        "reference_norm": gt_norm,
        "dataset_fingerprint": fingerprint,
        **result.to_dict(),
    })

# ─────────────────────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────────────────────

df = pd.DataFrame(records)

df["run_timestamp"] = pd.Timestamp.now(tz="UTC").isoformat()

df.to_csv(
    RESULTS_PATH,
    index=False,
    encoding="utf-8"
)

log.info(f"Results saved → {RESULTS_PATH}")

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"RESULTS — Voxtral ({device_name})")
print("=" * 60)

print(f"Segments:        {len(df)}")
print(f"Mean WER:        {df['wer'].mean():.3f}")
print(f"Mean CER:        {df['cer'].mean():.3f}")
print(f"Med entity acc:  {df['med_entity_acc'].mean():.3f}")
print(f"Mean RTF:        {df['rtf'].mean():.3f}")
print(f"Mean latency:    {df['latency_s'].mean():.1f}s")

n_crit = df["med_critical_errors"].apply(
    lambda x: 1 if x and x != "" else 0
).sum()

print(f"Critical errors: {n_crit}")
print(f"Dataset:         {fingerprint}")

print("=" * 60)