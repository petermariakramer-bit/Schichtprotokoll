import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import html
from io import BytesIO

# --- OPTIONALE IMPORTS ---
try:
    from staticmap import StaticMap, CircleMarker as StaticCircleMarker
    HAS_STATICMAP = True
except ImportError:
    HAS_STATICMAP = False

# --- REPORTLAB IMPORTS ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

# --- KONFIGURATION ---
st.set_page_config(page_title="Profi Bohrprotokoll", layout="wide")

if 'lat' not in st.session_state: st.session_state.lat = 52.42751
if 'lon' not in st.session_state: st.session_state.lon = 13.1905

st.title("🕳️ Bohrprotokoll & Schichtenverzeichnis")

# ==============================================================================
# 1. HELPER: KARTEN & SVG
# ==============================================================================
def get_static_map_image(lat, lon, zoom=15):
    if not HAS_STATICMAP: return None
    try:
        m = StaticMap(width=800, height=400, url_template='http://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
        marker = StaticCircleMarker((lon, lat), 'red', 18)
        m.add_marker(marker)
        image = m.render(zoom=zoom)
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer
    except: return None

def generate_svg_string(df_geo, df_rohr, df_ring, meta):
    # (SVG Code bleibt gleich wie vorher - Kurzfassung)
    scale_y = 15
    width = 700
    max_depth = 48
    if not df_geo.empty: max_depth = max(max_depth, df_geo['Bis_m'].max())
    total_height = 50 + (max_depth * scale_y) + 50 # Header im SVG selbst reduziert, da jetzt im PDF Header
    
    svg = f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
    # ... Patterns ...
    svg += '''<defs>
    <pattern id="pat-Sand" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fffacd"/><circle cx="2" cy="2" r="1" fill="gold"/><circle cx="7" cy="7" r="1" fill="gold"/></pattern>
    <pattern id="pat-Mudde" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#ddd"/><path d="M0,5 h10" stroke="black" stroke-width="2"/></pattern>
    <pattern id="pat-Mergel" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#eee"/><path d="M0,0 l10,10 m0,-10 l-10,10" stroke="#555"/></pattern>
    <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#5c4033"/></pattern>
    <pattern id="pat-Tonsperre" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="brown"/><path d="M0,10 l10,-10" stroke="white"/></pattern>
    <pattern id="pat-Filterkies" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="white"/><circle cx="3" cy="3" r="1.5" fill="orange"/></pattern>
    <pattern id="pat-Filterrohr" width="10" height="5" patternUnits="userSpaceOnUse"><rect width="10" height="5" fill="white" stroke="black"/><line x1="2" y1="2" x2="8" y2="2" stroke="black"/></pattern>
    </defs>'''
    
    start_y = 20 # Weniger Platz oben, da Header jetzt im PDF ist
    col_geo_x = 80
    col_geo_w = 100
    col_tech_x = 350
    
    # Skala
    svg += f'<line x1="{col_geo_x}" y1="{start_y}" x2="{col_geo_x}" y2="{start_y + max_depth*scale_y}" stroke="black"/>'
    for i in range(int(max_depth)+1):
        y = start_y + i*scale_y
        svg += f'<line x1="{col_geo_x}" y1="{y}" x2="{col_geo_x-5}" y2="{y}" stroke="black"/>'
        if i % 1 == 0: svg += f'<text x="{col_geo_x-10}" y="{y+3}" text-anchor="end" font-family="Arial" font-size="10">{i}</text>'

    last_d = 0
    for _, r in df_geo.iterrows():
        h = (r['Bis_m'] - last_d) * scale_y
        pat = "pat-Sand"
        if "Mudde" in r['Benennung']: pat = "pat-Mudde"
        if "Mergel" in r['Benennung']: pat = "pat-Mergel"
        if "Mutterboden" in r['Benennung']: pat = "pat-Mutterboden"
        svg += f'<rect x="{col_geo_x}" y="{start_y+last_d*scale_y}" width="{col_geo_w}" height="{h}" fill="url(#{pat})" stroke="black"/>'
        svg += f'<text x="{col_geo_x+col_geo_w+5}" y="{start_y+last_d*scale_y + h/2}" font-family="Arial" font-size="10">{r["Benennung"]}</text>'
        last_d = r['Bis_m']
        
    for _, r in df_ring.iterrows():
        y = start_y + r['Von']*scale_y
        h = (r['Bis'] - r['Von']) * scale_y
        pat = "pat-Filterkies"
        if "Ton" in r['Mat']: pat = "pat-Tonsperre"
        svg += f'<rect x="{col_tech_x-40}" y="{y}" width="80" height="{h}" fill="url(#{pat})" stroke="none"/>'
        
    for _, r in df_rohr.iterrows():
        y = start_y + r['Von']*scale_y
        h = (r['Bis'] - r['Von']) * scale_y
        fill = "white"
        if "Filter" in r['Typ']: fill = "url(#pat-Filterrohr)"
        if "Sumpf" in r['Typ']: fill = "#ccc"
        svg += f'<rect x="{col_tech_x-20}" y="{y}" width="40" height="{h}" fill="{fill}" stroke="black" stroke-width="2"/>'
        
    svg += '</svg>'
    return svg

# ==============================================================================
# 2. PDF HEADER FUNKTION (DAS IST NEU!)
# ==============================================================================

def draw_header_on_page(canvas, doc):
    """
    Zeichnet den festen Header auf jede Seite.
    Layout basiert auf 'Schichtenverzeichnis.pdf'.
    """
    canvas.saveState()
    
    # Metadaten aus dem Doc-Objekt holen (dort speichern wir sie gleich)
    meta = doc.meta_data 
    
    # Abmessungen Header
    page_width, page_height = A4
    margin_left = 2*cm
    margin_right = 2*cm
    header_top = page_height - 1*cm
    header_bottom = page_height - 4.5*cm # Der Header ist ca 3.5cm hoch
    width = page_width - margin_left - margin_right
    
    # 1. Rahmen um den Header
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1)
    # Rechteck für den ganzen Header
    canvas.rect(margin_left, header_bottom, width, header_top - header_bottom)
    
    # 2. Vertikale Trennlinien
    # Linie 1: Trennt Logo (links) von Titel (mitte)
    canvas.line(margin_left + 4*cm, header_bottom, margin_left + 4*cm, header_top)
    # Linie 2: Trennt Titel (mitte) von Aktenzeichen (rechts)
    canvas.line(page_width - margin_right - 5*cm, header_bottom, page_width - margin_right - 5*cm, header_top)
    
    # 3. Horizontale Trennlinie (für untere Zeile: Ort, Datum etc.)
    row_line_y = header_bottom + 1.2*cm
    canvas.line(margin_left, row_line_y, page_width - margin_right, row_line_y)
    
    # --- INHALT ---
    
    # A) LOGO BEREICH (Oben Links)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.setFillColor(colors.green) # Bohr2000 ist grün im Original
    canvas.drawString(margin_left + 0.2*cm, header_top - 0.6*cm, "Bohr2000")
    
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(colors.black)
    canvas.drawString(margin_left + 0.2*cm, header_top - 1.2*cm, meta['firma'])
    
    # B) TITEL BEREICH (Oben Mitte)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(page_width/2, header_top - 0.6*cm, "Schichtenverzeichnis / Bohrprofil")
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(page_width/2, header_top - 1.0*cm, "nach DIN 4022 / DIN 4023")
    canvas.drawCentredString(page_width/2, header_top - 1.4*cm, "für Bohrungen ohne durchgehende Kerngewinnung")
    
    # C) RECHTS BEREICH (Aktenzeichen)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(page_width - margin_right - 4.8*cm, header_top - 0.6*cm, "Aktenzeichen:")
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(page_width - margin_right - 4.8*cm, header_top - 1.0*cm, meta['aktenzeichen'])
    
    canvas.setFont("Helvetica", 9)
    canvas.drawString(page_width - margin_right - 4.8*cm, header_top - 1.5*cm, "Archiv-Nr:")
    
    # D) UNTERE ZEILE (Projektinfos)
    # Links: Ort & Bohrung
    text_y_row = row_line_y - 0.4*cm
    canvas.setFont("Helvetica", 9)
    canvas.drawString(margin_left + 0.2*cm, text_y_row, f"Ort: {meta['ort']}")
    canvas.drawString(margin_left + 0.2*cm, text_y_row - 0.4*cm, f"Bohrung: {meta['projekt']}")
    
    # Rechts: Datum
    # Wir brauchen noch eine kleine vertikale Linie unten rechts für das Datum
    canvas.line(page_width - margin_right - 5*cm, header_bottom, page_width - margin_right - 5*cm, row_line_y)
    
    canvas.drawString(page_width - margin_right - 4.8*cm, text_y_row, "Datum:")
    canvas.drawString(page_width - margin_right - 4.8*cm, text_y_row - 0.4*cm, meta['datum'])

    # E) Seitenzahl (Unten im Footer oder oben im Header)
    # Im Original steht "Anlage 1, Blatt X". Wir setzen es rechts oben in die Ecke der unteren Zeile
    page_num = doc.page
    canvas.drawRightString(page_width - margin_right - 5.2*cm, text_y_row - 0.2*cm, f"Blatt {page_num}")

    canvas.restoreState()

# ==============================================================================
# 3. PDF BUILDER
# ==============================================================================

def create_multipage_pdf_with_header(meta, df_geo, df_rohr, df_ring, svg_bytes, map_image_buffer):
    buffer = BytesIO()
    
    # WICHTIG: topMargin muss groß genug sein (4.5cm), damit der Header Platz hat!
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=2*cm, leftMargin=2*cm, 
                            topMargin=5*cm, bottomMargin=2*cm)
    
    # Metadaten an das Doc hängen, damit die Header-Funktion sie lesen kann
    doc.meta_data = meta
    
    story = []
    styles = getSampleStyleSheet()
    style_h2 = styles['Heading2']
    style_norm = styles['Normal']
    
    # --- SEITE 1: STAMMDATEN & KARTE ---
    # Kein eigener Header im Story-Flow mehr nötig, da draw_header_on_page das macht!
    
    story.append(Paragraph("Stammdaten Übersicht", style_h2))
    
    data_stamm = [
        ["Auftraggeber:", meta['auftraggeber']],
        ["Bohrverfahren:", meta['verfahren']],
        ["Endteufe:", f"{meta['teufe']} m"],
        ["Ansatzpunkt:", f"{meta['ansatz']} m u. GOK"],
        ["Grundwasser:", f"{meta['ws_ruhe']} m u. GOK"]
    ]
    t_stamm = Table(data_stamm, colWidths=[4*cm, 10*cm])
    t_stamm.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_stamm)
    story.append(Spacer(1, 1*cm))
    
    story.append(Paragraph("Lageplan", style_h2))
    if map_image_buffer:
        img = RLImage(map_image_buffer)
        img.drawHeight = 8*cm
        img.drawWidth = 14*cm
        story.append(img)
    else:
        story.append(Paragraph("(Keine Karte verfügbar)", style_norm))
        
    story.append(PageBreak())
    
    # --- SEITE 2: SCHICHTENVERZEICHNIS ---
    # Header erscheint hier automatisch
    table_headers = ["Tiefe bis", "Bodenart", "Zusatz", "Farbe", "Kalk", "Gruppe", "Bemerkung"]
    table_data = [table_headers]
    for _, row in df_geo.iterrows():
        # Zeilenumbruch mit Paragraph
        table_data.append([
            f"{row['Bis_m']:.2f}",
            Paragraph(str(row['Benennung']), style_norm),
            Paragraph(str(row['Zusatz']), style_norm),
            row['Farbe'],
            row['Kalk'],
            row['Gruppe'],
            Paragraph(str(row['Bemerkung']), style_norm)
        ])
    
    t_geo = Table(table_data, colWidths=[2*cm, 2.5*cm, 3.5*cm, 2*cm, 1*cm, 2*cm, 3*cm], repeatRows=1)
    t_geo.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_geo)
    story.append(PageBreak())
    
    # --- SEITE 3: GRAFIK ---
    # Auch hier erscheint der Header automatisch
    if svg_bytes:
        try:
            drawing = svg2rlg(BytesIO(svg_bytes.encode('utf-8')))
            # Skalieren auf Seitenbreite
            avail_width = 460
            factor = avail_width / drawing.width
            drawing.width = drawing.width * factor
            drawing.height = drawing.height * factor
            drawing.scale(factor, factor)
            story.append(drawing)
        except:
            story.append(Paragraph("Fehler beim Grafik-Import", style_norm))

    # PDF bauen mit Header-Callback
    doc.build(story, onFirstPage=draw_header_on_page, onLaterPages=draw_header_on_page)
    return buffer.getvalue()


# ==============================================================================
# 4. GUI & EINGABE
# ==============================================================================

with st.expander("1. Kopfblatt & Standort", expanded=True):
    col_map, col_data = st.columns([1, 1])
    with col_data:
        st.subheader("Stammdaten")
        projekt = st.text_input("Projekt / Bohrung", value="Notwasserbrunnen ZE079-905")
        ort = st.text_input("Ort / Adresse", value="Wiesenschlag ggü 4, 14129 Berlin")
        if st.button("📍 Adresse suchen"):
            try:
                loc = Nominatim(user_agent="app").geocode(ort)
                if loc:
                    st.session_state.lat, st.session_state.lon = loc.latitude, loc.longitude
                    st.success("Gefunden!")
            except: pass

        c1, c2 = st.columns(2)
        auftraggeber = c1.text_input("Auftraggeber", value="Berliner Wasserbetriebe")
        bohrfirma = c2.text_input("Bohrunternehmer", value="Ackermann KG")
        
        c3, c4 = st.columns(2)
        datum_str = c3.text_input("Datum", value="06.10.25")
        aktenzeichen = c4.text_input("Aktenzeichen", value="V26645")
        
        c5, c6 = st.columns(2)
        ansatzpunkt = c5.number_input("Ansatzpunkt", value=0.0)
        endteufe = c6.number_input("Endteufe", value=45.0)
        bohrverfahren = st.text_input("Verfahren", value="Spülbohren, Ø 330mm")

    with col_map:
        m = folium.Map([st.session_state.lat, st.session_state.lon], zoom_start=16)
        folium.CircleMarker([st.session_state.lat, st.session_state.lon], radius=8, color="red", fill=True, fill_color="red").add_to(m)
        st_folium(m, height=350)

with st.expander("2. Schichtenverzeichnis", expanded=False):
    default_geo = [
        {"Bis_m": 14.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "braun", "Kalk": "0", "Gruppe": "SE", "Bemerkung": "schwer zu bohren"},
        {"Bis_m": 29.00, "Benennung": "Mudde", "Zusatz": "organisch", "Farbe": "dunkelbraun", "Kalk": "+", "Gruppe": "SU*-TL", "Bemerkung": ""},
        {"Bis_m": 46.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "grau", "Kalk": "+", "Gruppe": "SE", "Bemerkung": ""},
    ]
    df_geo = st.data_editor(pd.DataFrame(default_geo), num_rows="dynamic", use_container_width=True)

with st.expander("3. Ausbau", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        default_rohr = [{"Von": 0.0, "Bis": 40.0, "Typ": "Vollrohr", "DN": 150}, {"Von": 40.0, "Bis": 44.0, "Typ": "Filterrohr", "DN": 150}]
        df_rohr = st.data_editor(pd.DataFrame(default_rohr), num_rows="dynamic", key="rohr")
        ws_ruhe = st.number_input("Ruhewasser", value=14.70)
    with c2:
        default_ring = [{"Von": 0.0, "Bis": 14.0, "Mat": "Filterkies"}, {"Von": 14.0, "Bis": 29.0, "Mat": "Tonsperre"}]
        df_ring = st.data_editor(pd.DataFrame(default_ring), num_rows="dynamic", key="ring")

# --- OUTPUT ---
st.divider()
meta_data = {
    "projekt": projekt, "ort": ort, "firma": bohrfirma, "auftraggeber": auftraggeber,
    "datum": datum_str, "aktenzeichen": aktenzeichen, 
    "verfahren": bohrverfahren, "ansatz": ansatzpunkt, "teufe": endteufe, "ws_ruhe": ws_ruhe
}

if st.button("📄 PDF mit Kopfzeile erstellen"):
    svg_str = generate_svg_string(df_geo, df_rohr, df_ring, meta_data)
    map_buf = get_static_map_image(st.session_state.lat, st.session_state.lon)
    pdf = create_multipage_pdf_with_header(meta_data, df_geo, df_rohr, df_ring, svg_str, map_buf)
    st.download_button("📥 PDF Download", pdf, "Bohrprotokoll.pdf", "application/pdf")
