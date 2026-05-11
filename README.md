# Napoleon - Convertisseur JSON vers PDF

Convertisseur de consultations médicales JSON en rapports PDF professionnels avec mise en page de qualité médicale.

## Fonctionnalités

- Conversion de fichiers JSON d'extraction de consultations en PDF formatés
- Mise en page professionnelle avec tableau à deux colonnes
- En-têtes gris avec texte gras pour les sections
- Support complet du français (accents, caractères spéciaux)
- Gestion flexible des données manquantes
- Traitement par lot possible

## Installation

### Prérequis

- Python 3.7+
- pip

### Étapes

1. Clonez le repository:
```bash
git clone https://github.com/Raul59209/Napoleon.git
cd Napoleon
```

2. Créez un environnement virtuel (optionnel mais recommandé):
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installez reportlab:
```bash
pip install reportlab
```

## Utilisation

### Utilisation simple

```bash
python json_to_pdf.py results/extraction_consultation_1001.json
```

Cela génère un PDF: `extraction_consultation_1001.pdf`

### Spécifier le fichier de sortie

```bash
python json_to_pdf.py results/extraction_consultation_1001.json mon_rapport.pdf
```

### Traitement par lot

```bash
# Convertir tous les fichiers JSON du dossier results
for file in results/extraction_consultation*.json; do
    python json_to_pdf.py "$file"
done
```

## Format JSON d'entrée

Le script accepte des fichiers JSON avec la structure suivante:

```json
{
  "consultation_report": {
    "motif_de_consultation": "Description du motif",
    "interrogatoire": "Détails de l'interrogatoire",
    "examen_clinique": "Résultats de l'examen",
    "proposition_therapeutique": "Plan de traitement"
  },
  "medical_record": {
    "motif_de_consultation": "Motif principal",
    "historique_medical": "Antécédents généraux",
    "antecedents": {
      "medicaux": ["Liste des antécédents médicaux"],
      "chirurgicaux": ["Liste des interventions"],
      "familiaux": ["Antécédents familiaux"],
      "gynecologiques": []
    },
    "mode_de_vie": {
      "tabac": "Statut tabagique",
      "alcool": "Consommation d'alcool",
      "activite_physique": "Description",
      "autre": "Informations supplémentaires"
    },
    "traitements_habituels": [
      {
        "nom_commercial": "Nom du médicament",
        "molecule": "Molécule active",
        "posologie": "Dosage et fréquence"
      }
    ],
    "allergies": ["Liste des allergies"],
    "interrogatoire": {
      "symptomes_generaux": "Description",
      "symptomes_par_organe": "Description"
    },
    "examen_clinique": {
      "constantes": {
        "poids_kg": null,
        "taille_cm": null,
        "tension_arterielle": "mmHg"
      },
      "examen_specifique": "Détails de l'examen"
    },
    "conclusion": {
      "diagnostic": "Diagnostic établi",
      "proposition_therapeutique": "Traitement proposé",
      "examens_complementaires": ["Liste des examens"],
      "orientation": "Orientations cliniques",
      "prochaine_consultation": "Date/délai de suivi"
    }
  },
  "prescription": {
    "prescriptions": [
      {
        "nom_commercial": "Nom du médicament",
        "molecule": "Molécule",
        "dosage": "Dosage",
        "posologie": {
          "dose": "Dose",
          "frequence": "Fréquence",
          "voie": "Voie d'administration"
        },
        "instructions_complementaires": "Notes additionnelles"
      }
    ]
  }
}
```

## Format PDF de sortie

Le PDF généré comprend les sections suivantes:

1. **Motif de consultation** - Raison principale de la visite
2. **Historique médical**
   - Antécédents (médicaux, chirurgicaux, familiaux)
   - Mode de vie (tabac, alcool, activité physique)
   - Traitements habituels
   - Allergies
3. **Interrogatoire** - Symptômes et plaintes du patient
4. **Examen clinique** - Findings de l'examen physique
5. **Conclusion**
   - Diagnostic
   - Proposition thérapeutique
   - Examens complémentaires recommandés
   - Orientation du patient
   - Date de la prochaine consultation

## Exemples

### Exemple 1 - Conversion simple

```bash
python json_to_pdf.py results/extraction_consultation_1001.json
```

Génère: `extraction_consultation_1001.pdf`

### Exemple 2 - Conversion avec nom personnalisé

```bash
python json_to_pdf.py results/extraction_consultation_1001.json rapport_patient_dupont.pdf
```

### Exemple 3 - Conversion de plusieurs fichiers

```bash
python json_to_pdf.py results/extraction_consultation_1001.json
python json_to_pdf.py results/extraction_consultation_1003.json
python json_to_pdf.py results/extraction_consultation_1006.json
```

## Dépannage

### Erreur: "No module named 'reportlab'"

**Solution:** Installez reportlab
```bash
pip install reportlab
```

### Erreur: "File not found"

**Solution:** Vérifiez le chemin du fichier JSON. Utilisez un chemin absolu si nécessaire:
```bash
python json_to_pdf.py C:\chemin\complet\extraction_consultation_1001.json
```

### Le PDF contient des caractères mal affichés

**Solution:** Assurez-vous que le fichier JSON est encodé en UTF-8. Reportlab supporte nativement les caractères français.

### Le PDF ne contient pas toutes les données

**Solution:** Vérifiez que votre JSON a la structure correcte. Le script ignore silencieusement les champs manquants ou nuls.

## Structure du projet

```
Napoleon/
├── json_to_pdf.py          # Script principal
├── README.md               # Documentation (ce fichier)
├── results/                # Dossier des fichiers JSON d'entrée
│   ├── extraction_consultation_1001.json
│   ├── extraction_consultation_1003.json
│   └── ...
└── .gitignore
```

## Sécurité des données

Ce script traite des données médicales sensibles. Recommandations:

- Utilisez des chemins de fichiers sécurisés
- Limitez l'accès aux fichiers de sortie PDF
- Nettoyez les fichiers temporaires après génération
- Respectez les réglementations RGPD sur les données patients

## Configuration avancée

### Modifier les couleurs

Dans `json_to_pdf.py`, ligne ~55, modifiez les codes couleur HEX:

```python
colors.HexColor('#808080')   # En-têtes gris
colors.HexColor('#2e5c8a')   # Bleu personnalisé
colors.HexColor('#f0f0f0')   # Arrière-plan des lignes
```

### Modifier la taille de police

Recherchez `fontSize=` dans le fichier et ajustez les valeurs:

```python
fontSize=11   # En-têtes
fontSize=10   # Contenu normal
```

### Modifier les dimensions

Les largeurs de colonnes sont définies ligne ~180:

```python
colWidths=[2*inch, 4*inch]  # Première colonne: 2", Deuxième: 4"
```

## Cas d'usage

- Génération automatique de rapports médicaux
- Archivage de consultations en format PDF
- Distribution de rapports aux patients
- Intégration dans des workflows médicaux
- Conversion de données structurées en documents imprimables

## Performance

- Conversion d'un fichier JSON: ~1-2 secondes
- Fichier PDF généré: ~50-200 KB selon la longueur
- Pas de limite connue sur la taille des données

## Support

Pour toute question ou problème:
1. Vérifiez le dépannage ci-dessus
2. Consultez la structure JSON d'exemple
3. Testez avec un fichier JSON simple d'abord

## Licence

Propriétaire - Raul59209

## Auteur

Développé par Raul59209
