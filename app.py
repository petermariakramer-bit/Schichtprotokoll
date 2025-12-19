import streamlit as st
import pandas as pd

# Bibliotheken für PDF Konvertierung
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False

st.set_page_config(page_title="Profi Brunnen-Profil", layout="wide")

st.title("🕳️ Brunnen-Profil Generator & PDF Export")

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

col_left, col_right = st.columns([1, 1.2])

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
        },
        use_container_width=True
    )

# --- 3. SVG GENERIERUNG ---

def generate_svg(data_df, meta_data):
    scale_y = 40  # Pixel pro Meter
    
    # Layout-Konstanten
    margin_top = 180  # Platz für den Kopfbogen
    margin_left = 80
    graph_width = 400
    
    max_depth = data_df["bis"].max() if not data_df.empty else 10
    total_height = margin_top + (max_depth * scale_y) + 100
    total_width = 600
    
    svg = f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">'
    
    # --- DEFS (Muster) ---
    svg += '''
    <defs>
        <pattern id="pat-Sand/Kies" width="10" height="10" patternUnits="userSpaceOnUse">
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
    # Rahmen um den Kopf
    svg += f'<rect x="10" y="10" width="{total_width-20}" height="120" fill="none" stroke="black" stroke-width="2"/>'
    
    # Logo Bereich (Links oben)
    svg += f'<text x="30" y="50" font-size="24" font-weight="bold" fill="#8B0000">{meta_data["company"]}</text>'
    svg += f'<text x="30" y="80" font-size="12">{meta_data["address"]}</text>'
    svg += f'<line x1="10" y1="130" x2="{total_width-10}" y2="130" stroke="black" stroke-width="2"/>' # Trennlinie unten
    
    # Tabelle rechts im Kopf (Projektinfos)
    table_x = 300
    svg += f'<line x1="{table_x}" y1="10" x2="{table_x}" y2="130" stroke="black" stroke-width="1"/>' # Vertikale Linie
    
    # Zeilen
    row_h = 30
    for i in range(1, 4):
        y = 10 + i * row_h
        svg += f'<line x1="{table_x}" y1="{y}" x2="{total_width-10}" y2="{y}" stroke="black" stroke-width="0.5"/>'
    
    # --- KORREKTUR HIER ---
    # Wir definieren eine Funktion, die den String ZURÜCKGIBT, anstatt "svg" direkt zu ändern.
    def get_row_svg(y, label, value):
        row_str = f'<text x="{table_x + 5}" y="{y+20}" font-size="10" font-weight="bold">{label}:</text>'
        row_str += f'<text x="{table_x + 80}" y="{y+20}" font-size="12">{value}</text>'
        return row_str

    # Jetzt fügen wir das Ergebnis an "svg" an
    svg += get_row_svg(10, "Projekt", meta_data["project"])
    svg += get_row_svg(40, "Durchführung", meta_data["execution"])
    svg += get_row_svg(70, "Brunnentyp", meta_data["type"])
    svg += get_row_svg(100, "Datum", meta_data["date"])
    # -----------------------

    # Titel unter dem Kopf
    svg += f'<text x="{total_width/2}" y="160" font-size="18" font-weight="bold" text-anchor="middle">Bohrprofil</text>'

    # --- HAUPTZEICHNUNG ---
    
    # Meter-Skala (Links)
    for i in range(int(max_depth) + 1):
        y_pos = i * scale_y + margin_top
        svg += f'<line x1="{margin_left-10}" y1="{y_pos}" x2="{margin_left}" y2="{y_pos}" stroke="black" />'
        svg += f'<text x="{margin_left-15}" y="{y_pos}" font-size="10" text-anchor="end" dominant-baseline="middle">-{i}.00 m</text>'

    # Schichten
    for index, row in data_df.iterrows():
        try:
            tiefe_von = float(row["von"])
            tiefe_bis = float(row["bis"])
            material = row["material"]
            text = row["beschriftung"]
            
            height = (tiefe_bis - tiefe_von) * scale_y
            y_start = tiefe_von * scale_y + margin_top
            y_end = tiefe_bis * scale_y + margin_top
            
            # Schicht-Rechteck
            svg += f'<rect x="{margin_left}" y="{y_start}" width="120" height="{height}" fill="url(#pat-{material})" stroke="black" />'
            
            # Exakte Tiefe
            svg += f'<text x="{margin_left-5}" y="{y_end}" font-size="10" text-anchor="end" dominant-baseline="middle">{tiefe_bis:.2f}m</text>'
            
            # Beschriftung
            text_y = y_start + (height / 2)
            svg += f'<line x1="{margin_left + 120}" y1="{text_y}" x2="{margin_left + 140}" y2="{text_y}" stroke="#666" />'
            svg += f'<text x="{margin_left + 145}" y="{text_y}" font-size="12" dominant-baseline="middle">{text}</text>'
            
        except ValueError:
            continue

    svg += '</svg>'
    return svg

# --- 4. VORSCHAU & DOWNLOAD ---

with col_right:
    st.subheader("Vorschau")
    
    # Daten sammeln
    meta_data = {
        "company": company_name,
        "address": address,
        "project": project_name,
        "execution": execution,
        "type": well_type,
        "date": date_str
    }
    
    if not edited_df.empty:
        # SVG erstellen
        svg_string = generate_svg(edited_df, meta_data)
        
        # Anzeigen
        st.components.v1.html(svg_string, height=800, scrolling=True)
        
        st.divider()
        st.subheader("Export")
        
        # 1. SVG Download (immer verfügbar)
        st.download_button(
            label="📥 SVG herunterladen (Vektor)",
            data=svg_string,
            file_name=f"{project_name}_Profil.svg",
            mime="image/svg+xml"
        )
        
        # 2. PDF Download (Nur wenn Bibliotheken da sind)
        if HAS_PDF_LIBS:
            # Konvertierung
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
                st.error(f"PDF Fehler: {e}. Bitte SVG nutzen.")
        else:
            st.warning("Für PDF-Export bitte 'svglib' und 'reportlab' installieren.")

    else:
        st.info("Bitte Schichten definieren.")
