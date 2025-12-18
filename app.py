import streamlit as st
import pandas as pd

# Konfiguration der Seite
st.set_page_config(page_title="Brunnen-Profil Generator", layout="wide")

st.title("🕳️ Brunnen-Bohrprofil Generator")
st.markdown("Definiere die Schichten in der Tabelle links. Die Grafik rechts aktualisiert sich automatisch.")

# --- 1. DATEN EINGABE ---

# Standard-Daten für den Start
default_data = [
    {"von": 0.0, "bis": 0.4, "material": "Mutterboden", "beschriftung": "Mutterboden"},
    {"von": 0.4, "bis": 3.5, "material": "Sand/Kies", "beschriftung": "Sand, Kies"},
    {"von": 3.5, "bis": 4.6, "material": "Lehm", "beschriftung": "Sand, lehmig"},
    {"von": 4.6, "bis": 10.0, "material": "Kies", "beschriftung": "Kies, Sand"},
    {"von": 10.0, "bis": 12.0, "material": "Fels", "beschriftung": "Sandgestein"},
]

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Geologie Eingabe")
    
    # Der Data Editor erlaubt das Hinzufügen/Löschen von Zeilen
    df = pd.DataFrame(default_data)
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        column_config={
            "material": st.column_config.SelectboxColumn(
                "Material",
                options=["Mutterboden", "Sand/Kies", "Lehm", "Kies", "Fels"],
                required=True
            )
        },
        use_container_width=True
    )

# --- 2. SVG GENERIERUNG (Die "Engine") ---

def generate_svg(data_df):
    scale_y = 30  # 1 Meter = 30 Pixel
    
    # Maximale Tiefe ermitteln
    max_depth = data_df["bis"].max() if not data_df.empty else 10
    svg_height = max_depth * scale_y + 50
    
    # SVG Header
    svg = f'<svg width="500" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">'
    
    # --- DEFS (Muster für Schraffuren) ---
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
             <circle cx="5" cy="5" r="2" fill="#orange" />
        </pattern>
    </defs>
    '''

    # --- ZEICHNEN ---
    
    # Skalen-Linie
    svg += f'<line x1="40" y1="20" x2="40" y2="{max_depth * scale_y + 20}" stroke="black" stroke-width="1" />'

    current_y = 20
    
    # Iterieren durch die Datenzeilen
    for index, row in data_df.iterrows():
        try:
            tiefe_von = float(row["von"])
            tiefe_bis = float(row["bis"])
            material = row["material"]
            text = row["beschriftung"]
            
            height = (tiefe_bis - tiefe_von) * scale_y
            y_pos = tiefe_von * scale_y + 20
            
            # Rechteck
            svg += f'<rect x="50" y="{y_pos}" width="100" height="{height}" fill="url(#pat-{material})" stroke="black" />'
            
            # Beschriftung Tiefe (Links)
            svg += f'<text x="35" y="{y_pos + height}" font-family="Arial" font-size="10" text-anchor="end" dominant-baseline="middle">{tiefe_bis:.2f}m</text>'
            
            # Beschriftung Text (Rechts)
            text_y = y_pos + (height / 2)
            svg += f'<line x1="150" y1="{text_y}" x2="160" y2="{text_y}" stroke="#666" />'
            svg += f'<text x="165" y="{text_y}" font-family="Arial" font-size="12" dominant-baseline="middle">{text}</text>'
            
        except ValueError:
            continue # Falls User ungültige Zahlen eingibt

    svg += '</svg>'
    return svg

# --- 3. AUSGABE ---

with col2:
    st.subheader("Vorschau")
    if not edited_df.empty:
        svg_code = generate_svg(edited_df)
        # HTML rendern
        st.components.v1.html(svg_code, height=800, scrolling=True)
    else:
        st.warning("Bitte Daten eingeben.")

# Button zum Anzeigen des Codes (für Debugging oder Export)
with st.expander("SVG Quellcode anzeigen (für Export)"):
    st.code(generate_svg(edited_df), language='xml')
