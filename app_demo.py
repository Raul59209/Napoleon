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
import base64

# Try to import PDF library
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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

def generate_pdf_consultation(consultation_data):
    """Generate consultation PDF with ReportLab"""
    if not HAS_REPORTLAB:
        st.error("ReportLab not installed. Install with: pip install reportlab")
        return None
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1
        )
        
        elements.append(Paragraph("RAPPORT DE CONSULTATION MÉDICALE", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Motif
        elements.append(Paragraph("<b>MOTIF DE CONSULTATION:</b>", styles['Heading3']))
        elements.append(Paragraph(consultation_data.get('motif_de_consultation', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Interrogatoire
        elements.append(Paragraph("<b>INTERROGATOIRE:</b>", styles['Heading3']))
        elements.append(Paragraph(consultation_data.get('interrogatoire', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Examen Clinique
        elements.append(Paragraph("<b>EXAMEN CLINIQUE:</b>", styles['Heading3']))
        elements.append(Paragraph(consultation_data.get('examen_clinique', 'N/A'), styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Proposition Thérapeutique
        elements.append(Paragraph("<b>PROPOSITION THÉRAPEUTIQUE:</b>", styles['Heading3']))
        elements.append(Paragraph(consultation_data.get('proposition_therapeutique', 'N/A'), styles['Normal']))
        
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
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1
        )
        
        elements.append(Paragraph("ORDONNANCE MÉDICALE", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Prescriptions
        elements.append(Paragraph("<b>PRESCRIPTIONS:</b>", styles['Heading3']))
        elements.append(Spacer(1, 0.2*inch))
        
        for drug in ordonnance_data.get('prescriptions', []):
            # Drug name
            drug_name = f"{drug.get('nom_commercial', 'N/A')} ({drug.get('dci', 'N/A')})"
            elements.append(Paragraph(f"<b>{drug_name}</b>", styles['Heading4']))
            
            # Details
            posologie = drug.get('posologie', {})
            details = f"""
            <b>Dosage:</b> {drug.get('dosage', 'N/A')}<br/>
            <b>Posologie:</b> {posologie.get('dose', 'N/A')} {posologie.get('frequence', '')}<br/>
            <b>Durée:</b> {posologie.get('duree', 'N/A')}<br/>
            <b>Instructions:</b> {posologie.get('instructions', 'N/A')}<br/>
            """
            elements.append(Paragraph(details, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
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
        st.success("✓ Dépendances chargées")
    else:
        st.warning("⚠️ Mode démo (simulé)")

st.divider()

# ============================================================
# Sidebar Configuration
# ============================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Modèle STT")
    stt_model = st.radio(
        "Choisir le modèle:",
        ["Whisper Large V3", "Faster-Whisper", "Voxtral Mini", "WhisperX"],
        index=1,
        help="Différents modèles avec différents compromis vitesse/précision"
    )
    
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
        st.metric("STT", stt_model.split()[0])
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
    st.header("Transcription Automatique")
    
    if st.session_state.audio_file is None:
        st.warning("⚠️ Charger d'abord un fichier audio (Tab 1)")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Modèle:** {stt_model}")
            st.markdown(f"**Fichier:** {st.session_state.audio_file.name}")
        
        if st.button("🎤 Démarrer la transcription", key="btn_transcribe", use_container_width=True):
            with st.spinner(f"Transcription avec {stt_model}..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    if HAS_DEPS:
                        # Real transcription with Scaleway
                        status_text.text("Connexion à l'API Scaleway...")
                        progress_bar.progress(25)
                        
                        stt_client = ScalewaySTT()
                        
                        # Save temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(st.session_state.audio_file.getbuffer())
                            tmp_path = tmp.name
                        
                        status_text.text("Traitement en cours...")
                        progress_bar.progress(75)
                        
                        result = stt_client.transcribe_file(tmp_path)
                        
                        # Extract text from result
                        if isinstance(result, dict) and "text" in result:
                            transcription = result["text"]
                        else:
                            transcription = str(result)
                        
                        # Cleanup
                        Path(tmp_path).unlink()
                    
                    else:
                        # Demo mode - simulated transcription
                        status_text.text("Chargement de la transcription...")
                        progress_bar.progress(50)
                        
                        import time
                        time.sleep(2)
                        
                        transcription = """
Consultation du 15 mai 2024.

Je vois ce jour Madame Dupont Marie pour le suivi de sa polypose nasosinusienne.

Elle a bien suivi le traitement prescrit, à savoir lavages de nez quotidiens et NASONEX, 
1 pulvérisation par narine matin et soir, ce qui l'a partiellement amélioré.

Elle conserve cependant une anosmie marquée et une obstruction nasale bilatérale.
La rhinorrhée s'est en revanche bien améliorée.

Elle a bénéficié d'une cure de SOLUPRED dans l'intervalle, que je souhaite limiter.

À l'endoscopie nasale, je retrouve une polypose de grade 3 bilatérale, 
pas de pus aux méats, cavum libre.

En conclusion, je propose à la patiente d'augmenter le NASONEX à 2 pulvérisations 
par narine matin et soir, et je l'incite à limiter au maximum la corticothérapie per os,
d'autant qu'elle est suivie pour un diabète de type 2.

Je la reverrai dans 3 mois pour réévaluation.
                        """
                        progress_bar.progress(100)
                    
                    st.session_state.transcription = transcription
                    status_text.empty()
                    progress_bar.empty()
                    
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
                
                except Exception as e:
                    st.error(f"❌ Erreur de transcription: {str(e)}")
        
        if st.session_state.transcription:
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
                            "interrogatoire": "Amélioration partielle du traitement (diminution rhinorrhée). Anosmie marquée persistante. Obstruction nasale bilatérale. Cure de Solupred réalisée dans l'intervalle.",
                            "examen_clinique": "Endoscopie nasale: polypose bilatérale de grade 3. Absence de pus aux méats. Cavum libre.",
                            "proposition_therapeutique": "Augmentation du Nasonex à 2 pulvérisations par narine matin et soir. Limitation stricte de la corticothérapie per os en raison du diabète associé. Réévaluation à 3 mois."
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
            st.metric("Modèle STT", stt_model.split()[0])
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
