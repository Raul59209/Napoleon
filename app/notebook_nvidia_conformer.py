"""
notebook_nvidia_conformer.py — Benchmark: NVIDIA STT Fr Conformer-CTC Large
============================================================================
Model: nvidia/stt_fr_conformer_ctc_large (NeMo)
Docs:  https://huggingface.co/nvidia/stt_fr_conformer_ctc_large

Install:
    pip install nemo_toolkit[asr]
    # If nemo_toolkit has conflicts, try the lighter:
    # pip install nemo_toolkit

Note: NeMo will download the model from HuggingFace on first run (~500 MB).
This model is purpose-built for French — no initial_prompt needed.

Run:
    python notebook_nvidia_conformer.py
"""

import sys
import json
import time
import logging
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from Napoleon.containers.base.src.normalizer import MedicalNormalizer
from Napoleon.containers.base.src.metrics import BenchmarkMetrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Suppress NeMo's verbose logging
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME      = "nvidia/stt_fr_conformer_ctc_large"
DATASET_PATH    = Path("dataset/test_set_frozen.json")
AUDIO_BASE_DIR  = Path("audio")
RESULTS_DIR     = Path("results")
RESULTS_PATH    = RESULTS_DIR / "results_nvidia_conformer.csv"
RESULTS_DIR.mkdir(exist_ok=True)

# ── Load dataset ──────────────────────────────────────────────────────────────
with open(DATASET_PATH, encoding="utf-8") as f:
    dataset = json.load(f)

segments    = dataset["segments"]
fingerprint = dataset["dataset_fingerprint"]
log.info(f"Dataset fingerprint: {fingerprint}")
log.info(f"Segments: {len(segments)} | Total audio: {dataset['total_duration_s']:.1f}s")

# ── Load model ────────────────────────────────────────────────────────────────
log.info(f"Loading {MODEL_NAME}...")
log.info("(First run downloads ~500 MB from HuggingFace)")
try:
    import nemo.collections.asr as nemo_asr
    model = nemo_asr.models.EncDecCTCModelBPE.from_pretrained(MODEL_NAME)
    model.eval()

    # Try GPU
    import torch
    if torch.cuda.is_available():
        try:
            torch.zeros(1).cuda()
            model = model.cuda()
            device = "cuda"
            log.info("Model on GPU ✓")
        except Exception as e:
            log.warning(f"GPU failed: {e} — using CPU")
            device = "cpu"
    else:
        device = "cpu"
        log.info("Model on CPU")

except ImportError:
    log.error(
        "NeMo not installed. Run:\n"
        "  pip install nemo_toolkit[asr]\n"
        "If that fails due to conflicts, try:\n"
        "  pip install nemo_toolkit"
    )
    sys.exit(1)
except Exception as e:
    log.error(f"Failed to load model: {e}")
    sys.exit(1)

norm    = MedicalNormalizer()
metrics = BenchmarkMetrics()

# ── Audio preprocessing ───────────────────────────────────────────────────────
def ensure_wav_16k(audio_path: Path) -> Path:
    """
    NeMo Conformer-CTC expects 16kHz mono WAV.
    Converts m4a/mp3/flac on the fly using soundfile + librosa.
    Returns path to a (possibly temp) WAV file.
    """
    if audio_path.suffix.lower() == ".wav":
        return audio_path

    try:
        import librosa
        import soundfile as sf

        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        tmp   = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, y, 16000, subtype="PCM_16")
        log.info(f"  Converted {audio_path.name} → 16kHz WAV")
        return Path(tmp.name)
    except Exception as e:
        log.error(f"  Audio conversion failed: {e}")
        log.error("  Install: pip install librosa soundfile")
        raise

# ── Transcribe ────────────────────────────────────────────────────────────────
def transcribe(audio_path: Path) -> tuple[str, float]:
    wav_path = ensure_wav_16k(audio_path)
    t0 = time.perf_counter()

    # NeMo transcribe takes a list of file paths
    transcriptions = model.transcribe([str(wav_path)])
    latency = time.perf_counter() - t0

    # Clean up temp file if we created one
    if wav_path != audio_path and wav_path.exists():
        wav_path.unlink()

    text = transcriptions[0] if transcriptions else ""
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

    log.info(f"  REF: {gt_norm[:100]}")
    log.info(f"  HYP: {hyp_norm[:100]}")

    records.append({
        "model":               MODEL_NAME.split("/")[-1],
        "device":              device,
        "compute_type":        "fp32",
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
print(f"RESULTS — {MODEL_NAME} ({device})")
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