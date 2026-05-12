# Napoleon - Pipeline complet de traitement audio médical

Pipeline end-to-end pour convertir de l'audio médical en rapports PDF professionnels. Combine un benchmark STT multi-modèles avec extraction de consultations et génération de rapports.

## Vue d'ensemble du projet

**Napoleon** est un système complet qui:
1. Transcrit l'audio médical avec 5 modèles STT différents
2. Compare la qualité des transcriptions (WER, CER, précision médicale)
3. Extrait les données structurées des consultations avec LLM
4. Génère des rapports PDF professionnels

```
Audio médical (.mp3, .wav)
    ↓
[Benchmark STT multi-modèles]
    • Whisper Large V3 (OpenAI)
    • Faster-Whisper (CTranslate2)
    • WhisperX (avec alignement)
    • Voxtral Mini (optimisé français)
    • NVIDIA Conformer (haute précision)
    ↓
Transcription JSON + Métriques de qualité
    ↓
[Extraction LLM] (ChatGPT, Claude, Ollama)
    ↓
extraction_consultation_XXXX.json
    ↓
[Convertisseur JSON→PDF]
    ↓
Rapport médical professionnel (.pdf)
```

## Fonctionnalités

### Benchmark STT
- Comparaison de 5 modèles différents sur le même corpus
- Métriques: WER, CER, précision sur les termes médicaux
- Mesure de la latence et du RTF (Real-Time Factor)
- Normalisation identique des transcriptions
- Support du français médical

### Extraction de consultations
- Extraction automatique des informations cliniques
- Support de multiples LLM (OpenAI, Anthropic, local Ollama)
- Structuration des données: motif, antécédents, examen, diagnostic
- Extraction des prescriptions
- Gestion des données sensibles

### Génération de rapports
- Mise en page professionnelle de qualité médicale
- Tableau à deux colonnes (Champ | Valeur)
- En-têtes gris avec sections numérotées
- Support complet du français avec accents
- Format standardisé imprimable

## Prérequis

- Docker et Docker Compose
- GPU NVIDIA (RTX 3000+ recommandé, 8GB+ VRAM)
- Python 3.7+
- 50GB+ d'espace disque (modèles STT)
- Connexion internet (téléchargement des modèles)

## Installation

### 1. Cloner le repository

```bash
git clone https://github.com/Raul59209/Napoleon.git
cd Napoleon
```

### 2. Créer la structure de dossiers

```bash
mkdir -p audio dataset results transcriptions
```

### 3. Configurer les variables d'environnement

Créez un fichier `.env` à la racine:

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=claude-...
HF_TOKEN=hf_...
CUDA_VISIBLE_DEVICES=0
```

### 4. Installer les dépendances locales

```bash
pip install reportlab  # Pour la conversion PDF
```

## Guide complet étape par étape

### Étape 1 : Préparer les fichiers audio

Placez vos fichiers audio dans le dossier `audio/`:

```bash
audio/
├── consultation_1.mp3
├── consultation_2.wav
└── consultation_3.m4a
```

Formats supportés: MP3, WAV, M4A, FLAC, OGG

### Étape 2 : Construire l'image Docker

```bash
docker compose build
```

Cela télécharge les modèles STT (~30-50GB selon les modèles).

Durée: 20-60 minutes selon votre connexion.

### Étape 3 : Transcrire avec un modèle STT

Choisissez un modèle et lancez la transcription:

#### Option A : Whisper Large V3 (recommandé)

Meilleur équilibre qualité/vitesse. Excellente pour le français médical.

```bash
docker compose run whisper-large
```

- Durée: 15-30 minutes pour 2-3h d'audio
- Mémoire GPU: 8GB
- Qualité: Excellente
- Sortie: `results/transcription_whisper_large_XXXX.json`

#### Option B : Faster-Whisper (plus rapide)

Basé sur CTranslate2. Plus rapide, légèrement moins précis.

```bash
docker compose run faster-whisper
```

- Durée: 10-15 minutes pour 2-3h d'audio
- Mémoire GPU: 6GB
- Qualité: Bonne
- Sortie: `results/transcription_faster_XXXX.json`

#### Option C : WhisperX (avec alignement)

Includes forced alignment pour une synchronisation audio-texte précise.

```bash
docker compose run whisperx
```

- Durée: 25-40 minutes pour 2-3h d'audio
- Mémoire GPU: 10GB
- Qualité: Excellente + timestamps précis
- Sortie: `results/transcription_whisperx_XXXX.json`

#### Option D : Voxtral Mini (très rapide)

Modèle Mistral optimisé pour le français.

```bash
docker compose run voxtral
```

- Durée: 5-15 minutes pour 2-3h d'audio
- Mémoire GPU: 4GB
- Qualité: Très bonne
- Sortie: `results/transcription_voxtral_XXXX.json`

En cas d'erreur de mémoire GPU:

```yaml
# Dans docker-compose.yml, section voxtral:
environment:
  CUDA_VISIBLE_DEVICES: 0
  VOXTRAL_TORCH_DTYPE: float16  # Réduit la consommation
```

#### Option E : NVIDIA Conformer (haute précision)

Très précis mais lent. Pour les demandes de précision maximale.

```bash
docker compose run nvidia-conformer
```

- Durée: 45-90 minutes pour 2-3h d'audio
- Mémoire GPU: 12GB
- Qualité: Excellente
- Sortie: `results/transcription_nvidia_XXXX.json`

### Comparaison des modèles

Exécutez plusieurs modèles pour comparer:

```bash
# Modèle 1
docker compose run whisper-large

# Modèle 2
docker compose run faster-whisper

# Modèle 3
docker compose run whisperx

# Puis: consulter les métriques WER/CER dans results/
```

### Étape 4 : Extraire les données de consultation

Convertissez la transcription brute en données structurées avec un LLM.

#### Option A : OpenAI ChatGPT (recommandé)

```bash
export OPENAI_API_KEY="sk-..."
python extract_consultation.py \
  --transcription results/transcription_whisper_large_XXXX.json \
  --output results/extraction_consultation_XXXX.json \
  --model gpt-4
```

Coût: ~0.05-0.10 USD par consultation (dépend de la longueur)

#### Option B : Anthropic Claude

```bash
export ANTHROPIC_API_KEY="claude-..."
python extract_consultation.py \
  --provider anthropic \
  --transcription results/transcription_whisper_large_XXXX.json \
  --output results/extraction_consultation_XXXX.json \
  --model claude-3-opus
```

#### Option C : Local avec Ollama (gratuit)

```bash
# Démarrer Ollama dans un terminal
ollama serve

# Dans un autre terminal:
python extract_consultation.py \
  --provider ollama \
  --model mistral \
  --transcription results/transcription_whisper_large_XXXX.json \
  --output results/extraction_consultation_XXXX.json
```

La sortie est un fichier JSON structuré contenant:

```json
{
  "consultation_report": {
    "motif_de_consultation": "...",
    "interrogatoire": "...",
    "examen_clinique": "...",
    "proposition_therapeutique": "..."
  },
  "medical_record": {
    "antecedents": { "medicaux": [...], "familiaux": [...] },
    "mode_de_vie": { "tabac": "...", "alcool": "..." },
    "traitements_habituels": [...],
    "conclusion": { "diagnostic": "...", "prochaine_consultation": "..." }
  },
  "prescription": {
    "prescriptions": [
      {
        "nom_commercial": "Metformine",
        "dosage": "1000 mg",
        "posologie": "matin et soir"
      }
    ]
  }
}
```

### Étape 5 : Générer le rapport PDF

Convertissez le fichier JSON en rapport PDF professionnel.

#### Installation

```bash
pip install reportlab
```

#### Génération simple

```bash
python json_to_pdf.py results/extraction_consultation_XXXX.json
```

Sortie: `extraction_consultation_XXXX.pdf`

#### Avec nom personnalisé

```bash
python json_to_pdf.py results/extraction_consultation_XXXX.json rapport_patient_dupont.pdf
```

#### Conversion par lot

```bash
# Tous les fichiers du dossier
for file in results/extraction_consultation*.json; do
  python json_to_pdf.py "$file"
done
```

## Flux complet en une ligne

Exemple complet du début à la fin:

```bash
# 1. Construire
docker compose build

# 2. Transcrire
docker compose run whisper-large

# 3. Extraire
export OPENAI_API_KEY="sk-..."
python extract_consultation.py \
  --transcription results/transcription_whisper_large_*.json \
  --output results/extraction_consultation_001.json

# 4. Générer PDF
python json_to_pdf.py results/extraction_consultation_001.json rapport_final.pdf
```

## Structure complète du projet

```
Napoleon/
│
├── audio/                              # ENTRÉE: Fichiers audio
│   ├── consultation_1.mp3
│   ├── consultation_2.wav
│   └── ...
│
├── results/                            # SORTIES
│   ├── transcription_whisper_large_001.json    # Étape 2
│   ├── transcription_faster_whisper_001.json
│   ├── extraction_consultation_001.json        # Étape 3
│   ├── extraction_consultation_001.pdf         # Étape 4 FINALE
│   └── metrics_comparison.csv
│
├── dataset/                            # Données de benchmark
│   ├── correction_worksheet.tsv        # Pour correction manuelle
│   └── test_set_frozen.json
│
├── transcriptions/                     # Fichiers temporaires
│
├── json_to_pdf.py                      # Script conversion JSON→PDF
├── extract_consultation.py             # Script extraction LLM
├── normalizer.py                       # Normalisation texte
├── metrics.py                          # Calcul WER/CER
│
├── docker-compose.yml                  # Configuration Docker
├── Dockerfile                          # Construction image
├── requirements.txt                    # Dépendances Python
│
├── README.md                           # Documentation (ce fichier)
├── .env                               # Variables d'environnement
└── .gitignore
```

## Métriques et benchmark

### Mesures de qualité

| Métrique | Description | Importance |
|----------|-------------|-----------|
| **WER** | Word Error Rate (%) | Principale - Global |
| **CER** | Character Error Rate (%) | Utile pour les termes médicaux |
| **Précision médicale** | Exactitude sur medications/dosages | Critique en médecine |
| **Latence** | Temps de traitement (s) | Performance |
| **RTF** | Real-Time Factor | Comparaison avec audio |

### Normalisation (important!)

La normalisation est appliquée identiquement à la vérité de référence et aux sorties pour assurer la comparabilité:

```
Dr. / dr → docteur
500 mg / cinq cents milligrammes → 500 mg
IV → intraveineux
BID / bid → deux fois par jour
Tous minuscules, sans ponctuation
```

Sans cela, les WER entre modèles ne sont pas comparables.

### Performance comparée

| Modèle | Vitesse | Qualité | VRAM | Temps (2h) | WER |
|--------|---------|---------|------|-----------|-----|
| Whisper Large V3 | Moyenne | Excellente | 8GB | 20-30 min | ~3% |
| Faster-Whisper | Rapide | Bonne | 6GB | 10-15 min | ~4% |
| WhisperX | Moyenne | Excellente | 10GB | 25-40 min | ~3% |
| Voxtral Mini | Très rapide | Très bonne | 4GB | 5-15 min | ~4% |
| NVIDIA Conformer | Lent | Excellente | 12GB | 45-60 min | ~2% |

*Les chiffres WER sont estimés sur du français médical. Les résultats varient selon le corpus.*

## Dépannage

### Erreur: "CUDA out of memory"

**Cause**: Le modèle est trop gros pour votre GPU.

**Solutions**:

1. Utiliser float16 (réduit 50% mémoire):
```bash
# Dans docker-compose.yml:
environment:
  VOXTRAL_TORCH_DTYPE: float16
```

2. Utiliser un modèle plus petit:
```bash
docker compose run voxtral  # Plus petit que whisper-large
```

3. Augmenter la mémoire GPU:
```bash
docker compose run --memory 16g whisper-large
```

### Erreur: "CUDA driver error"

```bash
# Vérifier la GPU
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime nvidia-smi

# Mettre à jour les drivers NVIDIA
# https://www.nvidia.com/Download/driverDetails.aspx
```

### Erreur: "No module named 'reportlab'"

```bash
pip install reportlab
```

### Conteneurs Docker orphelins

```bash
docker compose down --remove-orphans
docker system prune -a
docker compose build
docker compose run whisper-large
```

### Le PDF contient des caractères mal affichés

Assurez-vous que votre JSON est encodé UTF-8:

```bash
file results/extraction_consultation_001.json
# output: UTF-8 Unicode text
```

### Modèle ne se télécharge pas

```bash
# Vérifier connexion Internet
ping huggingface.co

# Utiliser cache manuel
export HF_HOME=/custom/cache/path
docker compose run whisper-large
```

## Variables d'environnement

```bash
# APIs LLM
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="claude-..."
export HF_TOKEN="hf_..."

# GPU
export CUDA_VISIBLE_DEVICES=0        # GPU à utiliser (0-indexed)
export CUDA_LAUNCH_BLOCKING=1        # Mode debug

# Modèles
export MODEL_CACHE=/path/to/cache    # Cache HuggingFace personnalisé
export TRANSFORMERS_OFFLINE=0        # Forcer offline mode

# Fichiers .env
# Créer .env à la racine du projet
OPENAI_API_KEY=sk-...
CUDA_VISIBLE_DEVICES=0
```

## Sécurité des données

Recommandations pour traiter des données médicales sensibles:

1. Chiffrez vos fichiers audio:
```bash
gpg --encrypt audio/consultation.mp3
```

2. Limitez les permissions:
```bash
chmod 600 .env
chmod 700 audio/ results/ dataset/
```

3. Utilisez des variables d'environnement pour les clés:
```bash
# NE PAS faire:
OPENAI_API_KEY=sk-... python script.py

# FAIRE:
export OPENAI_API_KEY="sk-..."
python script.py
```

4. Supprimez les fichiers après traitement:
```bash
shred -vfz audio/consultation.mp3  # Secure delete
```

5. Respectez RGPD et régulations locales:
   - Consentement patient
   - Durée de rétention
   - Droit à l'oubli

## Performance et ressources

### Consommation GPU

| Modèle | Mémoire | Consommation CPU | Temps inférence |
|--------|---------|-----------------|-----------------|
| Whisper Large V3 | 8GB | Moyenne | 20-30 min/2h |
| Faster-Whisper | 6GB | Basse | 10-15 min/2h |
| WhisperX | 10GB | Moyenne | 25-40 min/2h |
| Voxtral Mini | 4GB | Basse | 5-15 min/2h |
| NVIDIA Conformer | 12GB | Haute | 45-60 min/2h |

### Stockage

- Modèles STT: 30-50GB
- Audio 2h: 100-500MB
- Transcriptions: 50-200KB
- PDFs: 50-200KB

Total estimé: 50-60GB pour setup complet.

## Support et troubleshooting

Pour toute question ou problème:

1. Consultez le dépannage ci-dessus
2. Vérifiez les logs:
```bash
docker compose logs -f whisper-large
```

3. Testez avec un fichier simple d'abord
4. Vérifiez les ressources GPU:
```bash
nvidia-smi
```

5. Ouvrez une issue sur GitHub avec:
   - Logs complets
   - Version Docker
   - Modèle de GPU
   - Commande exacte exécutée

## Limitations connues

- Nécessite GPU pour performances acceptables (CPU très lent)
- Modèles volumineux (~3-7GB par modèle)
- Français médical peut être moins précis que l'anglais
- LLM peut halluciner des informations (vérifier toujours)
- Audio très bruyant: qualité réduite

## Contributeurs et licence

Développé par **Raul59209**

Licence: Propriétaire

## Auteurs

- **Raul59209**: Architecture, benchmark STT, intégration
