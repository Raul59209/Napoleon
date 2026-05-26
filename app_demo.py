"""
app_demo.py — Napoleon Medical Pipeline Demo
============================================
Streamlit interface for the full pipeline:
  Tab 1: Upload audio → transcribe with faster-whisper → hallucination check
  Tab 2: LLM extraction → CR, DPI, ordonnance (Scaleway)
  Tab 3: PDF generation + download

Run:
    pip install streamlit faster-whisper openai python-dotenv reportlab
    streamlit run app_demo.py
"""

import io
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Napoleon — Pipeline Médical",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .main { background-color: #F7F6F2; }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }

    h1, h2, h3 {
        font-family: 'DM Serif Display', serif;
        color: #0D1B3E;
    }

    .napoleon-header {
        background: linear-gradient(135deg, #0D1B3E 0%, #1a2f5e 100%);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .napoleon-header h1 {
        color: white !important;
        font-size: 2.2rem;
        margin: 0;
        font-family: 'DM Serif Display', serif;
    }

    .napoleon-header p {
        color: #A0B4CC;
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }

    .napoleon-badge {
        background: #028090;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .step-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E8E6E0;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .step-card h4 {
        font-family: 'DM Serif Display', serif;
        color: #0D1B3E;
        margin-bottom: 0.5rem;
        font-size: 1.1rem;
    }

    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }

    .metric-box {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        flex: 1;
        text-align: center;
    }

    .metric-box .value {
        font-size: 1.6rem;
        font-weight: 600;
        color: #028090;
        font-family: 'DM Serif Display', serif;
    }

    .metric-box .label {
        font-size: 0.75rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .alert-ok {
        background: #ECFDF5;
        border: 1px solid #6EE7B7;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        color: #065F46;
        font-weight: 500;
    }

    .alert-warn {
        background: #FFF7ED;
        border: 1px solid #FCD34D;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        color: #92400E;
        font-weight: 500;
    }

    .alert-error {
        background: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        color: #991B1B;
        font-weight: 500;
    }

    .transcript-box {
        background: #FAFAF8;
        border: 1px solid #E8E6E0;
        border-radius: 8px;
        padding: 1.2rem;
        font-size: 0.9rem;
        line-height: 1.7;
        color: #374151;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: 'DM Sans', sans-serif;
    }

    .json-section {
        background: white;
        border-radius: 12px;
        border: 1px solid #E8E6E0;
        margin-bottom: 1rem;
        overflow: hidden;
    }

    .json-section-header {
        background: #0D1B3E;
        color: white;
        padding: 0.8rem 1.2rem;
        font-weight: 600;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: white;
        border-radius: 12px;
        padding: 6px;
        border: 1px solid #E8E6E0;
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        color: #64748B;
    }

    .stTabs [aria-selected="true"] {
        background: #0D1B3E !important;
        color: white !important;
    }

    .stButton > button {
        background: #028090;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        font-family: 'DM Sans', sans-serif;
        transition: background 0.2s;
    }

    .stButton > button:hover {
        background: #026070;
    }

    .stDownloadButton > button {
        background: #0D1B3E;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    div[data-testid="stFileUploader"] {
        background: white;
        border-radius: 12px;
        border: 2px dashed #CBD5E1;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="napoleon-header">
    <div style="font-size:2.5rem">🩺</div>
    <div>
        <h1>Napoleon</h1>
        <p>Pipeline de traitement audio médical — transcription, extraction, rapport</p>
    </div>
    <div style="margin-left:auto">
        <span class="napoleon-badge">Demo</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "hallucination_ok" not in st.session_state:
    st.session_state.hallucination_ok = None
if "review" not in st.session_state:
    st.session_state.review = None
if "extraction" not in st.session_state:
    st.session_state.extraction = None
if "audio_filename" not in st.session_state:
    st.session_state.audio_filename = None


# ── Utilities ─────────────────────────────────────────────────────────────────

def detect_hallucination(text: str) -> tuple[bool, str]:
    """
    Returns (is_hallucinating, reason).
    Detects Whisper loop hallucinations by checking for repeated sentences.
    """
    if not text or len(text.strip()) < 10:
        return True, "Transcription vide ou trop courte."

    sentences = [s.strip() for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()]

    if len(sentences) < 3:
        return False, "OK"

    counts = Counter(sentences)
    most_common, freq = counts.most_common(1)[0]

    if freq > 5:
        return True, f"Boucle détectée : \"{most_common[:60]}...\" répété {freq} fois."

    # Check repetition ratio — if 30%+ of sentences are identical
    if freq / len(sentences) > 0.3 and freq > 3:
        return True, f"Contenu répétitif suspect : \"{most_common[:60]}\" ({freq}/{len(sentences)} phrases identiques)."

    # Check total length vs unique content
    unique_chars = len(" ".join(set(sentences)))
    total_chars = len(text)
    if total_chars > 500 and unique_chars / total_chars < 0.15:
        return True, "Ratio contenu unique/total très faible — hallucination probable."

    return False, "Aucune boucle détectée."


def transcribe_audio(audio_bytes: bytes, filename: str) -> tuple[str, float]:
    """Transcribe audio using faster-whisper. Returns (text, rtf)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        st.error("faster-whisper non installé. `pip install faster-whisper`")
        return None, -1

    with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Load model — try GPU first, fall back to CPU
        try:
            model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            device_used = "cuda/float16"
        except Exception:
            model = WhisperModel("large-v3", device="cpu", compute_type="int8")
            device_used = "cpu/int8"

        t0 = time.perf_counter()
        segments_gen, info = model.transcribe(
            tmp_path,
            language="fr",
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            initial_prompt=(
                "Transcription médicale en français. "
                "Termes: mg, ml, narine, polypes, cortisone, Nasonex, "
                "atorvastatine, périndopril, audiogramme, VPPB."
            ),
        )
        text = " ".join(seg.text.strip() for seg in segments_gen)
        elapsed = time.perf_counter() - t0
        duration = info.duration if hasattr(info, "duration") else -1
        rtf = elapsed / duration if duration > 0 else -1

        return text.strip(), rtf, device_used, duration

    finally:
        os.unlink(tmp_path)


def call_llm(transcript: str, output_type: str) -> dict:
    """Call Scaleway LLM for extraction."""
    try:
        from openai import OpenAI
        sys.path.insert(0, str(Path(__file__).parent))
        from prompts import build_prompt
    except ImportError as e:
        return {"error": str(e)}

    api_key = os.environ.get("SCW_API_KEY")
    if not api_key:
        return {"error": "SCW_API_KEY non définie dans .env"}

    client = OpenAI(
        base_url="https://api.scaleway.ai/v1",
        api_key=api_key,
    )

    try:
        prompt = build_prompt(output_type, transcript)
        # Review needs more tokens — it returns the full corrected transcript
        # plus all corrections. Other prompts are fine with 2000.
        max_tokens = 4000 if output_type == "review" else 2000
        response = client.chat.completions.create(
            model="llama-3.3-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"JSON invalide: {e}", "raw": raw[:500]}
    except Exception as e:
        return {"error": str(e)}


def generate_pdf(extraction: dict, filename_stem: str) -> bytes:
    """Generate PDF from extraction dict. Returns PDF bytes."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle("Header", parent=styles["Normal"],
                                   fontSize=11, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("Body", parent=styles["Normal"],
                                   fontSize=10, alignment=TA_LEFT)

    def safe(obj, key, default=""):
        if obj is None: return default
        return obj.get(key, default) or default

    report = extraction.get("consultation_report", {})
    record = extraction.get("medical_record", {})
    prescription = extraction.get("prescription", {})

    rows = []

    # CR section
    rows.append([Paragraph("<b>Compte-rendu de consultation</b>", header_style), ""])
    for label, key in [
        ("Motif", "motif_de_consultation"),
        ("Interrogatoire", "interrogatoire"),
        ("Examen clinique", "examen_clinique"),
        ("Proposition thérapeutique", "proposition_therapeutique"),
    ]:
        val = safe(report, key)
        if val:
            rows.append([Paragraph(f"<b>{label}</b>", normal_style),
                         Paragraph(str(val), normal_style)])

    # Antécédents
    rows.append([Paragraph("<b>Antécédents</b>", header_style), ""])
    antec = record.get("antecedents", {}) or {}
    for label, key in [("Médicaux", "medicaux"), ("Chirurgicaux", "chirurgicaux"),
                       ("Familiaux", "familiaux")]:
        items = antec.get(key, [])
        if items:
            rows.append([Paragraph(f"<b>{label}</b>", normal_style),
                         Paragraph(", ".join(items), normal_style)])

    # Traitements
    trts = record.get("traitements_habituels", []) or []
    if trts:
        rows.append([Paragraph("<b>Traitements habituels</b>", header_style), ""])
        for t in trts:
            name = t.get("nom_commercial", "") or ""
            pos = t.get("posologie", "") or ""
            rows.append([Paragraph(f"<b>{name}</b>", normal_style),
                         Paragraph(pos, normal_style)])

    # Conclusion
    conclusion = record.get("conclusion", {}) or {}
    rows.append([Paragraph("<b>Conclusion</b>", header_style), ""])
    for label, key in [("Diagnostic", "diagnostic"),
                       ("Proposition thérapeutique", "proposition_therapeutique"),
                       ("Prochaine consultation", "prochaine_consultation")]:
        val = safe(conclusion, key)
        if val:
            rows.append([Paragraph(f"<b>{label}</b>", normal_style),
                         Paragraph(str(val), normal_style)])

    # Ordonnance
    prescriptions = prescription.get("prescriptions", []) or []
    if prescriptions:
        rows.append([Paragraph("<b>Ordonnance</b>", header_style), ""])
        for p in prescriptions:
            name = p.get("nom_commercial", "") or p.get("dci", "")
            pos = p.get("posologie", {}) or {}
            dose = pos.get("dose", "") or ""
            freq = pos.get("frequence", "") or ""
            duree = p.get("duree", "") or ""
            line = f"{dose} {freq}".strip()
            if duree:
                line += f" — {duree}"
            rows.append([Paragraph(f"<b>{name}</b>", normal_style),
                         Paragraph(line, normal_style)])

    table = Table(rows, colWidths=[2*inch, 4.3*inch])
    style_cmds = [
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E6E0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAFAF8")]),
    ]
    for i, row in enumerate(rows):
        if row[1] == "":
            style_cmds.extend([
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#0D1B3E")),
                ("TEXTCOLOR", (0, i), (-1, i), colors.white),
                ("SPAN", (0, i), (-1, i)),
            ])
    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    doc.build(story)
    return buf.getvalue()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🎙️  Transcription",
    "🧠  Extraction",
    "📋  Rapport PDF",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Transcription
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### 1. Charger l'audio")
        st.caption("Formats acceptés : .m4a, .wav, .mp3, .flac")

        uploaded = st.file_uploader(
            "Déposez votre fichier audio ici",
            type=["m4a", "wav", "mp3", "flac", "ogg"],
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if uploaded:
            st.audio(uploaded)
            st.session_state.audio_filename = uploaded.name

            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### 2. Transcrire")
            st.caption("Modèle : faster-whisper large-v3 · Langue : français")

            if st.button("▶  Lancer la transcription", use_container_width=True):
                with st.spinner("Transcription en cours..."):
                    audio_bytes = uploaded.read()
                    result = transcribe_audio(audio_bytes, uploaded.name)

                if result and result[0]:
                    text, rtf, device, duration = result
                    st.session_state.transcript = text
                    st.session_state.hallucination_ok = None
                    st.success("Transcription terminée ✓")

                    # Metrics
                    st.markdown(f"""
                    <div class="metric-row">
                        <div class="metric-box">
                            <div class="value">{duration:.0f}s</div>
                            <div class="label">Durée audio</div>
                        </div>
                        <div class="metric-box">
                            <div class="value">{rtf:.2f}</div>
                            <div class="label">RTF</div>
                        </div>
                        <div class="metric-box">
                            <div class="value">{len(text.split())}</div>
                            <div class="label">Mots</div>
                        </div>
                    </div>
                    <p style="font-size:0.8rem;color:#94A3B8">Dispositif : {device}</p>
                    """, unsafe_allow_html=True)
                else:
                    st.error("La transcription a échoué.")

            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        if st.session_state.transcript:
            # ── Step 3: Hallucination check ───────────────────────────
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### 3. Vérification anti-hallucination")

            is_hallucinating, reason = detect_hallucination(st.session_state.transcript)
            st.session_state.hallucination_ok = not is_hallucinating

            if is_hallucinating:
                st.markdown(f'<div class="alert-error">⚠️ <b>Hallucination détectée</b><br>{reason}<br><br>La transcription n\'est pas fiable. Veuillez réessayer ou vérifier manuellement.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-ok">✓ <b>Aucune hallucination détectée</b><br>{reason}</div>', unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Step 4: LLM review ────────────────────────────────────
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### 4. Vérification médicale par l'IA")
            st.caption("Le LLM vérifie les noms de médicaments, termes anatomiques et dosages")

            if st.button("🔍  Vérifier avec Scaleway IA", use_container_width=True):
                with st.spinner("Vérification en cours..."):
                    review_result = call_llm(st.session_state.transcript, "review")

                if "error" in review_result:
                    st.error(f"Erreur : {review_result['error']}")
                else:
                    st.session_state.review = review_result
                    corrections = review_result.get("corrections", [])
                    alertes = review_result.get("alertes", [])

                    if not corrections and not alertes:
                        st.markdown('<div class="alert-ok">✓ <b>Transcription validée</b><br>' + review_result.get("resume", "") + '</div>', unsafe_allow_html=True)
                    else:
                        if corrections:
                            st.markdown(f'<div class="alert-warn">✏️ <b>{len(corrections)} correction(s) proposée(s)</b> — {review_result.get("resume", "")}</div>', unsafe_allow_html=True)
                            st.markdown("<br>", unsafe_allow_html=True)
                            for c in corrections:
                                badge_color = {"haute": "#065F46", "moyenne": "#92400E", "faible": "#6B7280"}.get(c.get("confiance", ""), "#6B7280")
                                st.markdown(f"""
                                <div style="display:flex;align-items:center;gap:0.8rem;padding:0.5rem 0;border-bottom:1px solid #F0EEE8">
                                    <span style="background:#FEF3C7;color:#92400E;padding:0.1rem 0.5rem;border-radius:4px;font-family:monospace;font-size:0.85rem;text-decoration:line-through">{c.get('original','')}</span>
                                    <span style="color:#028090">→</span>
                                    <span style="background:#ECFDF5;color:#065F46;padding:0.1rem 0.5rem;border-radius:4px;font-family:monospace;font-size:0.85rem;font-weight:600">{c.get('corrige','')}</span>
                                    <span style="font-size:0.75rem;color:{badge_color};margin-left:auto">{c.get('confiance','').upper()} · {c.get('type','')}</span>
                                </div>
                                <p style="font-size:0.8rem;color:#64748B;margin:0.2rem 0 0.5rem 0">{c.get('explication','')}</p>
                                """, unsafe_allow_html=True)

                        if alertes:
                            st.markdown(f'<div class="alert-warn">⚠️ <b>{len(alertes)} alerte(s)</b> à vérifier par le médecin</div>', unsafe_allow_html=True)
                            for a in alertes:
                                st.markdown(f"- **«{a.get('texte','')}»** — {a.get('raison','')}")

                        # Apply corrections button
                        corrected = review_result.get("transcription_corrigee", "")
                        if corrected and corrected != st.session_state.transcript:
                            if st.button("✅  Appliquer les corrections à la transcription"):
                                st.session_state.transcript = corrected
                                st.success("Corrections appliquées ✓")
                                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Step 5: Editable transcript ───────────────────────────
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### 5. Transcription finale")
            st.caption("Modifiez si nécessaire avant de passer à l'extraction")

            edited = st.text_area(
                "Transcription :",
                value=st.session_state.transcript,
                height=220,
                label_visibility="collapsed"
            )
            if edited != st.session_state.transcript:
                st.session_state.transcript = edited
                st.caption("✏️ Modifiée manuellement")

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:300px;color:#94A3B8;text-align:center">
                <div style="font-size:3rem">🎙️</div>
                <p>Chargez un fichier audio et lancez la transcription</p>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Extraction LLM
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    if not st.session_state.transcript:
        st.info("Complétez d'abord l'étape de transcription (onglet 1).")
    else:
        if st.session_state.hallucination_ok is False:
            st.markdown('<div class="alert-warn">⚠️ Une hallucination a été détectée dans la transcription. Vérifiez et corrigez le texte avant l\'extraction.</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 2], gap="large")

        with col_left:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### Extraction LLM")
            st.caption("Modèle : llama-3.3-70b-instruct · Scaleway Generative APIs")

            outputs_to_run = st.multiselect(
                "Documents à générer",
                options=["consultation_report", "medical_record", "prescription"],
                default=["consultation_report", "medical_record", "prescription"],
                format_func=lambda x: {
                    "consultation_report": "📝 Compte-rendu",
                    "medical_record": "🗂️ DPI",
                    "prescription": "💊 Ordonnance"
                }[x]
            )

            if st.button("🧠  Lancer l'extraction", use_container_width=True):
                if not outputs_to_run:
                    st.warning("Sélectionnez au moins un document.")
                else:
                    extraction = {}
                    progress = st.progress(0)
                    status = st.empty()

                    for i, output_type in enumerate(outputs_to_run):
                        labels = {
                            "consultation_report": "compte-rendu",
                            "medical_record": "DPI",
                            "prescription": "ordonnance"
                        }
                        status.caption(f"Extraction du {labels[output_type]}...")
                        extraction[output_type] = call_llm(st.session_state.transcript, output_type)
                        progress.progress((i + 1) / len(outputs_to_run))

                    st.session_state.extraction = extraction
                    status.empty()
                    progress.empty()

                    errors = [k for k, v in extraction.items() if "error" in v]
                    if errors:
                        st.error(f"Erreurs sur : {', '.join(errors)}")
                    else:
                        st.success("Extraction terminée ✓")

            st.markdown("</div>", unsafe_allow_html=True)

            # Download raw JSON
            if st.session_state.extraction:
                st.download_button(
                    "⬇  Télécharger JSON brut",
                    data=json.dumps(st.session_state.extraction, ensure_ascii=False, indent=2),
                    file_name=f"extraction_{Path(st.session_state.audio_filename or 'consultation').stem}.json",
                    mime="application/json",
                    use_container_width=True
                )

        with col_right:
            if st.session_state.extraction:
                icons = {
                    "consultation_report": "📝",
                    "medical_record": "🗂️",
                    "prescription": "💊"
                }
                labels = {
                    "consultation_report": "Compte-rendu",
                    "medical_record": "DPI — Dossier patient",
                    "prescription": "Ordonnance"
                }

                for key, data in st.session_state.extraction.items():
                    st.markdown(f"""
                    <div class="json-section">
                        <div class="json-section-header">
                            {icons.get(key, "📄")} {labels.get(key, key)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if "error" in data:
                        st.error(f"Erreur : {data['error']}")
                    else:
                        with st.expander("Voir le JSON", expanded=True):
                            st.json(data)
            else:
                st.markdown("""
                <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:300px;color:#94A3B8;text-align:center">
                    <div style="font-size:3rem">🧠</div>
                    <p>Lancez l'extraction pour voir les résultats ici</p>
                </div>
                """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — PDF
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.extraction:
        st.info("Complétez d'abord l'extraction LLM (onglet 2).")
    else:
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### Générer le rapport PDF")
            st.caption("Compte-rendu structuré prêt à être vérifié par le médecin")

            filename_stem = Path(st.session_state.audio_filename or "consultation").stem

            if st.button("📋  Générer le PDF", use_container_width=True):
                with st.spinner("Génération du PDF..."):
                    pdf_bytes = generate_pdf(st.session_state.extraction, filename_stem)

                if pdf_bytes:
                    st.session_state.pdf_bytes = pdf_bytes
                    st.success("PDF généré ✓")
                else:
                    st.error("Erreur de génération. `pip install reportlab`")

            if "pdf_bytes" in st.session_state and st.session_state.pdf_bytes:
                st.download_button(
                    "⬇  Télécharger le PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=f"rapport_{filename_stem}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### Aperçu du contenu")

            extraction = st.session_state.extraction
            report = extraction.get("consultation_report", {}) or {}
            record = extraction.get("medical_record", {}) or {}
            conclusion = (record.get("conclusion") or {})
            prescription = extraction.get("prescription", {}) or {}

            if report.get("motif_de_consultation"):
                st.markdown(f"**Motif :** {report['motif_de_consultation']}")

            if report.get("examen_clinique"):
                st.markdown(f"**Examen clinique :** {report['examen_clinique']}")

            if report.get("proposition_therapeutique"):
                st.markdown(f"**Proposition thérapeutique :** {report['proposition_therapeutique']}")

            if conclusion.get("diagnostic"):
                st.markdown(f"**Diagnostic :** {conclusion['diagnostic']}")

            if conclusion.get("prochaine_consultation"):
                st.markdown(f"**Prochaine consultation :** {conclusion['prochaine_consultation']}")

            prescriptions = prescription.get("prescriptions", []) or []
            if prescriptions:
                st.markdown("**Ordonnance :**")
                for p in prescriptions:
                    name = p.get("nom_commercial") or p.get("dci") or "—"
                    pos = p.get("posologie", {}) or {}
                    st.markdown(f"- **{name}** — {pos.get('dose','')} {pos.get('frequence','')}")

            st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="border:none;border-top:1px solid #E8E6E0;margin-top:3rem">
<p style="text-align:center;color:#94A3B8;font-size:0.8rem">
Napoleon · Pipeline médical IA · Données traitées localement · Confidentiel
</p>
""", unsafe_allow_html=True)