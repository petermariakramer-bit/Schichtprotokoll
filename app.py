import streamlit as st
import pandas as pd
import html
from io import BytesIO

# --- KONFIGURATION ---
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

# --- 3. SVG GENERIERUNG ---
def generate_svg(data_df, meta_data):
    # --- EINSTELLUNGEN ---
    scale_y = 40  # Pixel pro Meter
    
    # NEUES LAYOUT:
    margin_top = 180      # Platz oben
    axis_x = 60           # X-Pos der linken Linie mit den Dreiecken
    profile_x = 160       # X-Pos wo das bunte Profil beginnt
    profile_width = 100   # Breite der bunten Säule
    total_width = 700
    
    max_depth = data_df["bis"].max() if not data_df.empty else 10
    total_height = margin_top + (max_depth * scale_y) + 100
    
    svg = f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">'
    
    # --- DEFS (Muster) ---
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

    # --- KOPFBOGEN ---
    def safe(text): return html.escape(str(text))

    head_height = 130
    svg += f'<rect x="10" y="10" width="{total_width-20}" height="{head_height}" fill="none" stroke="black" stroke-width="2"/>'
    
    # Firma (Links)
    svg += f'<text x="30" y="50" font-size="18" font-weight="bold" fill="black">{safe(meta_data["company"])}</text>'
    svg += f'<text x="30" y="75" font-size="12" fill="black">{safe(meta_data["address"])}</text>'
    
    # Trennlinie unten
    svg += f'<line x1="10" y1="{head_height+10}" x2="{total_width-10}" y2="{head_height+10}" stroke="black" stroke-width="2"/>'
    
    # Tabelle (Rechts)
    table_x = 350 
    svg += f'<line x1="{table_x}" y1="10" x2="{table_x}" y2="{head_height+10}" stroke="black" stroke-width="1"/>'
    row_h = head_height / 4
    for i in range(1, 4):
        y = 10 + i * row_h
        svg += f'<line x1="{table_x}" y1="{y}" x2="{total_width-10}" y2="{y}" stroke="black" stroke-width="0.5"/>'
    
    def get_row_svg(row_index, label, value):
        y_base = 10 + row_index * row_h
        text_y = y_base + (row_h / 2) + 4 
        return f'<text x="{table_x + 10}" y="{text_y}" font-size="10" font-weight="bold">{safe(label)}:</text>' \
               f'<text x="{table_x + 100}" y="{text_y}" font-size="12">{safe(value)}</text>'

    svg += get_row_svg(0, "Projekt", meta_data["project"])
    svg += get_row_svg(1, "Durchführung", meta_data["execution"])
    svg += get_row_svg(2, "Brunnentyp", meta_data["type"])
    svg += get_row_svg(3, "Datum", meta_data["date"])

    # Titel
    svg += f'<text x="{total_width/2}" y="{margin_top - 30}" font-size="18" font-weight="bold" text-anchor="middle">Bohrprofil</text>'

    # --- SKALA LINKS (Die Linie mit den Dreiecken) ---
    
    # Die Haupt-Vertikale Linie ganz links (Achse)
    svg += f'<line x1="{axis_x}" y1="{margin_top}" x2="{axis_x}" y2="{margin_top + max_depth * scale_y}" stroke="black" stroke-width="1" />'

    # Die Meter-Markierungen
    for i in range(int(max_depth) + 1):
        y_pos = i * scale_y + margin_top
        
        # 1. Das Dreieck (Niveau-Symbol) direkt auf der Achse
        # Pfad: Spitze unten auf der Linie, dann nach oben links und rechts
        svg += f'<path d="M{axis_x},{y_pos} l-5,-5 l10,0 z" fill="white" stroke="black" stroke-width="1"/>'
        
        # 2. Verbindungslinie von der Achse rüber zum Profil
        # Beginnt erst rechts vom Dreieck, damit es nicht durchgestrichen aussieht
        svg += f'<line x1="{axis_x + 5}" y1="{y_pos}" x2="{profile_x}" y2="{y_pos}" stroke="black" stroke-width="0.5" stroke-dasharray="2,2" />'
        
        # 3. Text (z.B. -1.00m) - Steht auf der Linie, links vom Dreieck
        svg += f'<text x="{axis_x - 10}" y="{y_pos - 2}" font-size="10" text-anchor="end">-{i}.00 m</text>'
        
        # 4. Kleiner Strich für den Text
        svg += f'<line x1="{axis_x - 5}" y1="{y_pos}" x2="{axis_x - 40}" y2="{y_pos}" stroke="black" stroke-width="0.5" />'


    # --- BOHRPROFIL (Die bunten Balken) ---
    for index, row in data_df.iterrows():
        try:
            tiefe_von = float(row["von"])
            tiefe_bis = float(row["bis"])
            material = row["material"]
            text = row["beschriftung"]
            
            safe_id = material.replace("/", "_").replace(" ", "_")
            
            height = (tiefe_bis - tiefe_von) * scale_y
            y_start = tiefe_von * scale_y + margin_top
            y_end = tiefe_bis * scale_y + margin_top
            
            # Rechteck
            svg += f'<rect x="{profile_x}" y="{y_start}" width="{profile_width}" height="{height}" fill="url(#pat-{safe_id})" stroke="black" />'
            
            # Exakte Tiefe (Zahl) direkt am Balken unten links
            svg += f'<text x="{profile_x - 5}" y="{y_end}" font-size="10" text-anchor="end" dominant-baseline="middle">{tiefe_bis:.2f}m</text>'
            # Kleiner Strich dazu
            svg += f'<line x1="{profile_x}" y1="{y_end}" x2="{profile_x - 5}" y2="{y_end}" stroke="black" />'
            
            # Beschriftung Text (Rechts)
            text_y = y_start + (height / 2)
            svg += f'<line x1="{profile_x + profile_width}" y1="{text_y}" x2="{profile_x + profile_width + 20}" y2="{text_y}" stroke="#666" />'
            svg += f'<text x="{profile_x + profile_width + 25}" y="{text_y}" font-size="12" dominant-baseline="middle">{safe(text)}</text>'
            
        except ValueError:
            continue

    svg += '</svg>'
    return svg

# --- 4. VORSCHAU ---
with col_right:
    st.subheader("Vorschau")
    meta_data = {
        "company": company_name, "address": address, 
        "project": project_name, "execution": execution, 
        "type": well_type, "date": date_str
    }
    
    if not edited_df.empty:
        svg_string = generate_svg(edited_df, meta_data)
        st.components.v1.html(svg_string, height=800, scrolling=True)
        
        st.download_button("📥 SVG Download", svg_string, f"{project_name}.svg", "image/svg+xml")
        
        if HAS_PDF_LIBS:
            try:
                drawing = svg2rlg(BytesIO(svg_string.encode('utf-8')))
                pdf_bytes = BytesIO()
                renderPDF.drawToFile(drawing, pdf_bytes)
                st.download_button("📄 PDF Download", pdf_bytes.getvalue(), f"{project_name}.pdf", "application/pdf")
            except: pass
    else:
        st.warning("Bitte Daten eingeben.")
