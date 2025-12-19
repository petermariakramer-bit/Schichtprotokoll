import streamlit as st
import pandas as pd
import html
from io import BytesIO

# --- KONFIGURATION & PDF CHECK ---
st.set_page_config(page_title="Profi Brunnen-Profil", layout="wide")

HAS_PDF_LIBS = False
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    HAS_PDF_LIBS = True
except ImportError:
    pass

st.title("🕳️ Brunnen-Profil Generator")

# --- 1. EINGABE: KOPFBOGEN ---

with st.expander("📝 Projekt-Daten (Kopfbogen)", expanded=True):
    col_h1, col_h2, col_h3 = st.columns(3)
    
    with col_h1:
        company_name = st.text_input("Firmenname", value="S&K Brunnenbohr GmbH")
        address = st.text_input("Anschrift/Standort", value="Industrieparkstrasse 13")
    
    with col_h2:
        project_name = st.text_input("Projekt", value="Musterprojekt")
        execution = st.text_input("Ausführung", value="Max Mustermann")
    
    with col_h3:
        well_type = st.text_input("Brunnentyp", value="Entnahmebrunnen")
        date_str = st.date_input("Datum").strftime("%d.%m.%Y")

# --- 2. EINGABE: SCHICHTEN ---

default_data = [
    {"von": 0.0, "bis": 0.4, "material": "Mutterboden", "beschriftung": "Mutterboden"},
    {"von": 0.4, "bis": 3.5, "material": "Sand/Kies", "beschriftung": "Sand, Kies"},
    {"von": 3.5, "bis": 4.6, "material": "Lehm", "beschriftung": "Sand, lehmig, kiesig"},
    {"von": 4.6, "bis": 10.9, "material": "Kies", "beschriftung": "Kies, Sand, lehmig"},
    {"von": 10.9, "bis": 12.0, "material": "Fels", "beschriftung": "Sandgestein"},
]

col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.subheader("Geologie Schichten")
    df = pd.DataFrame(default_data)
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        column_config={
            "material": st.column_config.SelectboxColumn(
                "Material",
                options=["Mutterboden", "Sand/Kies", "Lehm", "Kies", "Fels"],
                required=True
            ),
            "von": st.column_config.NumberColumn("Von (m)", format="%.2f"),
            "bis": st.column_config.NumberColumn("Bis (m)", format="%.2f"),
            "beschriftung": st.column_config.TextColumn("Beschriftung"),
        },
        use_container_width=True
    )

# --- 3. SVG GENERIERUNG (Die Engine) ---

def generate_svg(data_df, meta_data):
    # --- EINSTELLUNGEN ---
    scale_y = 40  # Pixel pro Meter Tiefe
    
    # Layout-Konstanten (angepasst für mehr Platz)
    margin_top = 200     # Mehr Platz oben für den Kopf
    margin_left = 130    # Viel mehr Platz links für die Skala
    graph_width = 120    # Breite der Bohrprofil-Säule
    
    # Gesamthöhe und -breite berechnen
    max_depth = data_df["bis"].max() if not data_df.empty else 10
    total_height = margin_top + (max_depth * scale_y) + 100
    total_width = 700    # Insgesamt breiter
    
    svg = f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">'
    
    # --- DEFS (Schraffur-Muster) ---
    svg += '''
    <defs>
        <pattern id="pat-Sand_Kies" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#ffd700" fill-opacity="0.3"/>
             <circle cx="2" cy="2" r="1" fill="#d4a017" />
             <circle cx="7" cy="7" r="1" fill="#d4a017" />
        </pattern>
        <pattern id="pat-Lehm" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#d2b48c" fill-opacity="0.3"/>
             <path d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2" stroke="#8b4513" stroke-width="1"/>
        </pattern>
        <pattern id="pat-Fels" width="20" height="20" patternUnits="userSpaceOnUse">
             <rect width="20" height="20" fill="#808080" fill-opacity="0.3"/>
             <path d="M0,0 L20,20 M20,0 L0,20" stroke="#333" stroke-width="1"/>
        </pattern>
        <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#5c4033"/>
        </pattern>
        <pattern id="pat-Kies" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#fffacd"/>
             <circle cx="3" cy="3" r="1.5" fill="#orange" />
             <circle cx="8" cy="8" r="1.5" fill="#orange" />
        </pattern>
    </defs>
    '''

    # --- KOPFBOGEN ZEICHNEN ---
    
    def safe(text):
        return html.escape(str(text))

    # Rahmen für den Kopf
    head_height = 130
    svg += f'<rect x="10" y="10" width="{total_width-20}" height="{head_height}" fill="none" stroke="black" stroke-width="2"/>'
    
    # Linker Bereich (Firmeninfo) - Schwarz, kleiner, besser positioniert
    svg += f'<text x="30" y="50" font-size="18" font-weight="bold" fill="black">{safe(meta_data["company"])}</text>'
    svg += f'<text x="30" y="75" font-size="12" fill="black">{safe(meta_data["address"])}</text>'
    
    # Trennlinie unten im Kopf
    svg += f'<line x1="10" y1="{head_height+10}" x2="{total_width-10}" y2="{head_height+10}" stroke="black" stroke-width="2"/>'
    
    # Rechter Bereich (Tabelle mit Projektinfos)
    table_x = 350 # Tabelle weiter nach rechts geschoben
    svg += f'<line x1="{table_x}" y1="10" x2="{table_x}" y2="{head_height+10}" stroke="black" stroke-width="1"/>' # Vertikale Linie
    
    # Horizontale Tabellenlinien
    row_h = head_height / 4
    for i in range(1, 4):
        y = 10 + i * row_h
        svg += f'<line x1="{table_x}" y1="{y}" x2="{total_width-10}" y2="{y}" stroke="black" stroke-width="0.5"/>'
    
    def get_row_svg(row_index, label, value):
        y_base = 10 + row_index * row_h
        text_y = y_base + (row_h / 2) + 4 
        row_str = f'<text x="{table_x + 10}" y="{text_y}" font-size="10" font-weight="bold">{safe(label)}:</text>'
        row_str += f'<text x="{table_x + 100}" y="{text_y}" font-size="12">{safe(value)}</text>'
        return row_str

    svg += get_row_svg(0, "Projekt", meta_data["project"])
    svg += get_row_svg(1, "Durchführung", meta_data["execution"])
    svg += get_row_svg(2, "Brunnentyp", meta_data["type"])
    svg += get_row_svg(3, "Datum", meta_data["date"])

    # Haupt-Überschrift unter dem Kopf
    svg += f'<text x="{total_width/2}" y="{margin_top - 30}" font-size="18" font-weight="bold" text-anchor="middle">Bohrprofil</text>'


    # --- HAUPTZEICHNUNG (DAS PROFIL) ---
    
    # 1. Skala und Dreiecke links zeichnen
    for i in range(int(max_depth) + 1):
        y_pos = i * scale_y + margin_top
        
        # a) Der kleine horizontale Strich am Profil
        svg += f'<line x1="{margin_left-10}" y1="{y_pos}" x2="{margin_left}" y2="{y_pos}" stroke="black" />'
        
        # b) Das Dreieck (Niveau-Marker)
        # Spitze ist bei (margin_left-10, y_pos). Pfad: MoveTo Spitze, LineUpLeft, LineRight, Close
        tip_x = margin_left - 10
        svg += f'<path d="M{tip_x},{y_pos} l-5,-5 l10,0 z" fill="white" stroke="black" stroke-width="1"/>'
        # Hinweis: fill="white" stroke="black" macht ein weißes Dreieck mit schwarzem Rand (wie im Plan). 
        # Wenn es ausgefüllt schwarz sein soll, ändere fill="black".
        
        # c) Der Text (Tiefe) - weiter nach links gerückt
        svg += f'<text x="{margin_left-25}" y="{y_pos}" font-size="10" text-anchor="end" dominant-baseline="middle">-{i}.00 m</text>'


    # 2. Die Schichten zeichnen
    for index, row in data_df.iterrows():
        try:
            tiefe_von = float(row["von"])
            tiefe_bis = float(row["bis"])
            material = row["material"]
            text = row["beschriftung"]
            
            # WICHTIG: Material-Name für die ID sicher machen (/ wird zu _)
            safe_material_id = material.replace("/", "_").replace(" ", "_")
            
            height = (tiefe_bis - tiefe_von) * scale_y
            y_start = tiefe_von * scale_y + margin_top
            y_end = tiefe_bis * scale_y + margin_top
            
            # Das Rechteck der Schicht
            svg += f'<rect x="{margin_left}" y="{y_start}" width="{graph_width}" height="{height}" fill="url(#pat-{safe_material_id})" stroke="black" />'
            
            # Exakte Tiefenangabe (unten links an der Schicht)
            svg += f'<text x="{margin_left-5}" y="{y_end}" font-size="10" text-anchor="end" dominant-baseline="middle">{tiefe_bis:.2f}m</text>'
            
            # Beschriftung (rechts daneben)
            text_y = y_start + (height / 2)
            svg += f'<line x1="{margin_left + graph_width}" y1="{text_y}" x2="{margin_left + graph_width + 20}" y2="{text_y}" stroke="#666" />'
            svg += f'<text x="{margin_left + graph_width + 25}" y="{text_y}" font-size="12" dominant-baseline="middle">{safe(text)}</text>'
            
        except ValueError:
            continue

    svg += '</svg>'
    return svg

# --- 4. VORSCHAU & DOWNLOAD ---

with col_right:
    st.subheader("Vorschau")
    
    # Metadaten sammeln
    meta_data = {
        "company": company_name,
        "address": address,
        "project": project_name,
        "execution": execution,
        "type": well_type,
        "date": date_str
    }
    
    if not edited_df.empty:
        # SVG String generieren
        svg_string = generate_svg(edited_df, meta_data)
        
        # Vorschau anzeigen
        st.components.v1.html(svg_string, height=800, scrolling=True)
        
        st.divider()
        st.subheader("Export")
        
        # 1. SVG Download
        st.download_button(
            label="📥 SVG herunterladen (Vektor)",
            data=svg_string,
            file_name=f"{project_name}_Profil.svg",
            mime="image/svg+xml"
        )
        
        # 2. PDF Download (optional)
        if HAS_PDF_LIBS:
            try:
                drawing = svg2rlg(BytesIO(svg_string.encode('utf-8')))
                pdf_bytes = BytesIO()
                renderPDF.drawToFile(drawing, pdf_bytes)
                st.download_button(
                    label="📄 PDF herunterladen",
                    data=pdf_bytes.getvalue(),
                    file_name=f"{project_name}_Profil.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF Fehler: {e}")
        else:
            st.info("Tipp: Installiere 'svglib' und 'reportlab' für direkten PDF-Export.")
            st.info("Alternative: Lade das SVG herunter und drucke es im Browser als PDF.")
    else:
        st.warning("Bitte Schichten definieren.")
