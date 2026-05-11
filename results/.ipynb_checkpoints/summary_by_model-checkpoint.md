# STT Benchmark Results — French Medical Audio

Dataset fingerprint: `e30a55744b6b962a1dd8`

## Summary: model × metric

| Model | WER ↓ | CER ↓ | Med entity acc ↑ | Latency (s) ↓ | RTF ↓ | Cost/hr audio ($) | Critical errors ↓ | Segments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| faster-whisper-large-v3 | 0.0316 | 0.0184 | 1.0000 | 119.2170 | 1.1270 | 0.0000 | 0 | 1 |
| whisper-large-v3 | 0.0447 | 0.0295 | 1.0000 | 103.4470 | 0.9780 | 0.0000 | 0 | 1 |
| whisperx-large-v3 | 1.0000 | 0.9974 | 0.0000 | -1.0000 | -0.0090 | 0.0000 | 0 | 1 |

## Notes
- WER and CER: lower is better. Computed on normalized text (same normalizer applied to both reference and hypothesis).
- Med entity acc: proportion of medical entities (drugs, dosages, routes, frequencies) correctly transcribed. Higher is better.
- RTF (Real-Time Factor): latency / audio duration. RTF < 1.0 = faster than real-time.
- Critical errors: dosage mismatches (e.g. 500 mg vs 5000 mg), missing or hallucinated dosages.
- Cost/hr audio: extrapolated API cost per hour of audio. Local models = $0.
