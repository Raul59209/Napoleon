#!/usr/bin/env python3
"""
Scaleway Inference API - STT for French Medical Audio

Uses Scaleway's inference API to transcribe audio without requiring local GPU.
Supports multiple models: Whisper, Voxtral, etc.

Environment variables required:
- SCALEWAY_API_KEY: Your Scaleway API key
- SCALEWAY_PROJECT_ID: Your Scaleway project ID
- SCALEWAY_REGION: Region (default: fr-par)
- SCALEWAY_MODEL: Model to use (default: whisper-large)
"""

import os
import json
import argparse
import requests
import time
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ScalewaySTT:
    """Scaleway Inference API client for STT"""
    
    def __init__(self):
        """Initialize Scaleway API client"""
        self.api_key = os.getenv('SCALEWAY_API_KEY')
        self.project_id = os.getenv('SCALEWAY_PROJECT_ID')
        self.region = os.getenv('SCALEWAY_REGION', 'fr-par')
        self.model = os.getenv('SCALEWAY_MODEL', 'whisper-large')
        
        if not self.api_key:
            raise ValueError("SCALEWAY_API_KEY environment variable not set")
        if not self.project_id:
            raise ValueError("SCALEWAY_PROJECT_ID environment variable not set")
        
        self.base_url = f"https://api.scaleway.com/inference/v1/projects/{self.project_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Scaleway STT initialized")
        logger.info(f"Region: {self.region}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Project ID: {self.project_id}")
    
    def list_models(self):
        """List available models"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            models = response.json()
            logger.info(f"Available models: {models}")
            return models
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return None
    
    def transcribe_file(self, audio_path):
        """
        Transcribe audio file using Scaleway API
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcription result
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing: {audio_path}")
        logger.info(f"File size: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        try:
            with open(audio_path, 'rb') as f:
                files = {
                    'file': (audio_path.name, f, 'audio/mpeg')
                }
                
                data = {
                    'model': self.model,
                    'language': 'fr'  # French
                }
                
                response = requests.post(
                    f"{self.base_url}/models/{self.model}:transcribe",
                    headers={"Authorization": self.headers["Authorization"]},
                    files=files,
                    data=data,
                    timeout=300  # 5 minutes timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info("Transcription completed successfully")
                return result
        
        except requests.exceptions.Timeout:
            logger.error("Request timed out. Audio file may be too large.")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"API error: {e}")
            raise
    
    def transcribe_batch(self, audio_dir, output_dir='results'):
        """
        Transcribe all audio files in a directory
        
        Args:
            audio_dir: Directory containing audio files
            output_dir: Directory to save transcriptions
        """
        audio_dir = Path(audio_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma'}
        audio_files = [f for f in audio_dir.iterdir() 
                      if f.suffix.lower() in audio_extensions]
        
        if not audio_files:
            logger.warning(f"No audio files found in {audio_dir}")
            return
        
        logger.info(f"Found {len(audio_files)} audio file(s)")
        
        results = []
        
        for i, audio_file in enumerate(audio_files, 1):
            try:
                logger.info(f"[{i}/{len(audio_files)}] Processing: {audio_file.name}")
                
                # Transcribe
                transcription = self.transcribe_file(audio_file)
                
                # Save result
                output_file = output_dir / f"transcription_{audio_file.stem}.json"
                
                result_data = {
                    "file": audio_file.name,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model,
                    "region": self.region,
                    "transcription": transcription
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Saved to: {output_file}")
                results.append(result_data)
                
                # Rate limiting - avoid API throttling
                if i < len(audio_files):
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Error processing {audio_file.name}: {e}")
                continue
        
        # Summary
        logger.info(f"\nProcessed {len(results)}/{len(audio_files)} files successfully")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe audio files using Scaleway Inference API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file
  python scaleway_stt.py --audio audio/consultation.mp3
  
  # Batch processing
  python scaleway_stt.py --batch --audio-dir audio/ --output-dir results/
  
  # List available models
  python scaleway_stt.py --list-models
  
Environment variables:
  SCALEWAY_API_KEY       - Your Scaleway API key (required)
  SCALEWAY_PROJECT_ID    - Your Scaleway project ID (required)
  SCALEWAY_REGION        - Region (default: fr-par)
  SCALEWAY_MODEL         - Model name (default: whisper-large)
        """
    )
    
    parser.add_argument('--audio', help='Path to audio file')
    parser.add_argument('--audio-dir', default='audio', help='Directory with audio files')
    parser.add_argument('--output-dir', default='results', help='Output directory')
    parser.add_argument('--batch', action='store_true', help='Process all files in directory')
    parser.add_argument('--list-models', action='store_true', help='List available models')
    
    args = parser.parse_args()
    
    try:
        client = ScalewaySTT()
        
        if args.list_models:
            models = client.list_models()
            if models:
                print("\nAvailable models:")
                print(json.dumps(models, indent=2))
        
        elif args.batch:
            logger.info(f"Batch mode: {args.audio_dir} → {args.output_dir}")
            client.transcribe_batch(args.audio_dir, args.output_dir)
        
        elif args.audio:
            logger.info(f"Single file mode: {args.audio}")
            result = client.transcribe_file(args.audio)
            
            # Save result
            output_path = Path('results') / f"transcription_{Path(args.audio).stem}.json"
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "file": args.audio,
                    "timestamp": datetime.now().isoformat(),
                    "model": client.model,
                    "transcription": result
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved to: {output_path}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)


if __name__ == '__main__':
    main()
