import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
import html
from io import BytesIO
import time

# --- NEU: StaticMap für PDF-Kartenbilder ---
from staticmap import StaticMap, CircleMarker as StaticCircleMarker

# --- REPORTLAB IMPORTS FÜR PDF ---
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

st.title("🕳️ Bohrprotokoll & Schichtenverzeichnis (DIN 4022/4023)")

# ==============================================================================
# 1. HELPER: STATISCHE KARTE GENERIEREN
# ==============================================================================
def get_static_map_image(lat, lon, zoom=15):
    """Erstellt ein PNG-Bild der Karte für das PDF."""
    try:
        # Breite/Höhe in Pixeln für das generierte Bild
        m = StaticMap(width=800, height=400, url_template='http://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
        
        # Roter Punkt Marker (Achtung: staticmap nutzt lon, lat)
        marker = StaticCircleMarker((lon, lat), 'red', 18) # 18px Radius
        m.add_marker(marker)
        
        # Bild rendern
        image = m.render(zoom=zoom)
        
        # In BytesIO speichern, damit ReportLab es lesen kann
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer
    except Exception as e:
        print(f"Fehler bei Karten-Generierung: {e}")
        return None

# ==============================================================================
# 2. EINGABE MASKE
# ==============================================================================

with st.expander("1. Kopfblatt & Standort (Seite 1)", expanded=True):
    col_map, col_data = st.columns([1, 1])
    
    with col_data:
        st.subheader("Stammdaten")
        projekt = st.text_input("Projekt / Bohrung", value="Notwasserbrunnen ZE079-905")
        ort = st.text_input("Ort / Adresse", value="Wiesenschlag ggü 4, 14129 Berlin")
        
        if st.button("📍 Adresse suchen"):
            try:
                geolocator = Nominatim(user_agent="brunnen_app_v2")
                location = geolocator.geocode(ort)
                if location:
                    st.session_state.lat = location.latitude
                    st.session_state.lon = location.longitude
                    st.success("Gefunden!")
                else: st.error("Nicht gefunden.")
            except: st.error("Fehler bei Suche.")

        c1, c2 = st.columns(2)
        auftraggeber = c1.text_input("Auftraggeber", value="Berliner Wasserbetriebe")
        bohrfirma = c2.text_input("Bohrunternehmer", value="Ackermann KG")
        
        c3, c4 = st.columns(2)
        datum_str = c3.text_input("Bohrzeitraum", value="06.10.25 - 08.10.25")
        aktenzeichen = c4.text_input("Aktenzeichen", value="V26645")
        
        c5, c6 = st.columns(2)
        ansatzpunkt = c5.number_input("Ansatzpunkt (m u. GOK)", value=0.0)
        endteufe = c6.number_input("Endteufe (m)", value=45.0)
        bohrverfahren = st.text_input("Bohrverfahren", value="Spülbohren, Ø 330mm")

    with col_map:
        st.subheader("Lageplan (Interaktiv)")
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=16)
        folium.CircleMarker([st.session_state.lat, st.session_state.lon], radius=8, color="red", fill=True, fill_color="red").add_to(m)
        st_folium(m, width="100%", height=350)
        st.info("Diese Ansicht ist interaktiv. Im PDF wird automatisch ein statisches Bild dieser Position generiert.")

with st.expander("2. Schichtenverzeichnis (Seite 2 & 3)", expanded=True):
    default_geologie = [
        {"Bis_m": 14.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "braun", "Konsistenz": "erdfeucht", "Gruppe": "SE", "Kalk": "0", "Bemerkung": "schwer zu bohren"},
        {"Bis_m": 29.00, "Benennung": "Mudde", "Zusatz": "organisch", "Farbe": "dunkelbraun", "Konsistenz": "steif", "Gruppe": "SU*-TL", "Kalk": "+", "Bemerkung": ""},
        {"Bis_m": 33.00, "Benennung": "Sand", "Zusatz": "feinsandig", "Farbe": "grau", "Konsistenz": "nass", "Gruppe": "SE", "Kalk": "+", "Bemerkung": ""},
        {"Bis_m": 39.00, "Benennung": "Mergel", "Zusatz": "Geschiebemergel", "Farbe": "grau", "Konsistenz": "steif", "Gruppe": "SU*-TL", "Kalk": "+", "Bemerkung": ""},
        {"Bis_m": 46.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "grau", "Konsistenz": "nass", "Gruppe": "SE", "Kalk": "+", "Bemerkung": ""},
    ]
    df_geo = st.data_editor(
        pd.DataFrame(default_geologie),
        num_rows="dynamic",
        column_config={
            "Bis_m": st.column_config.NumberColumn("Tiefe bis (m)", format="%.2f"),
            "Benennung": st.column_config.SelectboxColumn(options=["Mutterboden", "Sand", "Kies", "Mudde", "Mergel", "Ton", "Schluff"]),
            "Kalk": st.column_config.SelectboxColumn(options=["0", "+", "++"])
        }, use_container_width=True, key="geo_input"
    )

with st.expander("3. Ausbau & Wasserstände (Seite 4)", expanded=True):
    col_tech1, col_tech2 = st.columns(2)
    with col_tech1:
        st.markdown("**Rohrtour**")
        default_rohr = [
            {"Von": 0.0, "Bis": 40.0, "Typ": "Vollrohr", "DN": 150},
            {"Von": 40.0, "Bis": 44.0, "Typ": "Filterrohr", "DN": 150},
            {"Von": 44.0, "Bis": 45.0, "Typ": "Sumpfrohr", "DN": 150}
        ]
        df_rohr = st.data_editor(pd.DataFrame(default_rohr), num_rows="dynamic", use_container_width=True, key="rohr_input")
        ws_ruhe = st.number_input("Ruhewasserspiegel (m)", value=14.70)
        
    with col_tech2:
        st.markdown("**Ringraum**")
        default_ring = [
            {"Von": 0.0, "Bis": 14.0, "Mat": "Filterkies"},
            {"Von": 14.0, "Bis": 29.0, "Mat": "Tonsperre"},
            {"Von": 29.0, "Bis": 33.0, "Mat": "Filterkies"},
            {"Von": 33.0, "Bis": 39.0, "Mat": "Tonsperre"},
            {"Von": 39.0, "Bis": 45.0, "Mat": "Filterkies"}
        ]
        df_ring = st.data_editor(pd.DataFrame(default_ring), num_rows="dynamic", use_container_width=True, key="ring_input")

# ==============================================================================
# 3. PDF GENERIERUNG
# ==============================================================================

def create_multipage_pdf(meta, df_geo, df_rohr, df_ring, svg_bytes, map_image_buffer):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    story = []
    styles = getSampleStyleSheet()
    style_h1 = styles['Heading1']
    style_h2 = styles['Heading2']
    style_norm = styles['Normal']
    style_norm.fontSize = 10
    
    # --- SEITE 1: KOPFBLATT ---
    
    # Titelblock
    story.append(Paragraph("Bohr2000", style_h2)) 
    story.append(Paragraph(f"<b>{meta['firma']}</b>", style_h1))
    story.append(Paragraph("Kopfblatt zum Schichtenverzeichnis", style_h2))
    story.append(Spacer(1, 0.5*cm))
    
    # Stammdaten Tabelle
    data_stammdaten = [
        ["Projekt / Bohrung:", meta['projekt']],
        ["Ort:", meta['ort']],
        ["Auftraggeber:", meta['auftraggeber']],
        ["Bohrzeitraum:", meta['datum']],
        ["Aktenzeichen:", meta['aktenzeichen']],
        ["Bohrverfahren:", meta['verfahren']],
        ["Endteufe:", f"{meta['teufe']} m"],
        ["Ansatzpunkt:", f"{meta['ansatz']} m u. GOK"]
    ]
    t_stamm = Table(data_stammdaten, colWidths=[5*cm, 10*cm])
    t_stamm.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
    ]))
    story.append(t_stamm)
    story.append(Spacer(1, 0.5*cm))
    
    # --- KARTE EINFÜGEN ---
    story.append(Paragraph("Lageplan:", style_h2))
    
    if map_image_buffer:
        # Bild aus Speicher laden
        img = RLImage(map_image_buffer)
        
        # Bildgröße anpassen (z.B. max 16cm breit)
        img_width = 16 * cm
        aspect = img.imageHeight / float(img.imageWidth)
        img.drawHeight = img_width * aspect
        img.drawWidth = img_width
        
        story.append(img)
    else:
        story.append(Paragraph("(Kartenbild konnte nicht geladen werden)", style_norm))
        
    story.append(Spacer(1, 1*cm))
    
    # Zusammenfassung Ausbau (Tabelle unten Seite 1)
    story.append(Paragraph("Kurzzusammenfassung Ausbau:", style_h2))
    
    ausbau_data = [["Art", "Von (m)", "Bis (m)", "Details"]]
    for _, r in df_rohr.iterrows():
        ausbau_data.append([r['Typ'], f"{r['Von']:.2f}", f"{r['Bis']:.2f}", f"DN {r['DN']}"])
    for _, r in df_ring.iterrows():
        ausbau_data.append(["Ringraum (" + r['Mat'] + ")", f"{r['Von']:.2f}", f"{r['Bis']:.2f}", "-"])
        
    t_ausbau = Table(ausbau_data, colWidths=[5*cm, 3*cm, 3*cm, 4*cm])
    t_ausbau.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
    ]))
    story.append(t_ausbau)
    
    story.append(PageBreak())
    
    # --- SEITE 2/3: SCHICHTENVERZEICHNIS ---
    
    story.append(Paragraph(f"Schichtenverzeichnis: {meta['projekt']}", style_h2))
    story.append(Spacer(1, 0.5*cm))
    
    table_headers = ["Bis m", "Hauptbodenart", "Beschreibung / Zusatz", "Farbe", "Kalk", "Gruppe", "Bemerkung"]
    table_data = [table_headers]
    
    for _, row in df_geo.iterrows():
        p_benennung = Paragraph(str(row['Benennung']), style_norm)
        p_zusatz = Paragraph(str(row['Zusatz']), style_norm)
        p_bem = Paragraph(str(row['Bemerkung']), style_norm)
        
        table_data.append([
            f"{row['Bis_m']:.2f}",
            p_benennung,
            p_zusatz,
            row['Farbe'],
            row['Kalk'],
            row['Gruppe'],
            p_bem
        ])
        
    t_geo = Table(table_data, colWidths=[2*cm, 3*cm, 4*cm, 2.5*cm, 1.5*cm, 2*cm, 3*cm], repeatRows=1)
    t_geo.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke])
    ]))
    story.append(t_geo)
    
    story.append(PageBreak())
    
    # --- SEITE 4: ZEICHNERISCHE DARSTELLUNG (SVG) ---
    
    story.append(Paragraph("Zeichnerische Darstellung nach DIN 4023", style_h2))
    story.append(Spacer(1, 0.5*cm))
    
    if svg_bytes:
        try:
            drawing = svg2rlg(BytesIO(svg_bytes.encode('utf-8')))
            avail_width = 480
            factor = avail_width / drawing.width
            drawing.width = drawing.width * factor
            drawing.height = drawing.height * factor
            drawing.scale(factor, factor)
            story.append(drawing)
        except Exception as e:
            story.append(Paragraph(f"Fehler beim Rendern der Grafik: {e}", style_norm))
    
    doc.build(story)
    return buffer.getvalue()


def generate_svg_string(df_geo, df_rohr, df_ring, meta):
    scale_y = 15
    width = 700
    max_depth = 48
    if not df_geo.empty: max_depth = max(max_depth, df_geo['Bis_m'].max())
    total_height = 200 + (max_depth * scale_y) + 100
    
    svg = f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
    # Kurzversion der Patterns (bitte die langen aus der vorherigen Version übernehmen, falls nötig)
    svg += '''<defs>
    <pattern id="pat-Sand" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fffacd"/><circle cx="2" cy="2" r="1" fill="gold"/><circle cx="7" cy="7" r="1" fill="gold"/></pattern>
    <pattern id="pat-Mudde" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#ddd"/><path d="M0,5 h10" stroke="black" stroke-width="2"/></pattern>
    <pattern id="pat-Mergel" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#eee"/><path d="M0,0 l10,10 m0,-10 l-10,10" stroke="#555"/></pattern>
    <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#5c4033"/></pattern>
    <pattern id="pat-Tonsperre" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="brown"/><path d="M0,10 l10,-10" stroke="white"/></pattern>
    <pattern id="pat-Filterkies" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="white"/><circle cx="3" cy="3" r="1.5" fill="orange"/></pattern>
    <pattern id="pat-Filterrohr" width="10" height="5" patternUnits="userSpaceOnUse"><rect width="10" height="5" fill="white" stroke="black"/><line x1="2" y1="2" x2="8" y2="2" stroke="black"/></pattern>
    </defs>'''
    
    # Header
    svg += f'<rect x="10" y="10" width="{width-20}" height="150" fill="none" stroke="black"/>'
    svg += f'<text x="30" y="40" font-family="Arial" font-size="20" font-weight="bold" fill="green">Bohr2000</text>'
    svg += f'<text x="30" y="70" font-family="Arial" font-size="16">{html.escape(meta["firma"])}</text>'
    
    start_y = 180
    col_geo_x = 80
    col_geo_w = 100
    col_tech_x = 350
    
    # Skala
    svg += f'<line x1="{col_geo_x}" y1="{start_y}" x2="{col_geo_x}" y2="{start_y + max_depth*scale_y}" stroke="black"/>'
    for i in range(int(max_depth)+1):
        y = start_y + i*scale_y
        svg += f'<line x1="{col_geo_x}" y1="{y}" x2="{col_geo_x-5}" y2="{y}" stroke="black"/>'
        if i % 1 == 0: svg += f'<text x="{col_geo_x-10}" y="{y+3}" text-anchor="end" font-family="Arial" font-size="10">{i}</text>'

    # Geologie
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
        
    # Ausbau
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
# 4. OUTPUT & DOWNLOAD
# ==============================================================================

st.divider()

meta_data = {
    "projekt": projekt, "ort": ort, "firma": bohrfirma, "auftraggeber": auftraggeber,
    "datum": datum_str, "aktenzeichen": aktenzeichen, 
    "verfahren": bohrverfahren, "ansatz": ansatzpunkt, "teufe": endteufe
}

svg_str = generate_svg_string(df_geo, df_rohr, df_ring, meta_data)

st.subheader("Vorschau: Anlage Grafik (Seite 4)")
st.components.v1.html(svg_str, height=600, scrolling=True)

st.subheader("Finaler Download")
if st.button("📄 Gesamt-PDF erstellen (Seite 1-4)"):
    with st.spinner("Generiere PDF inkl. Karte..."):
        try:
            # 1. Kartenbild generieren
            map_buffer = get_static_map_image(st.session_state.lat, st.session_state.lon)
            
            # 2. PDF bauen (Karte übergeben)
            pdf_bytes = create_multipage_pdf(meta_data, df_geo, df_rohr, df_ring, svg_str, map_buffer)
            
            st.success("Erfolgreich erstellt!")
            st.download_button(
                label="📥 PDF herunterladen",
                data=pdf_bytes,
                file_name=f"Bohrprotokoll_{projekt.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Fehler bei PDF Generierung: {e}")
