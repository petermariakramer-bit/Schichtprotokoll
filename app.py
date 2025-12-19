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
from reportlab.lib.utils import ImageReader
from svglib.svglib import svg2rlg

# --- KONFIGURATION ---
st.set_page_config(page_title="Profi Bohrprotokoll", layout="wide")

if 'lat' not in st.session_state: st.session_state.lat = 52.42751
if 'lon' not in st.session_state: st.session_state.lon = 13.1905

st.title("🕳️ Bohrprotokoll & Schichtenverzeichnis")

# ==============================================================================
# 1. HELPER
# ==============================================================================
def get_static_map_image(lat, lon, zoom=15):
    if not HAS_STATICMAP: return None
    try:
        m = StaticMap(width=1000, height=500, url_template='http://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
        marker = StaticCircleMarker((lon, lat), 'red', 18)
        m.add_marker(marker)
        image = m.render(zoom=zoom)
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer
    except: return None

def generate_svg_string(df_geo, df_rohr, df_ring, meta):
    scale_y = 15
    width = 700
    max_depth = 48
    if not df_geo.empty: max_depth = max(max_depth, df_geo['Bis_m'].max())
    
    total_height = (max_depth * scale_y) + 50
    
    svg = f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
    svg += '''<defs>
    <pattern id="pat-Sand" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fffacd"/><circle cx="2" cy="2" r="1" fill="gold"/><circle cx="7" cy="7" r="1" fill="gold"/></pattern>
    <pattern id="pat-Mudde" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#ddd"/><path d="M0,5 h10" stroke="black" stroke-width="2"/></pattern>
    <pattern id="pat-Mergel" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#eee"/><path d="M0,0 l10,10 m0,-10 l-10,10" stroke="#555"/></pattern>
    <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#5c4033"/></pattern>
    <pattern id="pat-Tonsperre" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="brown"/><path d="M0,10 l10,-10" stroke="white"/></pattern>
    <pattern id="pat-Filterkies" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="white"/><circle cx="3" cy="3" r="1.5" fill="orange"/></pattern>
    <pattern id="pat-Filterrohr" width="10" height="5" patternUnits="userSpaceOnUse"><rect width="10" height="5" fill="white" stroke="black"/><line x1="2" y1="2" x2="8" y2="2" stroke="black"/></pattern>
    </defs>'''
    
    start_y = 10 
    col_geo_x = 80
    col_geo_w = 100
    col_tech_x = 350
    
    svg += f'<line x1="{col_geo_x}" y1="{start_y}" x2="{col_geo_x}" y2="{start_y + max_depth*scale_y}" stroke="black"/>'
    for i in range(int(max_depth)+1):
        y = start_y + i*scale_y
        svg += f'<line x1="{col_geo_x}" y1="{y}" x2="{col_geo_x-5}" y2="{y}" stroke="black"/>'
        if i % 1 == 0: svg += f'<text x="{col_geo_x-10}" y="{y+3}" text-anchor="end" font-family="Arial" font-size="10">{i}</text>'

    last_d = 0
    for _, r in df_geo.iterrows():
        h = (r['Bis_m'] - last_d) * scale_y
        
        # Muster Auswahl
        boden = str(r.get('f', '')).lower() + str(r.get('a', '')).lower()
        pat = "pat-Sand"
        if "mudde" in boden: pat = "pat-Mudde"
        if "mergel" in boden: pat = "pat-Mergel"
        if "mutterboden" in boden: pat = "pat-Mutterboden"
        
        svg += f'<rect x="{col_geo_x}" y="{start_y+last_d*scale_y}" width="{col_geo_w}" height="{h}" fill="url(#{pat})" stroke="black"/>'
        label = r.get('f', '')
        svg += f'<text x="{col_geo_x+col_geo_w+5}" y="{start_y+last_d*scale_y + h/2}" font-family="Arial" font-size="10">{label}</text>'
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
# 2. PDF HEADER
# ==============================================================================
def draw_header_on_page(canvas, doc):
    canvas.saveState()
    meta = doc.meta_data 
    page_width, page_height = A4
    margin_left = 2*cm
    margin_right = 2*cm
    box_w_firma = 3.5 * cm      
    box_w_akten = 4.0 * cm      
    header_top = page_height - 1*cm
    header_bottom = page_height - 4.5*cm 
    row_line_y = header_bottom + 1.2*cm
    x_line_1 = margin_left + box_w_firma
    x_line_2 = page_width - margin_right - box_w_akten
    
    # GRAU HINTERGRUND
    canvas.setFillColor(colors.whitesmoke)
    canvas.rect(margin_left, row_line_y, box_w_firma, header_top - row_line_y, fill=1, stroke=0)
    
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1)
    canvas.rect(margin_left, header_bottom, page_width - margin_left - margin_right, header_top - header_bottom, fill=0, stroke=1)
    canvas.line(margin_left, row_line_y, page_width - margin_right, row_line_y) 
    canvas.line(x_line_1, row_line_y, x_line_1, header_top) 
    canvas.line(x_line_2, header_bottom, x_line_2, header_top) 
    
    # LOGO
    if meta.get('logo_bytes'):
        try:
            logo_data = ImageReader(BytesIO(meta['logo_bytes']))
            avail_w = box_w_firma - 0.4*cm
            avail_h = (header_top - row_line_y) - 0.4*cm 
            iw, ih = logo_data.getSize()
            aspect = ih / float(iw)
            if aspect > avail_h / avail_w:
                draw_h = avail_h
                draw_w = draw_h / aspect
            else:
                draw_w = avail_w
                draw_h = draw_w * aspect
            x_img = margin_left + 0.2*cm + (avail_w - draw_w)/2
            y_img = row_line_y + 0.2*cm + (avail_h - draw_h)/2
            canvas.drawImage(logo_data, x_img, y_img, width=draw_w, height=draw_h, mask='auto')
        except: pass
    else:
        canvas.setFont("Helvetica-Bold", 14)
        canvas.setFillColor(colors.green)
        canvas.drawString(margin_left + 0.2*cm, header_top - 0.6*cm, "Bohr2000")
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.black)
        canvas.drawString(margin_left + 0.2*cm, header_top - 1.2*cm, meta['firma'])
    
    # TEXTE
    center_x = x_line_1 + (x_line_2 - x_line_1) / 2
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(center_x, header_top - 0.6*cm, "Schichtenverzeichnis / Bohrprofil")
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(center_x, header_top - 1.0*cm, "nach DIN 4022 / DIN 4023")
    canvas.drawCentredString(center_x, header_top - 1.4*cm, "für Bohrungen ohne durchgehende Kerngewinnung")
    
    text_x_right = x_line_2 + 0.2*cm
    canvas.setFont("Helvetica", 9)
    canvas.drawString(text_x_right, header_top - 0.6*cm, "Aktenzeichen:")
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(text_x_right, header_top - 1.0*cm, meta['aktenzeichen'])
    canvas.setFont("Helvetica", 9)
    canvas.drawString(text_x_right, header_top - 1.5*cm, "Archiv-Nr:")
    
    text_y_row = row_line_y - 0.4*cm
    canvas.setFont("Helvetica", 9)
    canvas.drawString(margin_left + 0.2*cm, text_y_row, f"Ort: {meta['ort']}")
    canvas.drawString(margin_left + 0.2*cm, text_y_row - 0.4*cm, f"Bohrung: {meta['projekt']}")
    
    canvas.line(x_line_2, header_bottom, x_line_2, row_line_y) 
    canvas.drawString(text_x_right, text_y_row, "Datum:")
    canvas.drawString(text_x_right, text_y_row - 0.4*cm, meta['datum'])
    
    page_num = doc.page
    canvas.drawRightString(page_width - margin_right - 0.2*cm, text_y_row, f"Blatt {page_num}")
    canvas.restoreState()

# ==============================================================================
# 3. PDF BUILDER
# ==============================================================================

def create_multipage_pdf_with_header(meta, df_geo, df_rohr, df_ring, svg_bytes, map_image_buffer):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=2*cm, leftMargin=2*cm, 
                            topMargin=5*cm, bottomMargin=2*cm)
    doc.meta_data = meta
    
    story = []
    styles = getSampleStyleSheet()
    
    style_tab_norm = ParagraphStyle('TabNorm', parent=styles['Normal'], fontSize=8, leading=10)
    style_tab_bold = ParagraphStyle('TabBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)
    
    # Sehr kleine Schrift für die dichte Schichten-Tabelle
    style_geo_norm = ParagraphStyle('GeoNorm', parent=styles['Normal'], fontSize=7, leading=8)
    style_geo_header = ParagraphStyle('GeoHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=8, alignment=1)
    
    page_width, _ = A4
    available_width = page_width - 4*cm
    col1_width = 5*cm
    col2_width = available_width - col1_width
    
    # --- SEITE 1 ---
    data_block1 = [
        [Paragraph("Bohrung:", style_tab_bold), Paragraph(meta['projekt'], style_tab_norm)],
        [Paragraph("Ort:", style_tab_bold), Paragraph(meta['ort'], style_tab_norm)],
        [Paragraph("Kreis:", style_tab_bold), Paragraph(meta['kreis'], style_tab_norm)],
        [Paragraph("Zweck der Bohrung:", style_tab_bold), Paragraph(meta['zweck'], style_tab_norm)],
        [Paragraph("Art der Bohrung:", style_tab_bold), Paragraph(meta['art_bohrung'], style_tab_norm)],
        [Paragraph("Höhe des Ansatzpunktes:", style_tab_bold), Paragraph(f"{meta['ansatz']} m u. GOK", style_tab_norm)]
    ]
    t1 = Table(data_block1, colWidths=[col1_width, col2_width])
    t1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t1)
    story.append(Spacer(1, 0.5*cm))
    
    data_block2 = [
        [Paragraph("Auftraggeber:", style_tab_bold), Paragraph(meta['auftraggeber'], style_tab_norm)],
        [Paragraph("Objekt:", style_tab_bold), Paragraph(meta['objekt'], style_tab_norm)],
        [Paragraph("Bohrunternehmer:", style_tab_bold), Paragraph(meta['firma'], style_tab_norm)],
        [Paragraph("Geräteführer:", style_tab_bold), Paragraph(meta['geraetefuehrer'], style_tab_norm)],
        [Paragraph("Gebohrt:", style_tab_bold), Paragraph(meta['datum'], style_tab_norm)],
        [Paragraph("Bohrlochdurchmesser:", style_tab_bold), Paragraph(f"bis {meta['teufe']}m: {meta['durchmesser']}mm", style_tab_norm)],
        [Paragraph("Bohrverfahren:", style_tab_bold), Paragraph(f"bis {meta['teufe']}m: {meta['verfahren']}", style_tab_norm)],
        [Paragraph("Gitterwerte:", style_tab_bold), Paragraph(f"Rechts: {meta['rechtswert']} | Hoch: {meta['hochwert']}", style_tab_norm)]
    ]
    t2 = Table(data_block2, colWidths=[col1_width, col2_width])
    t2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.5*cm))
    
    if map_image_buffer:
        img = RLImage(map_image_buffer)
        img_width = available_width
        aspect = img.imageHeight / float(img.imageWidth)
        img.drawWidth = img_width
        img.drawHeight = img_width * aspect
        t_map = Table([[img]], colWidths=[available_width])
        t_map.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_map)
    else:
        story.append(Paragraph("(Keine Karte)", style_tab_norm))
        
    story.append(PageBreak())
    
    # --- SEITE 2: SCHICHTENVERZEICHNIS (SPLIT COLUMNS) ---
    
    # 8 Spalten Layout für DIN Konformität
    h_row1 = [
        Paragraph("1", style_geo_header), 
        Paragraph("2", style_geo_header), 
        Paragraph("3", style_geo_header), 
        Paragraph("4", style_geo_header), 
        Paragraph("5", style_geo_header), 
        Paragraph("6", style_geo_header), 
        Paragraph("7", style_geo_header),
        Paragraph("8", style_geo_header)
    ]
    
    h_row2 = [
        Paragraph("Bis<br/>m", style_geo_header),
        Paragraph("a) Benennung<br/>b) Ergänzung", style_geo_norm),
        Paragraph("c) Bohrgut<br/>d) Vorgang", style_geo_norm),
        Paragraph("e) Farbe", style_geo_norm),
        Paragraph("f) Üblich<br/>g) Geol.", style_geo_norm),
        Paragraph("h) Gruppe<br/>i) Kalk", style_geo_norm),
        Paragraph("Bemerkung", style_geo_norm),
        Paragraph("Proben<br/>(Art/Nr/Tiefe)", style_geo_norm)
    ]
    
    table_data = [h_row1, h_row2]
    
    for _, row in df_geo.iterrows():
        # Textaufbau für die einzelnen Zellen
        # Spalte 2: a + b
        txt_ab = f"a) {row['a']}"
        if row['b']: txt_ab += f"<br/>b) {row['b']}"
        
        # Spalte 3: c + d
        txt_cd = ""
        if row['c']: txt_cd += f"c) {row['c']}"
        if row['d']: txt_cd += f"<br/>d) {row['d']}"
        
        # Spalte 4: e
        txt_e = f"e) {row['e']}" if row['e'] else ""
        
        # Spalte 5: f + g
        txt_fg = ""
        if row['f']: txt_fg += f"f) {row['f']}"
        if row['g']: txt_fg += f"<br/>g) {row['g']}"
        
        # Spalte 6: h + i
        txt_hi = ""
        if row['h']: txt_hi += f"h) {row['h']}"
        if row['i']: txt_hi += f"<br/>i) {row['i']}"
        
        # Spalte 8: Proben (Stacked)
        txt_proben = ""
        if row['p_art'] or row['p_nr'] or row['p_tiefe'] > 0:
            txt_proben = f"{row['p_art']} {row['p_nr']}<br/>{row['p_tiefe']:.2f}m"

        table_data.append([
            Paragraph(f"{row['Bis_m']:.2f}", style_geo_norm),
            Paragraph(txt_ab, style_geo_norm),
            Paragraph(txt_cd, style_geo_norm),
            Paragraph(txt_e, style_geo_norm),
            Paragraph(txt_fg, style_geo_norm),
            Paragraph(txt_hi, style_geo_norm),
            Paragraph(str(row['Bemerkung']), style_geo_norm),
            Paragraph(txt_proben, style_geo_norm)
        ])
    
    # Spaltenbreiten (Summe ca 17cm)
    # 1: 1.3, 2: 3.5, 3: 2.0, 4: 1.5, 5: 2.0, 6: 1.5, 7: 3.2, 8: 2.0
    col_widths = [1.3*cm, 3.5*cm, 2.0*cm, 1.5*cm, 2.0*cm, 1.5*cm, 3.2*cm, 2.0*cm]
    
    t_geo = Table(table_data, colWidths=col_widths, repeatRows=2)
    t_geo.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (0,0), (7,0), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,1), colors.lightgrey),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_geo)
    story.append(PageBreak())
    
    if svg_bytes:
        try:
            drawing = svg2rlg(BytesIO(svg_bytes.encode('utf-8')))
            avail_width = 460
            factor = avail_width / drawing.width
            drawing.width = drawing.width * factor
            drawing.height = drawing.height * factor
            drawing.scale(factor, factor)
            story.append(drawing)
        except: pass

    doc.build(story, onFirstPage=draw_header_on_page, onLaterPages=draw_header_on_page)
    return buffer.getvalue()

# ==============================================================================
# 4. GUI
# ==============================================================================

with st.expander("1. Kopfblatt & Standort", expanded=True):
    col_map, col_data = st.columns([1, 1])
    with col_data:
        st.subheader("Stammdaten")
        logo_upload = st.file_uploader("Firmenlogo (für PDF Header)", type=["png", "jpg", "jpeg"])
        
        projekt = st.text_input("Projekt / Bohrung", value="Notwasserbrunnen ZE079-905")
        ort = st.text_input("Ort / Adresse", value="Wiesenschlag ggü 4, 14129 Berlin")
        kreis = st.text_input("Kreis", value="Berlin")
        
        c_zweck, c_art = st.columns(2)
        zweck = c_zweck.text_input("Zweck der Bohrung", value="Notbrunnen")
        art_bohrung = c_art.text_input("Art der Bohrung", value="Grundwasser") 
        
        if st.button("📍 Adresse suchen"):
            try:
                loc = Nominatim(user_agent="app").geocode(ort)
                if loc: st.session_state.lat, st.session_state.lon = loc.latitude, loc.longitude
            except: pass

        st.markdown("---")
        c1, c2 = st.columns(2)
        auftraggeber = c1.text_input("Auftraggeber", value="Berliner Wasserbetriebe")
        objekt = c2.text_input("Objekt", value="Notbrunnen")
        
        c3, c4 = st.columns(2)
        bohrfirma = c3.text_input("Bohrunternehmer", value="Ackermann KG")
        geraetefuehrer = c4.text_input("Geräteführer", value="C. Kempcke")
        
        datum_str = st.text_input("Bohrzeitraum", value="06.10.25 - 08.10.25")
        
        c5, c6 = st.columns(2)
        bohrdurchmesser = c5.number_input("Durchmesser (mm)", value=330)
        bohrverfahren = c6.text_input("Verfahren", value="Spülbohren")
        
        c7, c8 = st.columns(2)
        ansatzpunkt = c7.number_input("Ansatzhöhe (m)", value=0.0)
        endteufe = c8.number_input("Endteufe (m)", value=45.0)
        
        st.markdown("---")
        c_coord1, c_coord2 = st.columns(2)
        rechtswert = c_coord1.text_input("Rechtswert (Gitter)", value="378879.57")
        hochwert = c_coord2.text_input("Hochwert (Gitter)", value="5810039.19")
        aktenzeichen = st.text_input("Aktenzeichen", value="V26645")

    with col_map:
        m = folium.Map([st.session_state.lat, st.session_state.lon], zoom_start=16)
        folium.CircleMarker([st.session_state.lat, st.session_state.lon], radius=8, color="red", fill=True, fill_color="red").add_to(m)
        st_folium(m, height=350)

with st.expander("2. Schichtenverzeichnis (DIN Eingabe)", expanded=False):
    default_geo = [
        {"Bis_m": 14.00, "a": "mittelsandig", "b": "", "c": "erdfeucht", "d": "mäßig schwer", "e": "braun", "f": "Sand", "g": "", "h": "SE", "i": "0", "Bemerkung": "", "p_art": "", "p_nr": "", "p_tiefe": 0.0},
        {"Bis_m": 29.00, "a": "Tf, Mutterboden", "b": "", "c": "steif", "d": "mäßig schwer", "e": "dunkelbraun", "f": "Mudde", "g": "", "h": "SU*-TL", "i": "+", "Bemerkung": "WSP angebohrt", "p_art": "", "p_nr": "", "p_tiefe": 0.0},
    ]
    df_geo = st.data_editor(
        pd.DataFrame(default_geo), 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Bis_m": st.column_config.NumberColumn("Bis (m)", format="%.2f"),
            "a": st.column_config.TextColumn("a) Benennung"),
            "b": st.column_config.TextColumn("b) Ergänzung"),
            "c": st.column_config.TextColumn("c) Beschaff. Bohrgut"),
            "d": st.column_config.TextColumn("d) Beschaff. Vorgang"),
            "e": st.column_config.TextColumn("e) Farbe"),
            "f": st.column_config.SelectboxColumn("f) Übl. Benennung", options=["Sand", "Kies", "Mudde", "Mergel", "Ton", "Schluff", "Mutterboden"]),
            "g": st.column_config.TextColumn("g) Geol. Benennung"),
            "h": st.column_config.TextColumn("h) Gruppe"),
            "i": st.column_config.SelectboxColumn("i) Kalk", options=["0", "+", "++", "+++"]),
            "Bemerkung": st.column_config.TextColumn("Bemerkungen"),
            "p_art": st.column_config.TextColumn("Probe Art"),
            "p_nr": st.column_config.TextColumn("Probe Nr"),
            "p_tiefe": st.column_config.NumberColumn("Probe Tiefe", format="%.2f")
        }
    )

with st.expander("3. Ausbau", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        default_rohr = [{"Von": 0.0, "Bis": 40.0, "Typ": "Vollrohr", "DN": 150}, {"Von": 40.0, "Bis": 44.0, "Typ": "Filterrohr", "DN": 150}]
        df_rohr = st.data_editor(pd.DataFrame(default_rohr), num_rows="dynamic", key="rohr")
        ws_ruhe = st.number_input("Ruhewasser (m u. GOK)", value=14.70)
    with c2:
        default_ring = [{"Von": 0.0, "Bis": 14.0, "Mat": "Filterkies"}, {"Von": 14.0, "Bis": 29.0, "Mat": "Tonsperre"}]
        df_ring = st.data_editor(pd.DataFrame(default_ring), num_rows="dynamic", key="ring")

# --- OUTPUT ---
st.divider()

logo_bytes = logo_upload.getvalue() if logo_upload else None

meta_data = {
    "projekt": projekt, "ort": ort, "firma": bohrfirma, "auftraggeber": auftraggeber,
    "datum": datum_str, "aktenzeichen": aktenzeichen, 
    "verfahren": bohrverfahren, "durchmesser": bohrdurchmesser,
    "ansatz": ansatzpunkt, "teufe": endteufe, "ws_ruhe": ws_ruhe,
    "kreis": kreis, "zweck": zweck, "art_bohrung": art_bohrung, "objekt": objekt,
    "geraetefuehrer": geraetefuehrer,
    "rechtswert": rechtswert, "hochwert": hochwert,
    "logo_bytes": logo_bytes
}

if st.button("📄 PDF mit Logo erstellen"):
    svg_str = generate_svg_string(df_geo, df_rohr, df_ring, meta_data)
    map_buf = get_static_map_image(st.session_state.lat, st.session_state.lon)
    pdf = create_multipage_pdf_with_header(meta_data, df_geo, df_rohr, df_ring, svg_str, map_buf)
    st.download_button("📥 PDF Download", pdf, "Bohrprotokoll.pdf", "application/pdf")
