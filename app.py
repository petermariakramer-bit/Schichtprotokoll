import streamlit as st
import pandas as pd

st.set_page_config(page_title="Brunnen-Profil Generator", layout="wide")

st.title("🕳️ Brunnen-Bohrprofil Generator")

# --- 1. DATEN EINGABE ---

default_data = [
    {"von": 0.0, "bis": 0.4, "material": "Mutterboden", "beschriftung": "Mutterboden"},
    {"von": 0.4, "bis": 3.5, "material": "Sand/Kies", "beschriftung": "Sand, Kies"},
    {"von": 3.5, "bis": 4.6, "material": "Lehm", "beschriftung": "Sand, lehmig, kiesig"},
    {"von": 4.6, "bis": 10.9, "material": "Kies", "beschriftung": "Kies, Sand, lehmig"},
    {"von": 10.9, "bis": 12.0, "material": "Fels", "beschriftung": "Sandgestein"},
]

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Geologie Eingabe")
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

# --- 2. SVG GENERIERUNG ---

def generate_svg(data_df):
    scale_y = 40  # Pixel pro Meter (etwas größer für bessere Lesbarkeit)
    offset_y = 60 # Platz oben für Überschrift
    offset_x = 100 # Platz links für die Skala
    
    # Maximale Tiefe ermitteln für die Höhe des Bildes
    max_depth = data_df["bis"].max() if not data_df.empty else 10
    svg_height = max_depth * scale_y + 100
    
    # SVG Start
    svg = f'<svg width="600" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">'
    
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

    # --- ÜBERSCHRIFT ---
    svg += f'<text x="{offset_x + 50}" y="30" font-family="Arial" font-size="20" font-weight="bold" text-anchor="middle">Bohrprofil</text>'

    # --- HINTERGRUND-LINIEN (Meter-Skala links) ---
    # Wir zeichnen kleine Striche für jeden vollen Meter
    for i in range(int(max_depth) + 1):
        y_pos = i * scale_y + offset_y
        # Kleiner Strich bei der Skala
        svg += f'<line x1="40" y1="{y_pos}" x2="50" y2="{y_pos}" stroke="black" stroke-width="1" />'
        # Dreieck-Symbol (Niveau-Pfeil)
        svg += f'<path d="M45,{y_pos} l-5,-5 l10,0 z" fill="none" stroke="black" />'
        # Text (-1.00 m)
        svg += f'<text x="35" y="{y_pos}" font-family="Arial" font-size="10" text-anchor="end" dominant-baseline="middle">-{i}.00 m</text>'

    # --- HAUPTZEICHNUNG ---
    for index, row in data_df.iterrows():
        try:
            tiefe_von = float(row["von"])
            tiefe_bis = float(row["bis"])
            material = row["material"]
            text = row["beschriftung"]
            
            # Berechnungen
            height = (tiefe_bis - tiefe_von) * scale_y
            y_start = tiefe_von * scale_y + offset_y
            y_end = tiefe_bis * scale_y + offset_y
            
            # 1. Rechteck (Die Schicht)
            svg += f'<rect x="{offset_x}" y="{y_start}" width="100" height="{height}" fill="url(#pat-{material})" stroke="black" stroke-width="1" />'
            
            # 2. Exakte Tiefenangabe (Links am Balken, z.B. 3.50m)
            # Wir zeichnen die Zahl nur am unteren Ende der Schicht
            svg += f'<line x1="{offset_x}" y1="{y_end}" x2="{offset_x - 5}" y2="{y_end}" stroke="black" />' # Kleiner Strich
            svg += f'<text x="{offset_x - 8}" y="{y_end}" font-family="Arial" font-size="11" text-anchor="end" dominant-baseline="middle">{tiefe_bis:.2f}m</text>'

            # Oberste Linie (0.00m) auch beschriften beim ersten Element
            if index == 0:
                 svg += f'<text x="{offset_x - 8}" y="{y_start}" font-family="Arial" font-size="11" text-anchor="end" dominant-baseline="middle">0.00m</text>'

            # 3. Beschreibungstext (Rechts vom Balken)
            text_y = y_start + (height / 2)
            svg += f'<line x1="{offset_x + 100}" y1="{text_y}" x2="{offset_x + 110}" y2="{text_y}" stroke="#666" />'
            svg += f'<text x="{offset_x + 115}" y="{text_y}" font-family="Arial" font-size="12" dominant-baseline="middle">{text}</text>'
            
        except ValueError:
            continue

    svg += '</svg>'
    return svg

# --- 3. AUSGABE ---

with col2:
    st.subheader("Vorschau")
    if not edited_df.empty:
        svg_code = generate_svg(edited_df)
        st.components.v1.html(svg_code, height=800, scrolling=True)
    else:
        st.warning("Bitte Daten eingeben.")

# Optional: Code anzeigen
with st.expander("SVG Code für Export"):
    st.code(generate_svg(edited_df), language='xml')
