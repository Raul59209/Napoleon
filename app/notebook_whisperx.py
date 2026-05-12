"""
notebook_whisperx.py — Benchmark: WhisperX
===========================================
WhisperX adds forced word-level alignment and speaker diarization on top
of faster-whisper. For STT accuracy benchmarking we care about the
transcript text — alignment is a bonus.

Install:
    pip install whisperx

Note: WhisperX downloads a phoneme alignment model from HuggingFace
on first run (~1 GB). You may need a HF token for some alignment models:
    set HF_TOKEN=your_token_here

Run:
    python notebook_whisperx.py
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from Napoleon.containers.base.src.normalizer import MedicalNormalizer
from Napoleon.containers.base.src.metrics import BenchmarkMetrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_SIZE      = "large-v3"
LANGUAGE        = "fr"
DATASET_PATH    = Path("dataset/test_set_frozen.json")
AUDIO_BASE_DIR  = Path("audio")
RESULTS_DIR     = Path("results")
RESULTS_PATH    = RESULTS_DIR / "results_whisperx.csv"
RESULTS_DIR.mkdir(exist_ok=True)

# WhisperX compute type — "float16" for GPU, "int8" for CPU
# Will auto-fallback to CPU if GPU fails
COMPUTE_TYPE    = "float16"
DEVICE          = "cuda"
BATCH_SIZE      = 8   # reduce if GPU OOM; use 1 for CPU

HF_TOKEN = os.environ.get("HF_TOKEN", None)

# ── Load dataset ──────────────────────────────────────────────────────────────
with open(DATASET_PATH, encoding="utf-8") as f:
    dataset = json.load(f)

segments    = dataset["segments"]
fingerprint = dataset["dataset_fingerprint"]
log.info(f"Dataset fingerprint: {fingerprint}")
log.info(f"Segments: {len(segments)} | Total audio: {dataset['total_duration_s']:.1f}s")

# ── Load model ────────────────────────────────────────────────────────────────
log.info(f"Loading WhisperX {MODEL_SIZE}...")
try:
    import whisperx
    model = whisperx.load_model(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        language=LANGUAGE,
    )
    log.info(f"WhisperX loaded on {DEVICE}/{COMPUTE_TYPE} ✓")
except Exception as e:
    log.warning(f"GPU load failed: {e}")
    log.info("Retrying on CPU/int8...")
    DEVICE, COMPUTE_TYPE, BATCH_SIZE = "cpu", "int8", 1
    import whisperx
    model = whisperx.load_model(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        language=LANGUAGE,
    )
    log.info("WhisperX loaded on CPU ✓")

norm    = MedicalNormalizer()
metrics = BenchmarkMetrics()

# ── Transcribe ────────────────────────────────────────────────────────────────
def transcribe(audio_path: Path) -> tuple[str, float]:
    t0 = time.perf_counter()

    # Load audio
    audio = whisperx.load_audio(str(audio_path))

    # Transcribe
    result = model.transcribe(
        audio,
        batch_size=BATCH_SIZE,
        language=LANGUAGE,
        initial_prompt=(
            "Transcription médicale en français. "
            "Termes: mg, ml, narine, polypes, cortisone, Nasonex."
        ),
    )

    # Concatenate all segments
    text = " ".join(s["text"].strip() for s in result.get("segments", []))
    latency = time.perf_counter() - t0
    return text.strip(), latency

# ── Run benchmark ─────────────────────────────────────────────────────────────
records = []
for idx, seg in enumerate(segments):
    seg_id     = seg["segment_id"]
    audio_path = AUDIO_BASE_DIR / seg["audio_file"]
    duration_s = seg["duration_s"]
    gt_norm    = seg["ground_truth_normalized"]

    log.info(f"[{idx+1}/{len(segments)}] {seg_id}")

    if not audio_path.exists():
        log.warning(f"  Audio not found: {audio_path} — skipping")
        continue

    try:
        raw_text, latency = transcribe(audio_path)
    except Exception as e:
        log.error(f"  Failed: {e}")
        raw_text, latency = "[ERROR]", -1.0

    hyp_norm = norm.normalize(raw_text)
    result   = metrics.compute(
        ref=gt_norm, hyp=hyp_norm,
        latency_s=latency, audio_duration_s=duration_s,
        cost_per_minute=0.0,
    )

    log.info(f"  WER={result.wer:.3f} | CER={result.cer:.3f} | RTF={result.rtf:.3f}")
    if result.med_critical_errors:
        for err in result.med_critical_errors:
            log.warning(f"  ⚠️  {err}")

    records.append({
        "model":               f"whisperx-{MODEL_SIZE}",
        "device":              DEVICE,
        "compute_type":        COMPUTE_TYPE,
        "segment_id":          seg_id,
        "audio_file":          seg["audio_file"],
        "duration_s":          duration_s,
        "hypothesis_raw":      raw_text,
        "hypothesis_norm":     hyp_norm,
        "reference_norm":      gt_norm,
        "dataset_fingerprint": fingerprint,
        **result.to_dict(),
    })

# ── Save & summarise ──────────────────────────────────────────────────────────
df = pd.DataFrame(records)
df["run_timestamp"] = pd.Timestamp.now(tz="UTC").isoformat()
df.to_csv(RESULTS_PATH, index=False, encoding="utf-8")
log.info(f"Results saved → {RESULTS_PATH}")

print("\n" + "=" * 60)
print(f"RESULTS — WhisperX {MODEL_SIZE} ({DEVICE}/{COMPUTE_TYPE})")
print("=" * 60)
print(f"  Segments:        {len(df)}")
print(f"  Mean WER:        {df['wer'].mean():.3f}")
print(f"  Mean CER:        {df['cer'].mean():.3f}")
print(f"  Med entity acc:  {df['med_entity_acc'].mean():.3f}")
print(f"  Mean RTF:        {df['rtf'].mean():.3f}")
print(f"  Mean latency:    {df['latency_s'].mean():.1f}s")
n_crit = df['med_critical_errors'].apply(lambda x: 1 if x and x != '' else 0).sum()
print(f"  Critical errors: {n_crit}")
print(f"  Dataset:         {fingerprint}")
print("=" * 60)