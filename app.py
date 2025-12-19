import streamlit as st
import pandas as pd
import html
from io import BytesIO

# --- KONFIGURATION & PDF CHECK ---
st.set_page_config(page_title="Profi Brunnen-Profil", layout="wide")
HAS_PDF_LIBS = False
try:
    # Versuchen, PDF-Bibliotheken zu importieren, falls vorhanden
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    HAS_PDF_LIBS = True
except ImportError:
    pass # Läuft auch ohne PDF weiter

st.title("🕳️ Brunnen-Profil Generator")

# --- 1. EINGABE: KOPFBOGEN ---

with st.expander("📝 Projekt-Daten (Kopfbogen)", expanded=True):
    col_h1, col_h2, col_h3 = st.columns(3)
    # Hinweis: Bitte keine Sonderzeichen wie & oder < > verwenden, um SVG-Fehler zu vermeiden.
    with col_h1:
        company_name = st.text_input("Firmenname", value="SK Brunnenbohr GmbH")
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

col_left, col_right = st.columns([1, 1.5]) # Rechte Spalte etwas breiter für die Vorschau

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
    # WICHTIG: IDs haben Unterstriche statt Schrägstriche (z.B. pat-Sand_Kies)
    svg += '''
    <defs>
        <pattern id="pat-Sand_Kies" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#ffd700" fill-opacity="0.3"/>
             <circle cx="2" cy="2" r="1" fill="#d4a017" />
             <circle cx="7" cy="7" r="1" fill="#d4a017" />
        </pattern>
        <pattern id="pat-Lehm" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#d2b48c" fill-opacity="0.3"/>
             <path d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2" stroke="#8b4513" stroke-width="1
