"""
llm_extraction.py
=================
Takes a transcript and generates structured medical documents
using a Scaleway-hosted LLM.

Usage:
    python llm_extraction.py --transcript "path/to/transcript.txt" --outputs consultation_report medical_record prescription
    
Or import and use directly:
    from llm_extraction import extract_documents
    results = extract_documents(transcript, outputs=["consultation_report", "prescription"])
"""

import os
import json
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from prompts import build_prompt

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Scaleway config ───────────────────────────────────────────────────────────
SCALEWAY_API_URL = "https://api.scaleway.ai/v1"
SCALEWAY_API_KEY = os.environ.get("SCW_API_KEY")

# Best model for French medical structured output on Scaleway.
# Options: "llama-3.3-70b-instruct", "qwen3-235b-a22b-instruct-2507"
# Llama 3.3 70B is faster and cheaper; Qwen3 235B is more powerful.
MODEL = "llama-3.3-70b-instruct"

OUTPUT_TYPES = ["consultation_report", "medical_record", "prescription"]


# ── Client ────────────────────────────────────────────────────────────────────
def get_client() -> OpenAI:
    if not SCALEWAY_API_KEY:
        raise EnvironmentError(
            "SCW_API_KEY not found. Add it to your .env file."
        )
    return OpenAI(
        base_url=SCALEWAY_API_URL,
        api_key=SCALEWAY_API_KEY,
    )


# ── Core extraction function ──────────────────────────────────────────────────
def extract_one(client: OpenAI, transcript: str, output_type: str) -> dict:
    """
    Extract one document type from a transcript.
    Returns parsed JSON dict.
    """
    prompt = build_prompt(output_type, transcript)

    log.info(f"Calling {MODEL} for {output_type}...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,    # low temperature for consistent structured output
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model added them
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"JSON parse failed for {output_type}: {e}")
        log.error(f"Raw response: {raw[:300]}")
        return {"error": str(e), "raw_response": raw}


def extract_documents(
    transcript: str,
    outputs: list[str] = None,
    save_to: Path = None,
) -> dict:
    """
    Extract all requested document types from a transcript.

    Args:
        transcript:  raw transcript text
        outputs:     list of output types to generate. Defaults to all three.
        save_to:     optional path to save results JSON

    Returns:
        dict with one key per output type
    """
    if outputs is None:
        outputs = OUTPUT_TYPES

    client = get_client()
    results = {}

    for output_type in outputs:
        if output_type not in OUTPUT_TYPES:
            log.warning(f"Unknown output type '{output_type}' — skipping")
            continue
        try:
            results[output_type] = extract_one(client, transcript, output_type)
            log.info(f"  ✓ {output_type}")
        except Exception as e:
            log.error(f"  ✗ {output_type} failed: {e}")
            results[output_type] = {"error": str(e)}

    if save_to:
        save_to = Path(save_to)
        save_to.parent.mkdir(parents=True, exist_ok=True)
        with open(save_to, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info(f"Results saved → {save_to}")

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract structured medical documents from a transcript using Scaleway LLM."
    )
    parser.add_argument(
        "--transcript", type=str, required=True,
        help="Path to transcript .txt file, or transcript text directly"
    )
    parser.add_argument(
        "--outputs", nargs="+", default=OUTPUT_TYPES,
        choices=OUTPUT_TYPES,
        help="Which documents to generate (default: all three)"
    )
    parser.add_argument(
        "--save", type=Path, default=None,
        help="Path to save results JSON (optional)"
    )
    parser.add_argument(
        "--model", type=str, default=MODEL,
        help=f"Scaleway model to use (default: {MODEL})"
    )
    args = parser.parse_args()
    MODEL = args.model

    # Load transcript from file or use as string directly
    transcript_path = Path(args.transcript)
    if transcript_path.exists():
        transcript = transcript_path.read_text(encoding="utf-8")
        log.info(f"Loaded transcript from {transcript_path} ({len(transcript)} chars)")
    else:
        transcript = args.transcript
        log.info(f"Using transcript string directly ({len(transcript)} chars)")

    results = extract_documents(
        transcript=transcript,
        outputs=args.outputs,
        save_to=args.save,
    )

    # Print results
    print("\n" + "=" * 60)
    for output_type, data in results.items():
        print(f"\n── {output_type.upper()} ──")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    print("=" * 60)