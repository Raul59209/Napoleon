# STT Benchmark — French Medical Audio

Benchmark pipeline for comparing speech-to-text models on French medical audio.

## Models evaluated
- Whisper large-v3 (OpenAI)
- faster-whisper (CTranslate2 backend)
- WhisperX (+ forced alignment)
- NVIDIA STT Fr Conformer-CTC Large (NeMo)

## Metrics
| Metric | Description |
|--------|-------------|
| WER | Word Error Rate (primary metric) |
| CER | Character Error Rate (useful for medical terms) |
| Medical entity accuracy | Precision on medications, dosages, numbers |
| Latency (s) | Wall-clock time per segment |
| RTF | Real-Time Factor (latency / audio_duration) |
| Cost/hour audio | Estimated Scaleway GPU cost |

## File structure
```
stt_benchmark/
├── normalizer.py              # Shared text normalizer (apply to BOTH refs and hyps)
├── prep_ground_truth.py       # Step 1: bootstrap transcriptions with Whisper
├── freeze_dataset.py          # Step 2: lock the test set after human correction
├── metrics.py                 # WER, CER, medical entity metrics, RTF utils
├── notebook_whisper_large_v3.ipynb
├── notebook_faster_whisper.ipynb
├── notebook_whisperx.ipynb
├── notebook_nvidia_conformer.ipynb
├── consolidate.ipynb          # Merge all results → single comparison table
├── dataset/
│   ├── correction_worksheet.tsv   # Human review goes here
│   └── test_set_frozen.json       # Frozen after freeze_dataset.py
├── results/
│   ├── results_whisper_large_v3.csv
│   ├── results_faster_whisper.csv
│   ├── results_whisperx.csv
│   ├── results_nvidia_conformer.csv
│   └── results_all.csv            # Consolidated output
└── requirements.txt
```

## Quickstart

### Option A — Docker (recommended for sharing with your team)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the NVIDIA Container Toolkit enabled.

```bash
# 1. Build the image
docker build -t stt-benchmark .

# 2. Run interactively with GPU + mounted volumes (Windows)
docker run --gpus all -it --rm ^
  -v "%cd%/audio":/app/audio ^
  -v "%cd%/dataset":/app/dataset ^
  -v "%cd%/results":/app/results ^
  --env-file .env ^
  stt-benchmark

# Or with docker compose (handles volumes + GPU automatically):
docker compose run benchmark

# 3. Inside the container, run scripts normally:
python prep_ground_truth.py --audio_dir ./audio --output_dir ./dataset
```

> **Sharing with your boss:** just send the whole project folder (excluding `audio/`, `dataset/`, `results/`, and `.env`). They run `docker build` + `docker compose run benchmark` and get an identical environment.

---

### Option B — Local install

**⚠️ RTX 5060 / Blackwell GPU owners:** PyTorch stable does not support Blackwell yet.
Use the nightly build with CUDA 12.8:

```bash
pip uninstall torch torchvision torchaudio -y
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
```

For older GPUs (RTX 3000/4000 series):
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Then install the rest:
```bash
pip install -r requirements.txt
```

### Prepare ground truth (both options)
```bash
# Put your audio files in ./audio/
python prep_ground_truth.py --audio_dir ./audio --output_dir ./dataset
# set CUDA_VISIBLE_DEVICES=-1 && python containers/base/src/prep_ground_truth.py --audio_dir ./audio --output_dir ./dataset

# Open the worksheet and correct column D (ground_truth)
# Then freeze the test set:
python freeze_dataset.py --worksheet dataset/correction_worksheet.tsv
```

### 3. Run benchmarks (one per model)
```bash
jupyter nbconvert --to notebook --execute notebook_whisper_large_v3.ipynb --output notebook_whisper_large_v3_executed.ipynb
# or
python notebook_whisper_large_v3.py
python notebook_whisperx.py

# Repeat for each model
```

### 4. Consolidate results
```bash
jupyter nbconvert --to notebook --execute consolidate.ipynb
```

## Normalization rules (important!)
The normalizer is applied **identically** to both ground truth and model outputs before metric computation. Key transformations:
- `Dr.` / `dr` → `docteur`
- `500 mg` / `cinq cents milligrammes` → `500 mg`
- `IV` → `intraveineux`
- `BID` → `deux fois par jour`
- All text lowercased, punctuation removed

Without this, WER numbers are not comparable between models (one model may output numbers as words, another as digits).

## Medical entity accuracy
Beyond WER, we separately score accuracy on:
- Medication names
- Dosages (numbers + units)
- Frequencies
- Patient identifiers

A "500 mg" vs "5000 mg" error counts as 1 WER error but is clinically critical — this metric surfaces it.

## Reproducibility
Every model notebook logs:
- Model name + version
- Dataset fingerprint (from `test_set_frozen.json`)
- Inference timestamp
- GPU type + CUDA version
- All hyperparameters used