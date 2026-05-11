# Napoleon - Pipeline complet de traitement audio médical

Pipeline complet pour convertir de l'audio médical en rapports PDF professionnels. Du traitement audio brut à l'extraction de consultations et génération de PDF.

## Flux global

```
Audio (.mp3, .wav)
    ↓
[Docker STT Models] (Whisper, faster-whisper, WhisperX, Voxtral, Nvidia Conformer)
    ↓
Transcription JSON
    ↓
[Extraction d'informations] (LLM - ChatGPT, Claude, etc.)
    ↓
extraction_consultation_XXXX.json
    ↓
[json_to_pdf.py]
    ↓
Rapport PDF professionnel
```

## Prérequis

- Docker et Docker Compose
- GPU NVIDIA (RTX 3000+ recommandé, 8GB+ VRAM)
- Au moins 50GB d'espace disque (pour les modèles)
- Git

## Installation

1. Clonez le repository:
```bash
git clone https://github.com/Raul59209/Napoleon.git
cd Napoleon
```

2. Créez les dossiers nécessaires:
```bash
mkdir -p audio dataset results transcriptions
```

3. Placez vos fichiers audio dans le dossier `audio/`:
```bash
cp /chemin/vers/vos/fichiers.mp3 audio/
```

## Étape 1 : Construire l'image Docker

```bash
docker compose build
```

Cette étape télécharge et prépare les modèles STT (plusieurs minutes, selon votre connexion internet).

## Étape 2 : Transcrire l'audio avec STT

Choisissez un modèle et exécutez:

### Option A : Whisper Large V3 (recommandé - équilibre qualité/vitesse)

```bash
docker compose run whisper-large
```

Durée estimée: 15-30 minutes pour 2-3 heures d'audio

### Option B : Faster-Whisper (plus rapide, légèrement moins précis)

```bash
docker compose run faster-whisper
```

Durée estimée: 10-15 minutes pour 2-3 heures d'audio

### Option C : WhisperX (avec alignement forcé)

```bash
docker compose run whisperx
```

Durée estimée: 20-40 minutes pour 2-3 heures d'audio

### Option D : Voxtral Mini (très rapide, français optimisé)

```bash
docker compose run voxtral
```

Durée estimée: 5-15 minutes pour 2-3 heures d'audio (GPU permitting)

Pour éviter les erreurs de mémoire GPU sur Voxtral:

```bash
# Ajouter dans docker-compose.yml pour le service voxtral:
environment:
  CUDA_VISIBLE_DEVICES: 0
  VOXTRAL_TORCH_DTYPE: float16
```

### Option E : NVIDIA Conformer (très précis mais lent)

```bash
docker compose run nvidia-conformer
```

Durée estimée: 45+ minutes pour 2-3 heures d'audio

Après l'exécution, les transcriptions se trouvent dans `results/transcription_XXXX.json`.

## Étape 3 : Extraire les données de consultation

Une fois la transcription complétée, utilisez un LLM pour extraire les informations structurées:

### Avec OpenAI ChatGPT (recommandé)

```bash
export OPENAI_API_KEY="votre_clé_api"
python extract_consultation.py --transcription results/transcription_XXXX.json --output results/extraction_consultation_XXXX.json
```

### Avec Anthropic Claude

```bash
export ANTHROPIC_API_KEY="votre_clé_api"
python extract_consultation.py --provider anthropic --transcription results/transcription_XXXX.json --output results/extraction_consultation_XXXX.json
```

### Avec un modèle local (Ollama)

```bash
# Démarrer Ollama au préalable
ollama serve

# Dans un autre terminal:
python extract_consultation.py --provider ollama --model llama2-french --transcription results/transcription_XXXX.json --output results/extraction_consultation_XXXX.json
```

La sortie est un fichier `extraction_consultation_XXXX.json` contenant:
- Motif de consultation
- Historique médical
- Antécédents
- Interrogatoire
- Examen clinique
- Conclusion et diagnostic
- Prescriptions

## Étape 4 : Convertir en PDF

Installez reportlab:

```bash
pip install reportlab
```

Convertissez le fichier d'extraction en PDF professionnel:

```bash
python json_to_pdf.py results/extraction_consultation_XXXX.json
```

Sortie: `extraction_consultation_XXXX.pdf`

Pour spécifier un nom personnalisé:

```bash
python json_to_pdf.py results/extraction_consultation_XXXX.json rapport_patient_dupont.pdf
```

## Flux complet en une ligne (exemple)

```bash
# 1. Construire
docker compose build

# 2. Transcrire
docker compose run whisper-large

# 3. Extraire (supposant extract_consultation.py existe)
export OPENAI_API_KEY="sk-..."
python extract_consultation.py --transcription results/transcription_XXXX.json --output results/extraction_consultation_XXXX.json

# 4. Générer PDF
python json_to_pdf.py results/extraction_consultation_XXXX.json
```

## Structure des fichiers

```
Napoleon/
├── audio/                              # Fichiers audio d'entrée
│   ├── consultation_1.mp3
│   ├── consultation_2.wav
│   └── ...
├── results/                            # Résultats intermédiaires et finaux
│   ├── transcription_1001.json        # Sortie STT (étape 2)
│   ├── extraction_consultation_1001.json  # Sortie LLM (étape 3)
│   └── extraction_consultation_1001.pdf   # PDF final (étape 4)
├── dataset/                            # Dataset et corrections humaines
├── transcriptions/                     # Transcriptions temporaires
├── docker-compose.yml                  # Configuration Docker
├── json_to_pdf.py                      # Script de conversion JSON->PDF
├── extract_consultation.py             # Script d'extraction LLM (si présent)
├── Dockerfile                          # Construction Docker
└── README.md                           # Documentation
```

## Format de sortie JSON (étape 3)

```json
{
  "consultation_report": {
    "motif_de_consultation": "Suivi du diabète et hypertension",
    "interrogatoire": "Le patient rapporte...",
    "examen_clinique": "La tension artérielle est à 148/86 mmHg...",
    "proposition_therapeutique": "Ajout d'Indapamide 1,25 mg..."
  },
  "medical_record": {
    "motif_de_consultation": "Diabète, hypertension",
    "historique_medical": "Diabète depuis 10 ans...",
    "antecedents": {
      "medicaux": ["Diabète", "Hypertension", "Cholestérol"],
      "chirurgicaux": [],
      "familiaux": ["Crise cardiaque du père"],
      "gynecologiques": []
    },
    "mode_de_vie": {
      "tabac": "Arrêté il y a 20 ans",
      "alcool": "Modéré",
      "activite_physique": "Marche 30 min/jour",
      "autre": "Retraité"
    },
    "traitements_habituels": [
      {
        "nom_commercial": "Metformine",
        "molecule": "Metformine",
        "posologie": "1000 mg matin et soir"
      }
    ],
    "allergies": ["Pas d'allergies connues"],
    "interrogatoire": {
      "symptomes_generaux": "Asthénie légère",
      "symptomes_par_organe": "Œdèmes aux chevilles"
    },
    "examen_clinique": {
      "constantes": {
        "poids_kg": 75,
        "tension_arterielle": "148/86"
      },
      "examen_specifique": "ECG recommandé"
    },
    "conclusion": {
      "diagnostic": "Hypertension, diabète mal contrôlé",
      "proposition_therapeutique": "Optimisation du traitement",
      "examens_complementaires": ["ECG", "Bilan sanguin"],
      "orientation": "Suivi cardiologique",
      "prochaine_consultation": "Dans 3 semaines"
    }
  },
  "prescription": {
    "prescriptions": [
      {
        "nom_commercial": "INDAPAMIDE",
        "molecule": "indapamide",
        "dosage": "1,25 mg",
        "posologie": {
          "dose": "1,25 mg",
          "frequence": "le matin",
          "voie": "orale"
        }
      }
    ]
  }
}
```

## Format de sortie PDF (étape 4)

Le PDF contient:

- En-têtes gris avec titres de section
- Tableau à deux colonnes (Champ | Valeur)
- Sections organisées: Motif, Historique, Interrogatoire, Examen, Conclusion
- Mise en page professionnelle adaptée à la médecine
- Support complet du français

## Dépannage

### Erreur Docker: "out of memory"

Solution 1 (Voxtral):
```bash
# Dans docker-compose.yml, ajouter pour le service voxtral:
environment:
  CUDA_VISIBLE_DEVICES: 0
  TORCH_DTYPE: float16
```

Solution 2 (tous modèles):
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

### Conteneurs orphelins

```bash
docker compose down --remove-orphans
docker compose build
docker compose run whisper-large
```

## Variables d'environnement

```bash
# Pour l'extraction LLM
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="claude-..."
export HF_TOKEN="hf_..."

# Pour Docker STT
export CUDA_VISIBLE_DEVICES=0  # GPU à utiliser
export MODEL_CACHE=/path/to/cache  # Cache des modèles
```

## Performance estimée

| Modèle | Vitesse | Qualité | Mémoire | Durée pour 2h audio |
|--------|---------|---------|---------|-------------------|
| Whisper Large V3 | Moyenne | Excellente | 8GB | 20-30 min |
| Faster-Whisper | Rapide | Bonne | 6GB | 10-15 min |
| WhisperX | Moyenne | Excellente | 10GB | 25-40 min |
| Voxtral Mini | Très rapide | Très bonne | 4GB | 5-15 min |
| NVIDIA Conformer | Lent | Excellente | 12GB | 45-60 min |

## Sécurité des données

Ce pipeline traite des données médicales sensibles:

- Chiffrez vos fichiers audio
- Limitez l'accès aux fichiers de sortie
- Utilisez des clés API sécurisées (.env)
- Supprimez les fichiers après traitement
- Respectez RGPD et les régulations médicales locales

Exemple de fichier `.env`:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=claude-...
CUDA_VISIBLE_DEVICES=0
```

## Support et contributes

Pour des problèmes:
1. Consultez le dépannage ci-dessus
2. Vérifiez les logs: `docker compose logs whisper-large`
3. Ouvrez une issue sur GitHub

## Licence

Propriétaire - Raul59209

## Auteur

Développé par Raul59209
