from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import json
import sys
from pathlib import Path


def load_json_consultation(file_path):
    """Load consultation data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_get(obj, key, default=''):
    """Safely get value from dictionary."""
    if obj is None:
        return default
    return obj.get(key, default) or default


def create_consultation_pdf(json_file, output_pdf=None):
    """
    Convert a consultation JSON file to a PDF with professional table layout.
    
    Args:
        json_file: Path to the extraction_consultation JSON file
        output_pdf: Output PDF file path (defaults to replacing .json with .pdf)
    """
    
    # Determine output file
    if output_pdf is None:
        output_pdf = Path(json_file).stem + ".pdf"
    
    # Load data
    data = load_json_consultation(json_file)
    
    # Create PDF
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.black,
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    
    # Build main content table
    content_data = []
    
    # Extract data
    report = data.get('consultation_report', {})
    record = data.get('medical_record', {})
    
    # Motif de consultation
    content_data.append([Paragraph("<b>Motif de consultation</b>", header_style)])
    content_data.append([Paragraph(safe_get(report, 'motif_de_consultation'), normal_style)])
    
    # Historique médical section
    content_data.append([Paragraph("<b>Historique médical</b>", header_style)])
    
    # Antécédents subsection
    content_data.append([Paragraph("<b>Antécédents</b>", header_style)])
    
    antecedents = record.get('antecedents', {})
    
    medicaux = antecedents.get('medicaux', [])
    if medicaux:
        med_text = ', '.join(medicaux) if isinstance(medicaux, list) else str(medicaux)
        content_data.append([
            Paragraph("<b>Antécédents médicaux</b>", normal_style),
            Paragraph(med_text, normal_style)
        ])
    
    chirurgicaux = antecedents.get('chirurgicaux', [])
    if chirurgicaux:
        chir_text = ', '.join(chirurgicaux) if isinstance(chirurgicaux, list) else str(chirurgicaux)
        content_data.append([
            Paragraph("<b>Antécédents chirurgicaux</b>", normal_style),
            Paragraph(chir_text, normal_style)
        ])
    
    familiaux = antecedents.get('familiaux', [])
    if familiaux:
        fam_text = ', '.join(familiaux) if isinstance(familiaux, list) else str(familiaux)
        content_data.append([
            Paragraph("<b>Antécédents familiaux</b>", normal_style),
            Paragraph(fam_text, normal_style)
        ])
    
    # Mode de vie
    mode_de_vie = record.get('mode_de_vie', {})
    if mode_de_vie:
        mode_text_parts = []
        if mode_de_vie.get('tabac'):
            mode_text_parts.append(mode_de_vie['tabac'])
        if mode_de_vie.get('alcool'):
            mode_text_parts.append(mode_de_vie['alcool'])
        if mode_de_vie.get('activite_physique'):
            mode_text_parts.append(mode_de_vie['activite_physique'])
        if mode_de_vie.get('autre'):
            mode_text_parts.append(mode_de_vie['autre'])
        
        if mode_text_parts:
            mode_text = ' ; '.join(mode_text_parts)
            content_data.append([
                Paragraph("<b>Mode de vie</b>", normal_style),
                Paragraph(mode_text, normal_style)
            ])
    
    # Traitements habituels
    traitements = record.get('traitements_habituels', [])
    if traitements:
        trait_text_parts = []
        for trait in traitements:
            nom = trait.get('nom_commercial', '')
            mol = trait.get('molecule', '')
            pos = trait.get('posologie', '')
            
            if nom:
                if pos:
                    trait_text_parts.append(f"{nom} {pos}")
                else:
                    trait_text_parts.append(nom)
        
        if trait_text_parts:
            trait_text = ' ; '.join(trait_text_parts)
            content_data.append([
                Paragraph("<b>Traitements habituels</b>", normal_style),
                Paragraph(trait_text, normal_style)
            ])
    
    # Allergies
    allergies = record.get('allergies', [])
    if allergies and allergies != []:
        allergy_text = ', '.join(allergies) if isinstance(allergies, list) else str(allergies)
    else:
        allergy_text = safe_get(record, 'allergies_text', 'Aucune allergie connue')
    
    if allergy_text:
        content_data.append([
            Paragraph("<b>Allergies</b>", normal_style),
            Paragraph(allergy_text, normal_style)
        ])
    
    # Interrogatoire section
    content_data.append([Paragraph("<b>Interrogatoire</b>", header_style)])
    
    interrogatoire = record.get('interrogatoire', {})
    
    if interrogatoire.get('symptomes_generaux'):
        content_data.append([
            Paragraph("<b>Symptômes généraux</b>", normal_style),
            Paragraph(interrogatoire['symptomes_generaux'], normal_style)
        ])
    
    if interrogatoire.get('symptomes_par_organe'):
        content_data.append([
            Paragraph(f"<b>{interrogatoire.get('organe_specifique', 'Symptômes spécifiques')}</b>", normal_style),
            Paragraph(interrogatoire['symptomes_par_organe'], normal_style)
        ])
    
    # Additional interrogatoire details from report
    if report.get('interrogatoire'):
        content_data.append([
            Paragraph("<b>Détails additionnels</b>", normal_style),
            Paragraph(report['interrogatoire'], normal_style)
        ])
    
    # Examen clinique section
    content_data.append([Paragraph("<b>Examen clinique</b>", header_style)])
    
    examen = record.get('examen_clinique', {})
    
    if examen.get('examen_specifique'):
        content_data.append([
            Paragraph("<b>Selon spécialité (ORL)</b>", normal_style),
            Paragraph(examen['examen_specifique'], normal_style)
        ])
    
    if report.get('examen_clinique'):
        content_data.append([
            Paragraph("<b>Observations</b>", normal_style),
            Paragraph(report['examen_clinique'], normal_style)
        ])
    
    # Conclusion section
    conclusion = record.get('conclusion', {})
    if conclusion:
        content_data.append([Paragraph("<b>Conclusion</b>", header_style)])
        
        if conclusion.get('diagnostic'):
            content_data.append([
                Paragraph("<b>Diagnostic</b>", normal_style),
                Paragraph(conclusion['diagnostic'], normal_style)
            ])
        
        if conclusion.get('proposition_therapeutique'):
            content_data.append([
                Paragraph("<b>Proposition thérapeutique</b>", normal_style),
                Paragraph(conclusion['proposition_therapeutique'], normal_style)
            ])
        
        if report.get('proposition_therapeutique'):
            content_data.append([
                Paragraph("<b>Traitement recommandé</b>", normal_style),
                Paragraph(report['proposition_therapeutique'], normal_style)
            ])
        
        if conclusion.get('examens_complementaires'):
            examens_list = conclusion['examens_complementaires']
            if examens_list:
                examens_text = ', '.join(examens_list) if isinstance(examens_list, list) else str(examens_list)
                content_data.append([
                    Paragraph("<b>Examens complémentaires</b>", normal_style),
                    Paragraph(examens_text, normal_style)
                ])
        
        if conclusion.get('orientation'):
            content_data.append([
                Paragraph("<b>Orientation</b>", normal_style),
                Paragraph(conclusion['orientation'], normal_style)
            ])
    
    # Prochaine consultation
    if conclusion.get('prochaine_consultation'):
        content_data.append([Paragraph("<b>Prochaine consultation</b>", header_style)])
        content_data.append([Paragraph(conclusion['prochaine_consultation'], normal_style)])
    
    # Create table data with proper structure
    table_data = []
    for row in content_data:
        if len(row) == 1:
            # Full-width rows (headers)
            table_data.append([row[0], ''])
        else:
            # Two-column rows
            table_data.append(row)
    
    # Create main table
    main_table = Table(table_data, colWidths=[2*inch, 4*inch])
    
    # Build style commands
    style_commands = [
        # General styling
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
    ]
    
    # Apply header styling to section headers
    for i, row in enumerate(content_data):
        if len(row) == 1:
            # This is a header row
            style_commands.extend([
                ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#808080')),
                ('TEXTCOLOR', (0, i), (-1, i), colors.black),
                ('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'),
                ('FONTSIZE', (0, i), (-1, i), 11),
                ('SPAN', (0, i), (-1, i)),
            ])
    
    main_table.setStyle(TableStyle(style_commands))
    story.append(main_table)
    
    # Build PDF
    doc.build(story)
    print(f"✓ PDF créé avec succès: {output_pdf}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_pdf.py <consultation_json_file> [output_pdf_file]")
        print("Example: python json_to_pdf.py results/extraction_consultation_1001.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        create_consultation_pdf(json_file, output_pdf)
    except FileNotFoundError:
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
