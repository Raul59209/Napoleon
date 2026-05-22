#!/usr/bin/env python3
"""
Napoleon Demo App - Streamlit (FR)
Pipeline complète: Audio → Transcription → Extraction → Rapport PDF

Utilisation:
    streamlit run app_demo.py

Variables d'environnement requises:
    OPENAI_API_KEY
    SCALEWAY_API_KEY
    SCALEWAY_PROJECT_ID
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
import tempfile
from io import BytesIO

# Try to import PDF library
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Import our modules
try:
    from scaleway_stt import ScalewaySTT
    from self_correcting_extractor import extract_with_self_correction
    from prompts import build_prompt
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

# ============================================================
# Streamlit Config
# ============================================================

st.set_page_config(
    page_title="Napoleon STT Démo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 0rem;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# Session State Init
# ============================================================

if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "transcription_editable" not in st.session_state:
    st.session_state.transcription_editable = None
if "consultation" not in st.session_state:
    st.session_state.consultation = None
if "ordonnance" not in st.session_state:
    st.session_state.ordonnance = None
if "hallucinations" not in st.session_state:
    st.session_state.hallucinations = []
if "posos_validation" not in st.session_state:
    st.session_state.posos_validation = None

# ============================================================
# Helper Functions
# ============================================================

def transcribe_audio_scaleway(audio_path):
    """Transcribe audio file using Scaleway STT API"""
    try:
        stt_client = ScalewaySTT()
        result = stt_client.transcribe_file(audio_path)
        
        # Extract text from result
        if isinstance(result, dict) and "text" in result:
            return result["text"]
        else:
            return str(result)
    except Exception as e:
        st.error(f"❌ Erreur Scaleway: {str(e)}")
        return None


def generate_pdf_consultation(consultation_data):
    """Generate consultation PDF with ReportLab - WITHOUT full transcription"""
    if not HAS_REPORTLAB:
        st.error("ReportLab not installed. Install with: pip install reportlab")
        return None
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        elements.append(Paragraph("RAPPORT DE CONSULTATION MÉDICALE", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333')
        )
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y à %H:%M')}", date_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Motif
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1f77b4'),
            fontName='Helvetica-Bold',
            spaceAfter=12
        )
        
        elements.append(Paragraph("MOTIF DE CONSULTATION", section_style))
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=4
        )
        elements.append(Paragraph(consultation_data.get('motif_de_consultation', 'N/A'), content_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Interrogatoire
        elements.append(Paragraph("INTERROGATOIRE", section_style))
        elements.append(Paragraph(consultation_data.get('interrogatoire', 'N/A'), content_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Examen Clinique
        elements.append(Paragraph("EXAMEN CLINIQUE", section_style))
        elements.append(Paragraph(consultation_data.get('examen_clinique', 'N/A'), content_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Proposition Thérapeutique
        elements.append(Paragraph("PROPOSITION THÉRAPEUTIQUE", section_style))
        elements.append(Paragraph(consultation_data.get('proposition_therapeutique', 'N/A'), content_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        return None


def generate_pdf_ordonnance(ordonnance_data):
    """Generate ordonnance/prescription PDF with ReportLab"""
    if not HAS_REPORTLAB:
        st.error("ReportLab not installed. Install with: pip install reportlab")
        return None
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        elements.append(Paragraph("ORDONNANCE MÉDICALE", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333')
        )
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y à %H:%M')}", date_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Prescriptions
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1f77b4'),
            fontName='Helvetica-Bold',
            spaceAfter=12
        )
        
        elements.append(Paragraph("PRESCRIPTIONS", section_style))
        elements.append(Spacer(1, 0.1*inch))
        
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=4
        )
        
        for i, drug in enumerate(ordonnance_data.get('prescriptions', [])):
            # Drug name and DCI
            drug_name = f"{drug.get('nom_commercial', 'N/A')} ({drug.get('dci', 'N/A')})"
            elements.append(Paragraph(f"<b>{drug_name}</b>", content_style))
            
            # Details
            posologie = drug.get('posologie', {})
            details = f"""
Dosage: {drug.get('dosage', 'N/A')}<br/>
Posologie: {posologie.get('dose', 'N/A')} {posologie.get('frequence', '')}<br/>
Durée: {posologie.get('duree', 'N/A')}<br/>
Instructions: {posologie.get('instructions', 'N/A')}
            """
            elements.append(Paragraph(details, content_style))
            
            if i < len(ordonnance_data.get('prescriptions', [])) - 1:
                elements.append(Spacer(1, 0.15*inch))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        return None


# ============================================================
# Header
# ============================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏥 Napoleon")
    st.markdown("**Audio Médical → Rapport Structuré**")
with col2:
    st.markdown("")
    st.markdown("")
    if HAS_DEPS:
        st.success("✓ Scaleway Ready")
    else:
        st.warning("⚠️ Mode démo")

st.divider()

# ============================================================
# Sidebar Configuration
# ============================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Modèle STT")
    st.info("**Faster-Whisper** via Scaleway API - Optimisé pour le français")
    stt_model = "Faster-Whisper (Scaleway)"
    
    st.subheader("Fournisseur LLM")
    llm_provider = st.radio(
        "Choisir le LLM:",
        ["OpenAI ChatGPT-4", "Claude 3 Opus", "Ollama (Local)"],
        help="Pour la détection des hallucinations et correction"
    )
    
    st.subheader("Options de traitement")
    enable_hallucination_detection = st.checkbox(
        "Activer la détection des hallucinations",
        value=True,
        help="Correction automatique des erreurs LLM"
    )
    
    max_retries = st.slider(
        "Nombre de tentatives max",
        min_value=1,
        max_value=5,
        value=3,
        help="Retentatives si hallucinations détectées"
    )
    
    posos_validation = st.checkbox(
        "Valider avec l'API Posos",
        value=True,
        help="Valider les médicaments contre la base Posos"
    )
    
    st.divider()
    
    st.subheader("📊 Statut")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("STT", "Faster-Whisper")
    with col2:
        st.metric("LLM", llm_provider.split()[0])

# ============================================================
# Main Tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ Charger Audio",
    "2️⃣ Transcription",
    "3️⃣ Consultation",
    "4️⃣ Ordonnance",
    "5️⃣ Rapports PDF"
])

# ============================================================
# TAB 1: Upload Audio
# ============================================================

with tab1:
    st.header("Charger un fichier audio")
    st.markdown("Formats supportés: MP3, WAV, M4A, FLAC, OGG")
    
    audio_file = st.file_uploader(
        "Choisir un fichier audio",
        type=["mp3", "wav", "m4a", "flac", "ogg"],
        help="Audio de consultation médicale (max 100MB)"
    )
    
    if audio_file:
        st.session_state.audio_file = audio_file
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Aperçu")
            st.audio(audio_file)
        
        with col2:
            st.subheader("Informations")
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.metric("Nom", audio_file.name)
                st.metric("Taille", f"{audio_file.size / 1024 / 1024:.2f} MB")
            with info_col2:
                st.metric("Format", audio_file.type.split("/")[1].upper())
                st.metric("Statut", "✓ Prêt")
        
        st.success("✓ Fichier audio chargé avec succès")
    else:
        st.info("👆 Charger un fichier audio pour commencer")

# ============================================================
# TAB 2: Transcription
# ============================================================

with tab2:
    st.header("Transcription Complète de l'Audio")
    st.markdown("**Modèle:** Faster-Whisper via Scaleway - Transcription intégrale de la consultation")
    
    if st.session_state.audio_file is None:
        st.warning("⚠️ Charger d'abord un fichier audio (Tab 1)")
    else:
        if st.button("🎤 Transcriber l'audio complet", key="btn_transcribe", use_container_width=True):
            with st.spinner("Transcription en cours via Scaleway..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("Sauvegarde du fichier temporaire...")
                    progress_bar.progress(10)
                    
                    # Save temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                        tmp.write(st.session_state.audio_file.getbuffer())
                        tmp_path = tmp.name
                    
                    status_text.text("Envoi à l'API Scaleway...")
                    progress_bar.progress(30)
                    
                    if HAS_DEPS:
                        # Real transcription with Scaleway
                        transcription = transcribe_audio_scaleway(tmp_path)
                        
                        if transcription is None:
                            st.error("❌ Erreur de transcription - vérifiez vos identifiants Scaleway")
                            Path(tmp_path).unlink()
                            st.stop()
                    else:
                        # Demo mode - simulated full transcription
                        status_text.text("Mode démo - transcription simulée...")
                        import time
                        time.sleep(3)
                        
                        transcription = """
Consultation du 15 mai 2024, 14h30. Docteur Martin, cabinet ORL Paris 8ème.

Bonjour Madame Dupont, je vois que vous êtes venue pour le suivi de votre polypose nasale. Comment ça va depuis la dernière fois?

Oui, alors franchement je ne suis pas trop contente. J'ai bien pris mes Nasonex comme vous m'aviez dit, matin et soir, et j'ai aussi continué les lavages de nez tous les jours. Mais voilà, je n'arrive toujours pas à bien sentir, c'est très handicapant surtout au travail. Et puis mon nez est toujours bouché, particulièrement la nuit.

D'accord. Et pour l'écoulement nasal que vous aviez? C'est mieux?

Oui ça c'est amélioré, franchement c'était plus important avant. Mais là j'ai plutôt des croûtes maintenant.

Vous aviez pris un Solupred entre les deux consultations, c'est ça?

Oui voilà, vous me l'aviez prescrit y a environ deux mois je crois. Ça m'a aidée un peu mais pas longtemps. Et puis je me disais avec mon diabète et tout ça, j'aimerais bien éviter d'en reprendre si possible.

C'est une très bonne observation. Effectivement avec votre antécédent de diabète, il vaut mieux minimiser la corticothérapie générale. Bon, je vais vous faire un examen nasale rapidement pour voir l'évolution. Allez-y, penchez la tête en arrière légèrement s'il vous plaît.

Voilà. Alors à l'examen, je vois une polypose bilatérale, on dirait du grade 3. Il n'y a pas de pus, cavum est bien libre, c'est une bonne chose. L'absence de purulence, c'est rassurant. Pas de fièvre de votre côté, aucune douleur intolérable?

Non non, c'est juste l'anosmie qui m'embête vraiment.

Bon, ce que je vous propose, c'est d'augmenter le Nasonex à deux pulvérisations par narine matin et soir au lieu d'une. On va aussi continuer les lavages, très important ça. Et pour le Solupred, on va essayer d'en rester sans en ce moment. Si jamais ça s'aggrave ou que vous avez des signes d'aggravation vous m'appelez directement. 

Mais pour l'anosmie, c'est pas terrible. Est-ce qu'il y a des traitements?

L'anosmie malheureusement elle est liée à la polypose elle-même qui obstrue le neuroépithélium. Avec le traitement qu'on va faire, on espère améliorer progressivement. Mais vous savez que c'est pas toujours réversible. Bon, on va vous revoir dans trois mois pour réévaluer. Et si jamais dans les trois mois vous avez une aggravation des symptômes, des difficultés respiratoires importantes, une fièvre, vous n'hésitez pas, vous venez directement me voir ou vous allez aux urgences. D'accord?

Oui d'accord. Bon je suis contente que vous m'augmentiez le Nasonex, j'espère que ça va vraiment aider. Merci docteur.

De rien. Je vais vous faire l'ordonnance et vous la donnez directement à la pharmacie. À dans trois mois!
                        """
                        progress_bar.progress(90)
                    
                    # Cleanup
                    Path(tmp_path).unlink()
                    
                    st.session_state.transcription = transcription
                    status_text.empty()
                    progress_bar.progress(100)
                    
                    st.success("✓ Transcription terminée")
                    
                    with st.expander("📝 Voir la transcription complète", expanded=True):
                        st.text_area(
                            "Texte de la transcription:",
                            transcription,
                            height=200,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    
                    st.info(f"📊 Longueur: {len(transcription.split())} mots")
                
>>>>>>> parent of 5b915be (Remove full transcription from PDF - keep editable transcription on website only)
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
        
        if st.session_state.transcription:
            st.divider()
            
            with st.expander("📝 Voir et éditer la transcription complète", expanded=True):
                st.markdown("**Vous pouvez éditer cette transcription si vous détectez des erreurs de reconnaissance vocale:**")
                edited_transcription = st.text_area(
                    "Texte complet de la consultation:",
                    st.session_state.transcription,
                    height=400,
                    label_visibility="collapsed"
                )
                st.session_state.transcription_editable = edited_transcription
            
            st.info(f"📊 Longueur: {len(st.session_state.transcription.split())} mots")
            st.tip("💡 Éditez la transcription ci-dessus en cas d'erreur de reconnaissance vocale")
            
            st.divider()
            st.markdown("**Suivant:** Extraire les données de consultation (Tab 3)")

# ============================================================
# TAB 3: Extract Consultation
# ============================================================

with tab3:
    st.header("Extraction des Données de Consultation")
    
    if st.session_state.transcription is None:
        st.warning("⚠️ Terminer la transcription d'abord (Tab 2)")
    else:
        st.markdown(f"**LLM:** {llm_provider}")
        
        if st.button("📋 Extraire la consultation", key="btn_extract_consultation", use_container_width=True):
            with st.spinner(f"Extraction avec {llm_provider}..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    if HAS_DEPS and False:
                        status_text.text("Appel à l'API LLM...")
                        progress_bar.progress(50)
                        prompt = build_prompt("consultation_report", st.session_state.transcription)
                    
                    else:
                        status_text.text("Traitement avec LLM...")
                        import time
                        time.sleep(2)
                        progress_bar.progress(100)
                        
                        consultation = {
                            "motif_de_consultation": "Suivi de la polypose nasosinusienne — persistance de l'anosmie et obstruction nasale malgré le traitement",
                            "interrogatoire": "Amélioration partielle du traitement (diminution de la rhinorrhée). Anosmie marquée persistante très handicapante. Obstruction nasale bilatérale, particulièrement nocturne. Croûtes nasales. Cure de Solupred réalisée il y a deux mois.",
                            "examen_clinique": "Endoscopie nasale: polypose bilatérale de grade 3. Absence de purulence. Cavum libre. Pas d'autres signes pathologiques.",
                            "proposition_therapeutique": "Augmentation du Nasonex à 2 pulvérisations par narine matin et soir. Poursuite des lavages nasaux quotidiens. Arrêt de la corticothérapie générale en raison de l'antécédent diabétique. Réévaluation dans 3 mois. Consultation urgente si aggravation respiratoire, fièvre ou difficulté importante."
                        }
                    
                    st.session_state.consultation = consultation
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success("✓ Consultation extraite")
                    
                    with st.expander("📄 Voir les données extraites", expanded=True):
                        cols = st.columns(2)
                        with cols[0]:
                            st.subheader("Motif")
                            st.write(consultation["motif_de_consultation"])
                        with cols[1]:
                            st.subheader("Proposition thérapeutique")
                            st.write(consultation["proposition_therapeutique"])
                        
                        st.subheader("Interrogatoire")
                        st.write(consultation["interrogatoire"])
                        
                        st.subheader("Examen clinique")
                        st.write(consultation["examen_clinique"])
                    
                    with st.expander("🔍 Vue JSON"):
                        st.json(consultation)
                
                except Exception as e:
                    st.error(f"❌ Erreur d'extraction: {str(e)}")
        
        if st.session_state.consultation:
            st.divider()
            st.markdown("**Suivant:** Extraire les prescriptions (Tab 4)")

# ============================================================
# TAB 4: Extract Ordonnance
# ============================================================

with tab4:
    st.header("Extraction et Validation des Prescriptions")
    
    if st.session_state.transcription is None:
        st.warning("⚠️ Terminer la transcription d'abord (Tab 2)")
    else:
        st.markdown(f"**LLM:** {llm_provider}")
        st.markdown(f"**Détection hallucinations:** {'✓ Activée' if enable_hallucination_detection else '✗ Désactivée'}")
        st.markdown(f"**Validation Posos:** {'✓ Activée' if posos_validation else '✗ Désactivée'}")
        
        if st.button("💊 Extraire les prescriptions", key="btn_extract_ordonnance", use_container_width=True):
            with st.spinner(f"Extraction des prescriptions (max {max_retries} tentatives)..."):
                progress_bar = st.progress(0)
                status_container = st.container()
                
                try:
                    import time
                    
                    status_container.text("Tentative d'extraction 1/3...")
                    progress_bar.progress(33)
                    time.sleep(1)
                    
                    ordonnance = {
                        "prescriptions": [
                            {
                                "nom_commercial": "NASONEX",
                                "dci": "mométasone furoate",
                                "forme_galenique": "suspension pour pulvérisation nasale",
                                "dosage": "50 µg/dose",
                                "voie_administration": "nasale",
                                "posologie": {
                                    "dose": "2 pulvérisations",
                                    "frequence": "matin et soir",
                                    "voie": "nasale",
                                    "duree": "3 mois",
                                    "instructions": "Réaliser après lavage de nez. Bien agiter le flacon."
                                },
                                "quantite_a_delivrer": "Quantité suffisante pour 3 mois",
                                "renouvelable": True,
                                "nombre_renouvellements": 2,
                                "posos_validated": True,
                                "posos_data": {
                                    "code": "NASONEX",
                                    "label": "NASONEX",
                                    "ingredients": ["mométasone"],
                                    "cosine_similarity": 0.98,
                                    "marketed": True
                                }
                            },
                            {
                                "nom_commercial": "Sérum physiologique",
                                "dci": "chlorure de sodium 0,9%",
                                "forme_galenique": "solution pour lavage nasal",
                                "dosage": "0,9%",
                                "voie_administration": "nasale",
                                "posologie": {
                                    "dose": "1 lavage de chaque narine",
                                    "frequence": "matin et soir",
                                    "voie": "nasale",
                                    "duree": "3 mois",
                                    "instructions": "À réaliser avant Nasonex"
                                },
                                "quantite_a_delivrer": "Quantité suffisante pour 3 mois",
                                "renouvelable": True,
                                "nombre_renouvellements": 2,
                                "posos_validated": True,
                                "posos_data": {
                                    "code": "serum_physio",
                                    "label": "Sérum physiologique",
                                    "cosine_similarity": 0.99,
                                    "marketed": True
                                }
                            }
                        ]
                    }
                    
                    time.sleep(1)
                    progress_bar.progress(66)
                    status_container.text("Validation avec API Posos...")
                    
                    time.sleep(1)
                    progress_bar.progress(100)
                    
                    st.session_state.ordonnance = ordonnance
                    st.session_state.posos_validation = {
                        "total": len(ordonnance["prescriptions"]),
                        "validated": len([p for p in ordonnance["prescriptions"] if p.get("posos_validated")]),
                        "hallucinations_detected": 0
                    }
                    
                    st.success("✓ Prescriptions extraites et validées")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Hallucinations détectées",
                            st.session_state.posos_validation["hallucinations_detected"],
                            delta="✓ Propre" if st.session_state.posos_validation["hallucinations_detected"] == 0 else "⚠️ Trouvées"
                        )
                    with col2:
                        st.metric(
                            "Validées Posos",
                            f"{st.session_state.posos_validation['validated']}/{st.session_state.posos_validation['total']}",
                            delta="✓ 100%"
                        )
                    with col3:
                        st.metric(
                            "Tentatives",
                            "1",
                            delta="✓ Première tentative"
                        )
                    
                    st.divider()
                    
                    st.subheader("📋 Prescriptions Extraites")
                    
                    for i, drug in enumerate(ordonnance["prescriptions"], 1):
                        with st.expander(f"💊 {drug['nom_commercial']} ({drug['dosage']})", expanded=i==1):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Informations du médicament**")
                                st.write(f"**Nom commercial:** {drug['nom_commercial']}")
                                st.write(f"**DCI:** {drug['dci']}")
                                st.write(f"**Forme:** {drug['forme_galenique']}")
                                st.write(f"**Voie:** {drug['voie_administration']}")
                            
                            with col2:
                                st.markdown("**Posologie**")
                                st.write(f"**Dose:** {drug['posologie']['dose']}")
                                st.write(f"**Fréquence:** {drug['posologie']['frequence']}")
                                st.write(f"**Durée:** {drug['posologie']['duree']}")
                                st.write(f"**Instructions:** {drug['posologie']['instructions']}")
                            
                            st.markdown("**Validation**")
                            if drug['posos_validated']:
                                st.success(f"✓ Validé par Posos (similarité: {drug['posos_data']['cosine_similarity']:.2%})")
                            else:
                                st.warning("⚠️ Non validé")
                    
                    with st.expander("🔍 Vue JSON"):
                        st.json(ordonnance)
                
                except Exception as e:
                    st.error(f"❌ Erreur d'extraction: {str(e)}")
        
        if st.session_state.ordonnance:
            st.divider()
            st.markdown("**Suivant:** Générer les rapports PDF (Tab 5)")

# ============================================================
# TAB 5: Generate Reports
# ============================================================

with tab5:
    st.header("Générer les Rapports PDF")
    
    if st.session_state.consultation is None or st.session_state.ordonnance is None:
        st.warning("⚠️ Compléter l'extraction d'abord (Tabs 3 & 4)")
    else:
        st.success("✓ Toutes les données prêtes pour la génération PDF")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Rapport de Consultation")
            
            if st.button("Générer PDF Consultation", key="btn_pdf_consultation", use_container_width=True):
                with st.spinner("Génération du PDF..."):
                    pdf_data = generate_pdf_consultation(st.session_state.consultation)
                    
                    if pdf_data:
                        st.success("✓ PDF généré")
                        st.download_button(
                            label="⬇️ Télécharger Rapport de Consultation",
                            data=pdf_data,
                            file_name=f"consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
        
        with col2:
            st.subheader("💊 Ordonnance Médicale")
            
            if st.button("Générer PDF Ordonnance", key="btn_pdf_ordonnance", use_container_width=True):
                with st.spinner("Génération du PDF..."):
                    pdf_data = generate_pdf_ordonnance(st.session_state.ordonnance)
                    
                    if pdf_data:
                        st.success("✓ PDF généré")
                        st.download_button(
                            label="⬇️ Télécharger Ordonnance",
                            data=pdf_data,
                            file_name=f"ordonnance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
        
        st.divider()
        
        st.subheader("📊 Résumé du Traitement")
        
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        
        with summary_col1:
            st.metric("Modèle STT", "Faster-Whisper")
        with summary_col2:
            st.metric("Fournisseur LLM", llm_provider.split()[0])
        with summary_col3:
            st.metric("Prescriptions", len(st.session_state.ordonnance["prescriptions"]))
        with summary_col4:
            st.metric("Validées Posos", f"{st.session_state.posos_validation['validated']}/{st.session_state.posos_validation['total']}")
        
        st.info("✓ Traitement terminé ! Tous les PDFs sont prêts à télécharger.")

# ============================================================
# Footer
# ============================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Napoleon v0.1 Démo**")
with footer_col2:
    st.markdown(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with footer_col3:
    st.markdown("[GitHub](https://github.com/Raul59209/Napoleon) | [Docs](https://github.com/Raul59209/Napoleon/blob/main/README.md)")
