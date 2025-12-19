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

st.title("🕳️ Brunnen-Profil Generator (Geologie & Ausbau)")

# --- 1. DATEN-EINGABE (Jetzt mit Tabs für Geologie & Ausbau) ---

with st.expander("📝 Projekt-Daten (Kopfbogen)", expanded=False):
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

col_input, col_preview = st.columns([1, 1.5])

with col_input:
    tab1, tab2, tab3 = st.tabs(["🪨 Geologie", "🔧 Rohrtour", "🏗️ Ringraum"])
    
    # --- TAB 1: GEOLOGIE ---
    with tab1:
        st.caption("Bodenschichten definieren")
        default_geo = [
            {"von": 0.0, "bis": 0.4, "material": "Mutterboden", "txt": "Mutterboden"},
            {"von": 0.4, "bis": 3.5, "material": "Sand/Kies", "txt": "Sand, Kies"},
            {"von": 3.5, "bis": 4.6, "material": "Lehm", "txt": "Sand, lehmig"},
            {"von": 4.6, "bis": 14.3, "material": "Kies", "txt": "Kies, Sand"},
            {"von": 14.3, "bis": 18.2, "material": "Kies_Wasser", "txt": "Kies, wasserführend"},
            {"von": 18.2, "bis": 21.0, "material": "Fels", "txt": "Fels"},
        ]
        df_geo = st.data_editor(
            pd.DataFrame(default_geo),
            num_rows="dynamic",
            column_config={
                "material": st.column_config.SelectboxColumn("Material", options=["Mutterboden", "Sand/Kies", "Lehm", "Kies", "Kies_Wasser", "Fels"], required=True),
                "von": st.column_config.NumberColumn("Von", format="%.2f"),
                "bis": st.column_config.NumberColumn("Bis", format="%.2f"),
                "txt": st.column_config.TextColumn("Beschriftung")
            }, use_container_width=True, key="editor_geo"
        )

    # --- TAB 2: ROHRTOUR (Inneres) ---
    with tab2:
        st.caption("Rohre von oben nach unten")
        default_pipe = [
            {"von": 0.0, "bis": 15.0, "typ": "Vollrohr", "dn": 150},
            {"von": 15.0, "bis": 20.0, "typ": "Filterrohr", "dn": 150},
            {"von": 20.0, "bis": 21.0, "typ": "Sumpfrohr", "dn": 150},
        ]
        df_pipe = st.data_editor(
            pd.DataFrame(default_pipe),
            num_rows="dynamic",
            column_config={
                "typ": st.column_config.SelectboxColumn("Typ", options=["Vollrohr", "Filterrohr", "Sumpfrohr"], required=True),
                "von": st.column_config.NumberColumn("Von", format="%.2f"),
                "bis": st.column_config.NumberColumn("Bis", format="%.2f"),
                "dn": st.column_config.NumberColumn("DN (mm)", step=1)
            }, use_container_width=True, key="editor_pipe"
        )
        
        st.divider()
        st.caption("Wasserstände & Pumpe")
        c1, c2, c3 = st.columns(3)
        ws_ruhe = c1.number_input("Ruhewasser (m)", value=11.80)
        ws_absenk = c2.number_input("Abgesenkt (m)", value=13.10)
        pump_depth = c3.number_input("Pumpentiefe (m)", value=18.50)

    # --- TAB 3: RINGRAUM (Äußeres) ---
    with tab3:
        st.caption("Füllung zwischen Bohrloch und Rohr")
        default_annulus = [
            {"von": 0.0, "bis": 2.0, "mat": "Bohrgut"},
            {"von": 2.0, "bis": 5.0, "mat": "Tonsperre"},
            {"von": 5.0, "bis": 11.5, "mat": "Bohrgut"},
            {"von": 11.5, "bis": 14.0, "mat": "Tonsperre"},
            {"von": 14.0, "bis": 21.0, "mat": "Filterkies"},
        ]
        df_annulus = st.data_editor(
            pd.DataFrame(default_annulus),
            num_rows="dynamic",
            column_config={
                "mat": st.column_config.SelectboxColumn("Material", options=["Bohrgut", "Tonsperre", "Filterkies", "Zement"], required=True),
                "von": st.column_config.NumberColumn("Von", format="%.2f"),
                "bis": st.column_config.NumberColumn("Bis", format="%.2f"),
            }, use_container_width=True, key="editor_annulus"
        )


# --- SVG ENGINE ---

def generate_svg(df_geo, df_pipe, df_annulus, meta_data, extras):
    # --- SETUP ---
    scale_y = 35  # Pixel pro Meter (etwas kleiner damit mehr drauf passt)
    max_depth = max(df_geo["bis"].max() if not df_geo.empty else 0, df_pipe["bis"].max() if not df_pipe.empty else 0)
    if max_depth == 0: max_depth = 10
    
    # Layout-Konstanten X-Achse
    margin_top = 220
    
    # Spalte 1: Geologie
    axis_geo_x = 60
    geo_x = 130
    geo_width = 90
    
    # Spalte 2: Ausbau
    build_center_x = 450 # Mittelachse des Brunnens
    hole_radius = 50     # Radius Bohrloch (visuell)
    pipe_radius = 25     # Radius Rohr (visuell)
    
    total_width = 800
    total_height = margin_top + (max_depth * scale_y) + 100
    
    svg = f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">'
    
    # --- MUSTER (PATTERNS) ---
    svg += '''
    <defs>
        <pattern id="pat-Sand_Kies" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#fffacd"/>
             <circle cx="2" cy="2" r="1" fill="#d4a017" /><circle cx="7" cy="7" r="1" fill="#d4a017" />
        </pattern>
        <pattern id="pat-Lehm" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#d2b48c" fill-opacity="0.4"/>
             <path d="M0,10 l10,-10" stroke="#8b4513" stroke-width="1"/>
        </pattern>
        <pattern id="pat-Fels" width="20" height="20" patternUnits="userSpaceOnUse">
             <rect width="20" height="20" fill="#808080" fill-opacity="0.3"/>
             <path d="M0,0 L20,20 M20,0 L0,20" stroke="#333" stroke-width="1"/>
        </pattern>
        <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#5c4033"/></pattern>
        <pattern id="pat-Kies" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#fffacd"/>
             <circle cx="5" cy="5" r="2" fill="orange" />
        </pattern>
        <pattern id="pat-Kies_Wasser" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#e0ffff"/>
             <circle cx="3" cy="3" r="1.5" fill="blue" /><circle cx="8" cy="8" r="1.5" fill="blue" />
        </pattern>
        
        <pattern id="pat-Filter" width="10" height="4" patternUnits="userSpaceOnUse">
            <rect width="10" height="4" fill="white"/>
            <line x1="0" y1="2" x2="10" y2="2" stroke="black" stroke-width="1" />
        </pattern>
        <pattern id="pat-Tonsperre" width="8" height="8" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#8b4513"/>
            <path d="M0,8 l8,-8" stroke="white" stroke-width="1" opacity="0.5"/>
        </pattern>
        <pattern id="pat-Filterkies" width="6" height="6" patternUnits="userSpaceOnUse">
            <rect width="6" height="6" fill="#fff"/>
            <circle cx="3" cy="3" r="1" fill="#555" />
        </pattern>
        <pattern id="pat-Bohrgut" width="10" height="10" patternUnits="userSpaceOnUse">
            <rect width="10" height="10" fill="#ccc"/>
            <path d="M0,0 l5,5 M5,0 l-5,5" stroke="#999" stroke-width="1"/>
        </pattern>
    </defs>
    '''
    
    # --- HELPER ---
    def safe(t): return html.escape(str(t))

    # --- KOPFBOGEN ---
    head_h = 130
    svg += f'<rect x="10" y="10" width="{total_width-20}" height="{head_h}" fill="none" stroke="black" stroke-width="2"/>'
    svg += f'<text x="30" y="50" font-size="20" font-weight="bold" fill="black">{safe(meta_data["company"])}</text>'
    svg += f'<text x="30" y="75" font-size="12" fill="black">{safe(meta_data["address"])}</text>'
    svg += f'<line x1="10" y1="{head_h+10}" x2="{total_width-10}" y2="{head_h+10}" stroke="black" stroke-width="2"/>'
    
    # Tabelle rechts
    t_x = 450
    svg += f'<line x1="{t_x}" y1="10" x2="{t_x}" y2="{head_h+10}" stroke="black" stroke-width="1"/>'
    row_h = head_h/4
    for i in range(1,4):
        y = 10 + i*row_h
        svg += f'<line x1="{t_x}" y1="{y}" x2="{total_width-10}" y2="{y}" stroke="black" stroke-width="0.5"/>'
    
    def draw_row(idx, lab, val):
        y = 10 + idx*row_h + row_h/2 + 4
        return f'<text x="{t_x+10}" y="{y}" font-size="10" font-weight="bold">{safe(lab)}:</text><text x="{t_x+100}" y="{y}" font-size="12">{safe(val)}</text>'
    
    svg += draw_row(0,"Projekt", meta_data["project"])
    svg += draw_row(1,"Durchführung", meta_data["execution"])
    svg += draw_row(2,"Typ", meta_data["type"])
    svg += draw_row(3,"Datum", meta_data["date"])

    # --- ÜBERSCHRIFTEN ---
    title_y = margin_top - 40
    svg += f'<text x="{geo_x + geo_width/2}" y="{title_y}" font-size="18" font-weight="bold" text-anchor="middle">Bohrprofil</text>'
    svg += f'<text x="{build_center_x}" y="{title_y}" font-size="18" font-weight="bold" text-anchor="middle">Brunnenausbau</text>'

    # --- SKALA LINKS ---
    svg += f'<line x1="{axis_geo_x}" y1="{margin_top}" x2="{axis_geo_x}" y2="{margin_top + max_depth * scale_y}" stroke="black" stroke-width="1" />'
    for i in range(int(max_depth) + 1):
        y = i * scale_y + margin_top
        svg += f'<path d="M{axis_geo_x},{y} l-5,-5 l10,0 z" fill="white" stroke="black"/>'
        svg += f'<text x="{axis_geo_x - 10}" y="{y-2}" font-size="10" text-anchor="end">-{i}.00m</text>'
        # Hilfslinie quer rüber
        if i % 5 == 0 and i > 0:
             svg += f'<line x1="{axis_geo_x}" y1="{y}" x2="{total_width-50}" y2="{y}" stroke="#ddd" stroke-dasharray="4,4"/>'

    # --- TEIL 1: GEOLOGIE ZEICHNEN ---
    for _, row in df_geo.iterrows():
        try:
            h = (float(row["bis"]) - float(row["von"])) * scale_y
            y = float(row["von"]) * scale_y + margin_top
            mat = row["material"].replace("/","_").replace(" ","_")
            
            # Block
            svg += f'<rect x="{geo_x}" y="{y}" width="{geo_width}" height="{h}" fill="url(#pat-{mat})" stroke="black"/>'
            # Tiefe
            svg += f'<text x="{geo_x-5}" y="{y+h}" font-size="10" text-anchor="end" dominant-baseline="middle">{float(row["bis"]):.2f}m</text>'
            # Text
            tx_y = y + h/2
            svg += f'<line x1="{geo_x+geo_width}" y1="{tx_y}" x2="{geo_x+geo_width+10}" y2="{tx_y}" stroke="#666"/>'
            svg += f'<text x="{geo_x+geo_width+15}" y="{tx_y}" font-size="12" dominant-baseline="middle">{safe(row["txt"])}</text>'
        except: continue

    # --- TEIL 2: BRUNNENAUSBAU ZEICHNEN ---
    
    # A) Ringraum (Zwiebelschale außen)
    # Wir zeichnen Rechtecke von build_center_x nach links und rechts
    for _, row in df_annulus.iterrows():
        try:
            h = (float(row["bis"]) - float(row["von"])) * scale_y
            y = float(row["von"]) * scale_y + margin_top
            mat = row["mat"].replace("/","_") # Filterkies, Tonsperre...
            
            # Volle Breite des Bohrlochs
            svg += f'<rect x="{build_center_x - hole_radius}" y="{y}" width="{hole_radius*2}" height="{h}" fill="url(#pat-{mat})" stroke="black" stroke-width="0.5"/>'
            
            # Beschriftung Ringraum (rechts außen)
            if h > 10: # Nur wenn hoch genug
                svg += f'<line x1="{build_center_x + hole_radius}" y1="{y+h/2}" x2="{build_center_x + hole_radius + 40}" y2="{y+h/2}" stroke="black" stroke-width="0.5"/>'
                svg += f'<text x="{build_center_x + hole_radius + 45}" y="{y+h/2}" font-size="11" dominant-baseline="middle">{safe(row["mat"])}</text>'
        except: continue

    # B) Rohrtour (Zentral)
    last_pipe_bottom = 0
    for _, row in df_pipe.iterrows():
        try:
            depth_to = float(row["bis"])
            h = (depth_to - float(row["von"])) * scale_y
            y = float(row["von"]) * scale_y + margin_top
            typ = row["typ"]
            dn = row["dn"]
            last_pipe_bottom = y + h
            
            fill = "white"
            if typ == "Filterrohr": fill = "url(#pat-Filter)"
            if typ == "Sumpfrohr": fill = "#ddd"
            
            # Rohr zeichnen
            svg += f'<rect x="{build_center_x - pipe_radius}" y="{y}" width="{pipe_radius*2}" height="{h}" fill="{fill}" stroke="black" stroke-width="1.5"/>'
            
            # Beschriftung Rohr (links vom Ausbau)
            svg += f'<line x1="{build_center_x - pipe_radius}" y1="{y+h/2}" x2="{build_center_x - pipe_radius - 20}" y2="{y+h/2}" stroke="black" stroke-width="0.5"/>'
            svg += f'<text x="{build_center_x - pipe_radius - 25}" y="{y+h/2}" font-size="11" text-anchor="end" dominant-baseline="middle">{typ} DN{dn}</text>'
            
            # Tiefe markieren (rechts am Rohr)
            svg += f'<text x="{build_center_x - pipe_radius - 5}" y="{y+h}" font-size="9" text-anchor="end" dominant-baseline="middle">{depth_to:.2f}m</text>'
            svg += f'<line x1="{build_center_x - pipe_radius}" y1="{y+h}" x2="{build_center_x - pipe_radius - 5}" y2="{y+h}" stroke="black"/>'

        except: continue

    # C) Bodenkappe
    if last_pipe_bottom > 0:
        svg += f'<rect x="{build_center_x - pipe_radius}" y="{last_pipe_bottom}" width="{pipe_radius*2}" height="5" fill="black"/>'
        svg += f'<text x="{build_center_x + pipe_radius + 5}" y="{last_pipe_bottom + 5}" font-size="10">Bodenkappe</text>'

    # D) Wasserstände
    # Ruhewasser
    rw_y = extras["ws_ruhe"] * scale_y + margin_top
    svg += f'<line x1="{build_center_x+pipe_radius+5}" y1="{rw_y}" x2="{build_center_x+pipe_radius+30}" y2="{rw_y}" stroke="blue" stroke-width="1"/>'
    svg += f'<path d="M{build_center_x+pipe_radius+15},{rw_y} l-5,-8 l10,0 z" fill="none" stroke="blue"/>' # Dreieck leer
    svg += f'<text x="{build_center_x+pipe_radius+35}" y="{rw_y}" font-size="10" fill="blue" dominant-baseline="middle">RW {extras["ws_ruhe"]:.2f}m</text>'

    # Absenkung
    aw_y = extras["ws_absenk"] * scale_y + margin_top
    svg += f'<line x1="{build_center_x+pipe_radius+5}" y1="{aw_y}" x2="{build_center_x+pipe_radius+30}" y2="{aw_y}" stroke="blue" stroke-width="1"/>'
    svg += f'<path d="M{build_center_x+pipe_radius+15},{aw_y} l-5,-8 l10,0 z" fill="blue" stroke="blue"/>' # Dreieck voll
    svg += f'<text x="{build_center_x+pipe_radius+35}" y="{aw_y+10}" font-size="10" fill="blue" dominant-baseline="middle">AW {extras["ws_absenk"]:.2f}m</text>'

    # E) Pumpe
    p_y = extras["pump_depth"] * scale_y + margin_top
    # Symbol Pumpe (Kreis mit Dreieck drin)
    svg += f'<circle cx="{build_center_x}" cy="{p_y}" r="12" fill="white" stroke="black" stroke-width="2"/>'
    svg += f'<path d="M{build_center_x},{p_y-8} l-7,12 l14,0 z" fill="black"/>'
    svg += f'<line x1="{build_center_x}" y1="{p_y-12}" x2="{build_center_x}" y2="{p_y-100}" stroke="black" stroke-width="2"/>' # Steigleitung
    svg += f'<text x="{build_center_x+15}" y="{p_y}" font-size="11" font-weight="bold">Pumpe ({extras["pump_depth"]:.2f}m)</text>'

    svg += '</svg>'
    return svg

# --- 4. OUTPUT ---
with col_preview:
    st.subheader("Vorschau")
    
    meta_data = {
        "company": company_name, "address": address, 
        "project": project_name, "execution": execution, 
        "type": well_type, "date": date_str
    }
    extras = {
        "ws_ruhe": st.session_state.get("ws_ruhe", 11.80) if 'ws_ruhe' not in st.session_state else ws_ruhe,
        "ws_absenk": st.session_state.get("ws_absenk", 13.10) if 'ws_absenk' not in st.session_state else ws_absenk,
        "pump_depth": st.session_state.get("pump_depth", 18.50) if 'pump_depth' not in st.session_state else pump_depth
    } # Fallback Logik für Session State

    if not df_geo.empty:
        svg_string = generate_svg(df_geo, df_pipe, df_annulus, meta_data, extras)
        st.components.v1.html(svg_string, height=900, scrolling=True)
        
        st.download_button("📥 SVG Plan herunterladen", svg_string, f"{project_name}_Complete.svg", "image/svg+xml")
        
        if HAS_PDF_LIBS:
            try:
                drawing = svg2rlg(BytesIO(svg_string.encode('utf-8')))
                pdf_bytes = BytesIO()
                renderPDF.drawToFile(drawing, pdf_bytes)
                st.download_button("📄 PDF Plan herunterladen", pdf_bytes.getvalue(), f"{project_name}.pdf", "application/pdf")
            except: pass
