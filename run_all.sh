#!/bin/bash
set -e

echo "========================================"
echo " STT BENCHMARK — AUTOMATED EXECUTION"
echo "========================================"

echo "[1/5] Running Whisper large-v3..."
python notebook_whisper_large_v3.py

echo "[2/5] Running faster-whisper..."
python notebook_faster_whisper.py

echo "[3/5] Running WhisperX..."
python notebook_whisperx.py

echo "[4/5] Running NVIDIA Conformer..."
python notebook_nvidia_conformer.py

echo "[5/5] Consolidating results..."
python consolidate.py

echo "========================================"
echo " ALL BENCHMARKS COMPLETED SUCCESSFULLY"
echo " Results saved in /app/results"
echo "========================================"
