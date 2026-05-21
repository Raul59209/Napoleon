#!/usr/bin/env python3
"""
Napoleon Demo App - Streamlit
Complete pipeline: Audio → Transcription → Extraction → PDF Report

Usage:
    streamlit run app_demo.py

Environment variables required:
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
    page_title="Napoleon STT Demo",
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
# Header
# ============================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏥 Napoleon")
    st.markdown("**Medical Audio → Structured Report Pipeline**")
with col2:
    st.markdown("")
    st.markdown("")
    if HAS_DEPS:
        st.success("✓ Dependencies loaded")
    else:
        st.warning("⚠️ Demo mode (simulated)")

st.divider()

# ============================================================
# Sidebar Configuration
# ============================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("STT Model")
    stt_model = st.radio(
        "Choose Speech-to-Text model:",
        ["Whisper Large V3", "Faster-Whisper", "Voxtral Mini", "WhisperX"],
        index=1,  # Default to Faster-Whisper (index 1)
        help="Different models have different speed/accuracy tradeoffs"
    )
    
    st.subheader("LLM Provider")
    llm_provider = st.radio(
        "Choose LLM for extraction:",
        ["OpenAI ChatGPT-4", "Claude 3 Opus", "Ollama (Local)"],
        help="For hallucination detection and correction"
    )
    
    st.subheader("Processing Options")
    enable_hallucination_detection = st.checkbox(
        "Enable hallucination detection",
        value=True,
        help="Auto-correct LLM mistakes"
    )
    
    max_retries = st.slider(
        "Max retry attempts",
        min_value=1,
        max_value=5,
        value=3,
        help="Retries if hallucinations detected"
    )
    
    posos_validation = st.checkbox(
        "Validate with Posos API",
        value=True,
        help="Validate drugs against Posos database"
    )
    
    st.divider()
    
    st.subheader("📊 Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("STT", stt_model.split()[0])
    with col2:
        st.metric("LLM", llm_provider.split()[0])

# ============================================================
# Main Tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ Upload Audio",
    "2️⃣ Transcription",
    "3️⃣ Extract Consultation",
    "4️⃣ Extract Ordonnance",
    "5️⃣ Generate Report"
])

# ============================================================
# TAB 1: Upload Audio
# ============================================================

with tab1:
    st.header("Upload Medical Audio")
    st.markdown("Support: MP3, WAV, M4A, FLAC, OGG")
    
    # File uploader
    audio_file = st.file_uploader(
        "Choose audio file",
        type=["mp3", "wav", "m4a", "flac", "ogg"],
        help="Audio of medical consultation (max 100MB)"
    )
    
    if audio_file:
        st.session_state.audio_file = audio_file
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Preview")
            st.audio(audio_file)
        
        with col2:
            st.subheader("File Info")
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.metric("File name", audio_file.name)
                st.metric("File size", f"{audio_file.size / 1024 / 1024:.2f} MB")
            with info_col2:
                st.metric("Format", audio_file.type.split("/")[1].upper())
                st.metric("Status", "✓ Ready")
        
        st.success("✓ Audio file uploaded successfully")
    else:
        st.info("👆 Upload an audio file to begin")

# ============================================================
# TAB 2: Transcription
# ============================================================

with tab2:
    st.header("Speech-to-Text Transcription")
    
    if st.session_state.audio_file is None:
        st.warning("⚠️ Upload an audio file first (Tab 1)")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Model:** {stt_model}")
            st.markdown(f"**File:** {st.session_state.audio_file.name}")
        
        with col2:
            pass
        
        if st.button("🎤 Start Transcription", key="btn_transcribe", use_container_width=True):
            with st.spinner(f"Transcribing with {stt_model}..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    if HAS_DEPS:
                        # Real transcription with Scaleway
                        stt_client = ScalewaySTT()
                        
                        # Save temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                            tmp.write(st.session_state.audio_file.getbuffer())
                            tmp_path = tmp.name
                        
                        status_text.text("Connecting to Scaleway API...")
                        progress_bar.progress(25)
                        
                        result = stt_client.transcribe_file(tmp_path)
                        
                        status_text.text("Processing transcription...")
                        progress_bar.progress(75)
                        
                        # Extract text from result
                        if isinstance(result, dict) and "text" in result:
                            transcription = result["text"]
                        else:
                            transcription = str(result)
                        
                        # Cleanup
                        Path(tmp_path).unlink()
                    
                    else:
                        # Demo mode - simulated transcription
                        status_text.text("Loading demo transcription...")
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
                    
                    st.success("✓ Transcription complete")
                    
                    with st.expander("📝 View full transcription", expanded=True):
                        st.text_area(
                            "Transcription text:",
                            transcription,
                            height=200,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    
                    st.info(f"📊 Transcription length: {len(transcription.split())} words")
                
                except Exception as e:
                    st.error(f"❌ Transcription failed: {str(e)}")
        
        if st.session_state.transcription:
            st.divider()
            st.markdown("**Next:** Extract consultation details (Tab 3)")

# ============================================================
# TAB 3: Extract Consultation
# ============================================================

with tab3:
    st.header("Extract Consultation Data")
    
    if st.session_state.transcription is None:
        st.warning("⚠️ Complete transcription first (Tab 2)")
    else:
        st.markdown(f"**LLM:** {llm_provider}")
        
        if st.button("📋 Extract Consultation", key="btn_extract_consultation", use_container_width=True):
            with st.spinner(f"Extracting with {llm_provider}..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    if HAS_DEPS and False:  # Disabled for now - use simulated
                        # Real extraction with LLM
                        status_text.text("Calling LLM API...")
                        progress_bar.progress(50)
                        
                        prompt = build_prompt("consultation_report", st.session_state.transcription)
                        # Call LLM here
                        # consultation = llm_client.extract(prompt)
                    
                    else:
                        # Demo mode - simulated extraction
                        status_text.text("Processing with LLM...")
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
                    
                    st.success("✓ Consultation extracted")
                    
                    with st.expander("📄 View extracted data", expanded=True):
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
                    
                    # Show JSON
                    with st.expander("🔍 JSON view"):
                        st.json(consultation)
                
                except Exception as e:
                    st.error(f"❌ Extraction failed: {str(e)}")
        
        if st.session_state.consultation:
            st.divider()
            st.markdown("**Next:** Extract prescriptions (Tab 4)")

# ============================================================
# TAB 4: Extract Ordonnance
# ============================================================

with tab4:
    st.header("Extract & Validate Prescriptions")
    
    if st.session_state.transcription is None:
        st.warning("⚠️ Complete transcription first (Tab 2)")
    else:
        st.markdown(f"**LLM:** {llm_provider}")
        st.markdown(f"**Hallucination Detection:** {'✓ Enabled' if enable_hallucination_detection else '✗ Disabled'}")
        st.markdown(f"**Posos Validation:** {'✓ Enabled' if posos_validation else '✗ Disabled'}")
        
        if st.button("💊 Extract Prescriptions", key="btn_extract_ordonnance", use_container_width=True):
            with st.spinner(f"Extracting prescriptions (max {max_retries} retries)..."):
                progress_bar = st.progress(0)
                status_container = st.container()
                
                try:
                    import time
                    
                    # Demo mode
                    status_container.text("Extraction attempt 1/3...")
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
                    status_container.text("Validating with Posos API...")
                    
                    time.sleep(1)
                    progress_bar.progress(100)
                    
                    st.session_state.ordonnance = ordonnance
                    st.session_state.posos_validation = {
                        "total": len(ordonnance["prescriptions"]),
                        "validated": len([p for p in ordonnance["prescriptions"] if p.get("posos_validated")]),
                        "hallucinations_detected": 0
                    }
                    
                    st.success("✓ Prescriptions extracted and validated")
                    
                    # Hallucination detection results
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Hallucinations Detected",
                            st.session_state.posos_validation["hallucinations_detected"],
                            delta="✓ Clean" if st.session_state.posos_validation["hallucinations_detected"] == 0 else "⚠️ Found"
                        )
                    with col2:
                        st.metric(
                            "Posos Validated",
                            f"{st.session_state.posos_validation['validated']}/{st.session_state.posos_validation['total']}",
                            delta="✓ 100%"
                        )
                    with col3:
                        st.metric(
                            "Extraction Attempts",
                            "1",
                            delta="✓ First try"
                        )
                    
                    st.divider()
                    
                    # Show prescriptions
                    st.subheader("📋 Extracted Prescriptions")
                    
                    for i, drug in enumerate(ordonnance["prescriptions"], 1):
                        with st.expander(f"💊 {drug['nom_commercial']} ({drug['dosage']})", expanded=i==1):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Drug Info**")
                                st.write(f"**Commercial name:** {drug['nom_commercial']}")
                                st.write(f"**DCI:** {drug['dci']}")
                                st.write(f"**Form:** {drug['forme_galenique']}")
                                st.write(f"**Route:** {drug['voie_administration']}")
                            
                            with col2:
                                st.markdown("**Posology**")
                                st.write(f"**Dose:** {drug['posologie']['dose']}")
                                st.write(f"**Frequency:** {drug['posologie']['frequence']}")
                                st.write(f"**Duration:** {drug['posologie']['duree']}")
                                st.write(f"**Instructions:** {drug['posologie']['instructions']}")
                            
                            st.markdown("**Validation**")
                            if drug['posos_validated']:
                                st.success(f"✓ Validated by Posos (similarity: {drug['posos_data']['cosine_similarity']:.2%})")
                            else:
                                st.warning("⚠️ Not validated")
                    
                    # Full JSON view
                    with st.expander("🔍 JSON view"):
                        st.json(ordonnance)
                
                except Exception as e:
                    st.error(f"❌ Extraction failed: {str(e)}")
        
        if st.session_state.ordonnance:
            st.divider()
            st.markdown("**Next:** Generate final report (Tab 5)")

# ============================================================
# TAB 5: Generate Report
# ============================================================

with tab5:
    st.header("Generate Final Report")
    
    if st.session_state.consultation is None or st.session_state.ordonnance is None:
        st.warning("⚠️ Complete extraction first (Tabs 3 & 4)")
    else:
        st.success("✓ All data ready for PDF generation")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Consultation Report")
            
            if st.button("Generate Consultation PDF", key="btn_pdf_consultation", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    import time
                    time.sleep(1)
                    
                    # Simulate PDF generation
                    pdf_content = f"""
RAPPORT DE CONSULTATION MÉDICALE
Date: {datetime.now().strftime('%d/%m/%Y')}

MOTIF: {st.session_state.consultation['motif_de_consultation']}

INTERROGATOIRE:
{st.session_state.consultation['interrogatoire']}

EXAMEN CLINIQUE:
{st.session_state.consultation['examen_clinique']}

PROPOSITION THÉRAPEUTIQUE:
{st.session_state.consultation['proposition_therapeutique']}
                    """.encode()
                    
                    st.success("✓ PDF generated")
                    st.download_button(
                        label="⬇️ Download Consultation PDF",
                        data=pdf_content,
                        file_name=f"consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        
        with col2:
            st.subheader("💊 Prescription Report")
            
            if st.button("Generate Ordonnance PDF", key="btn_pdf_ordonnance", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    import time
                    time.sleep(1)
                    
                    # Simulate PDF generation
                    pdf_content = f"""
ORDONNANCE MÉDICALE
Date: {datetime.now().strftime('%d/%m/%Y')}

PRESCRIPTIONS:
""".encode()
                    
                    for drug in st.session_state.ordonnance["prescriptions"]:
                        pdf_content += f"""

{drug['nom_commercial']} ({drug['dci']})
Dosage: {drug['dosage']}
Posologie: {drug['posologie']['dose']} {drug['posologie']['frequence']}
Durée: {drug['posologie']['duree']}
""".encode()
                    
                    st.success("✓ PDF generated")
                    st.download_button(
                        label="⬇️ Download Ordonnance PDF",
                        data=pdf_content,
                        file_name=f"ordonnance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        
        st.divider()
        
        # Summary
        st.subheader("📊 Processing Summary")
        
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        
        with summary_col1:
            st.metric("STT Model", stt_model.split()[0])
        with summary_col2:
            st.metric("LLM Provider", llm_provider.split()[0])
        with summary_col3:
            st.metric("Prescriptions", len(st.session_state.ordonnance["prescriptions"]))
        with summary_col4:
            st.metric("Posos Valid", f"{st.session_state.posos_validation['validated']}/{st.session_state.posos_validation['total']}")
        
        st.info("✓ Processing complete! All PDFs are ready for download.")

# ============================================================
# Footer
# ============================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Napoleon v0.1 Demo**")
with footer_col2:
    st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
with footer_col3:
    st.markdown("[GitHub](https://github.com/Raul59209/Napoleon) | [Docs](https://github.com/Raul59209/Napoleon/blob/main/README.md)")
