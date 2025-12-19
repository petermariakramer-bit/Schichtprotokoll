import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import html

# --- KONFIGURATION ---
st.set_page_config(page_title="Bohrprotokoll & Brunnenausbau Generator", layout="wide")

# Initialisiere Session State für Geodaten
if 'lat' not in st.session_state: st.session_state.lat = 52.42751
if 'lon' not in st.session_state: st.session_state.lon = 13.1905

st.title("🕳️ Professioneller Bohrprofil-Generator (DIN 4023 Stil)")

# --- TEIL 1: KOPFBLATT & KARTE ---
with st.expander("1. Kopfblatt & Standort (Seite 1)", expanded=True):
    col_map, col_data = st.columns([1, 1])
    
    with col_data:
        st.subheader("Stammdaten")
        # Daten aus Quelle [cite: 8]
        projekt = st.text_input("Projekt / Bohrung", value="Notwasserbrunnen ZE079-905")
        ort = st.text_input("Ort / Adresse", value="Wiesenschlag ggü 4, 14129 Berlin")
        
        if st.button("📍 Adresse suchen & Karte laden"):
            try:
                geolocator = Nominatim(user_agent="brunnen_app")
                location = geolocator.geocode(ort)
                if location:
                    st.session_state.lat = location.latitude
                    st.session_state.lon = location.longitude
                    st.success(f"Gefunden: {location.address}")
                else:
                    st.error("Adresse nicht gefunden.")
            except Exception as e:
                st.error(f"Fehler bei Geocoding: {e}")

        c1, c2 = st.columns(2)
        auftraggeber = c1.text_input("Auftraggeber", value="Berliner Wasserbetriebe")
        bohrfirma = c2.text_input("Bohrunternehmer", value="Ackermann KG")
        
        c3, c4 = st.columns(2)
        datum_start = c3.date_input("Beginn", value=pd.to_datetime("2025-10-06"))
        datum_ende = c4.date_input("Ende", value=pd.to_datetime("2025-10-08"))
        
        # Technische Daten [cite: 8]
        st.markdown("---")
        c5, c6 = st.columns(2)
        ansatzpunkt = c5.number_input("Höhe Ansatzpunkt (m u. GOK)", value=0.0)
        endteufe = c6.number_input("Endteufe (m)", value=45.0)
        bohrverfahren = st.text_input("Bohrverfahren", value="Spülbohren")
        bohrdurchmesser = st.number_input("Bohrdurchmesser (mm)", value=330)

  with col_map:
        st.subheader("Lageplan")
        # Karte rendern
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=16)
        
        # ÄNDERUNG: CircleMarker statt Marker für den "roten Punkt"
        folium.CircleMarker(
            location=[st.session_state.lat, st.session_state.lon],
            radius=8,          # Größe des Punktes
            popup=projekt,
            color="red",       # Randfarbe
            fill=True,
            fill_color="red",  # Füllfarbe
            fill_opacity=1.0,  # Deckkraft
            tooltip="Bohrpunkt"
        ).add_to(m)
        
        st_data = st_folium(m, width="100%", height=400)
        st.caption(f"Koordinaten: {st.session_state.lat:.5f}, {st.session_state.lon:.5f}")

# --- TEIL 2: SCHICHTENVERZEICHNIS (Eingabe wie Seite 2/3) ---
with st.expander("2. Schichtenverzeichnis (Seite 2 & 3)", expanded=True):
    st.info("Geben Sie hier die Geologie ein, analog zur Tabelle im PDF.")
    
    # Standardwerte basierend auf PDF Seite 2 
    default_geologie = [
        {"Tiefe bis (m)": 14.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "braun", "Konsistenz": "erdfeucht", "Kurzzeichen": "mS", "Gruppe": "SE", "Kalk": "0"},
        {"Tiefe bis (m)": 29.00, "Benennung": "Mudde", "Zusatz": "organisch", "Farbe": "dunkelbraun", "Konsistenz": "steif", "Kurzzeichen": "Mu", "Gruppe": "SU*-TL", "Kalk": "+"},
        {"Tiefe bis (m)": 33.00, "Benennung": "Sand", "Zusatz": "feinsandig", "Farbe": "grau", "Konsistenz": "nass", "Kurzzeichen": "fS", "Gruppe": "SE", "Kalk": "+"},
        {"Tiefe bis (m)": 39.00, "Benennung": "Mergel", "Zusatz": "Geschiebemergel", "Farbe": "grau", "Konsistenz": "steif", "Kurzzeichen": "Mg", "Gruppe": "SU*-TL", "Kalk": "+"},
        {"Tiefe bis (m)": 46.00, "Benennung": "Sand", "Zusatz": "mittelsandig", "Farbe": "grau", "Konsistenz": "nass", "Kurzzeichen": "mS", "Gruppe": "SE", "Kalk": "+"},
    ]
    
    df_geo = st.data_editor(
        pd.DataFrame(default_geologie),
        num_rows="dynamic",
        column_config={
            "Tiefe bis (m)": st.column_config.NumberColumn(format="%.2f"),
            "Benennung": st.column_config.SelectboxColumn("Hauptbodenart", options=["Mutterboden", "Sand", "Kies", "Mudde", "Mergel", "Ton", "Schluff"], required=True),
            "Farbe": st.column_config.SelectboxColumn(options=["braun", "dunkelbraun", "grau", "schwarz", "gelb"]),
            "Kalk": st.column_config.SelectboxColumn(options=["0", "+", "++", "+++"])
        },
        use_container_width=True,
        key="geo_editor"
    )

# --- TEIL 3: BRUNNENAUSBAU (Seite 4) ---
with st.expander("3. Brunnenausbau & Ringraum (Daten für Grafik)", expanded=True):
    col_rohr, col_ring = st.columns(2)
    
    with col_rohr:
        st.subheader("Rohrtour (Innen)")
        # Daten aus [cite: 20]
        default_rohre = [
            {"Von (m)": 0.00, "Bis (m)": 40.00, "Typ": "Vollrohr", "DN (mm)": 150},
            {"Von (m)": 40.00, "Bis (m)": 44.00, "Typ": "Filterrohr", "DN (mm)": 150}, # angepasst an Bild Seite 4
            {"Von (m)": 44.00, "Bis (m)": 45.00, "Typ": "Sumpfrohr", "DN (mm)": 150}
        ]
        df_rohr = st.data_editor(pd.DataFrame(default_rohre), num_rows="dynamic", use_container_width=True, key="rohr_editor")
        
        st.markdown("**Wasserstände [cite: 20]**")
        ws_ruhe = st.number_input("Ruhewasserspiegel (m u. GOK)", value=14.70)
    
    with col_ring:
        st.subheader("Ringraum (Außen)")
        # Daten aus [cite: 20] und Bild Seite 4 [cite: 82, 101, 108, 120]
        default_ringraum = [
            {"Von (m)": 0.00, "Bis (m)": 14.00, "Material": "Filterkies"},
            {"Von (m)": 14.00, "Bis (m)": 29.00, "Material": "Tonsperre"}, # Tf, Mu laut Grafik
            {"Von (m)": 29.00, "Bis (m)": 33.00, "Material": "Filterkies"},
            {"Von (m)": 33.00, "Bis (m)": 39.00, "Material": "Tonsperre"},
            {"Von (m)": 39.00, "Bis (m)": 45.00, "Material": "Filterkies"}
        ]
        df_ring = st.data_editor(
            pd.DataFrame(default_ringraum), 
            num_rows="dynamic", 
            column_config={
                "Material": st.column_config.SelectboxColumn(options=["Filterkies", "Tonsperre", "Zement", "Bohrgut"])
            },
            use_container_width=True, 
            key="ring_editor"
        )

# --- TEIL 4: SVG GENERIERUNG ---

def generate_svg_din4023(geo_data, pipe_data, ring_data, meta, width=800):
    # Skalierung: Seite 4 nutzt 1:240 [cite: 72]
    # Wir nehmen 4 Pixel pro Meter für gute Lesbarkeit am Bildschirm, aber layouten es wie DIN
    scale_y = 15 # Pixel pro Meter Tiefe
    
    max_depth = max(geo_data["Tiefe bis (m)"].max() if not geo_data.empty else 0, 45)
    header_height = 200
    footer_height = 100
    total_height = header_height + (max_depth * scale_y) + footer_height
    
    # Spaltenbreiten (Layout Seite 4)
    col_depth_x = 50
    col_geo_x = 100
    col_geo_w = 120
    col_tech_x = 300 # Start technischer Ausbau
    center_tech = 400
    
    svg = f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif">'
    
    # --- DEFINITIONEN (Muster/Schraffuren) ---
    svg += '''
    <defs>
        <pattern id="pat-Sand" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#fffacd"/> <circle cx="2" cy="2" r="1" fill="#d4a017" /><circle cx="7" cy="7" r="1" fill="#d4a017" />
        </pattern>
        <pattern id="pat-Mudde" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#dcdcdc"/>
             <line x1="0" y1="5" x2="10" y2="5" stroke="black" stroke-width="2"/>
        </pattern>
        <pattern id="pat-Mergel" width="10" height="10" patternUnits="userSpaceOnUse">
             <rect width="10" height="10" fill="#e0e0e0"/>
             <path d="M0,0 L10,10 M10,0 L0,10" stroke="#555" stroke-width="0.5"/>
        </pattern>
        <pattern id="pat-Mutterboden" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#5c4033"/></pattern>
        
        <pattern id="pat-Filterkies" width="6" height="6" patternUnits="userSpaceOnUse">
            <rect width="6" height="6" fill="#fff"/>
            <circle cx="3" cy="3" r="1.5" fill="orange" />
        </pattern>
        <pattern id="pat-Tonsperre" width="8" height="8" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#8b4513"/>
            <path d="M0,8 l8,-8" stroke="white" stroke-width="1"/>
        </pattern>
        <pattern id="pat-Filterrohr" width="10" height="4" patternUnits="userSpaceOnUse">
            <rect width="10" height="4" fill="white"/>
            <line x1="2" y1="2" x2="8" y2="2" stroke="black" stroke-width="1" />
        </pattern>
    </defs>
    '''
    
    # --- HEADER (Kopfblatt Info im SVG) ---
    svg += f'<rect x="10" y="10" width="{width-20}" height="{header_height-20}" fill="none" stroke="black"/>'
    svg += f'<text x="20" y="40" font-size="20" font-weight="bold" fill="green">Bohr2000</text>' # Logo Fake
    svg += f'<text x="20" y="70" font-size="16" font-weight="bold">{meta["firma"]}</text>'
    svg += f'<text x="200" y="40" font-size="14" font-weight="bold">Zeichnerische Darstellung nach DIN 4023</text>'
    svg += f'<text x="200" y="60" font-size="12">Projekt: {meta["projekt"]}</text>'
    svg += f'<text x="200" y="80" font-size="12">Ort: {meta["ort"]}</text>'
    svg += f'<text x="600" y="40" font-size="12">Datum: {meta["datum"]}</text>'
    svg += f'<text x="600" y="60" font-size="12">Maßstab: 1:240</text>'

    # --- HINTERGRUND & LINIE ---
    start_y = header_height
    # Vertikale Linien
    svg += f'<line x1="{col_geo_x}" y1="{start_y}" x2="{col_geo_x}" y2="{total_height-footer_height}" stroke="black"/>'
    svg += f'<line x1="{col_geo_x+col_geo_w}" y1="{start_y}" x2="{col_geo_x+col_geo_w}" y2="{total_height-footer_height}" stroke="black"/>'
    
    # --- GEOLOGIE (Seite 4 Links) ---
    last_y = start_y
    last_depth = 0
    
    for _, row in geo_data.iterrows():
        depth = float(row["Tiefe bis (m)"])
        h = (depth - last_depth) * scale_y
        
        # Muster Auswahl
        pat = "pat-Sand"
        if "Mudde" in row["Benennung"]: pat = "pat-Mudde"
        if "Mergel" in row["Benennung"]: pat = "pat-Mergel"
        if "Mutterboden" in row["Benennung"]: pat = "pat-Mutterboden"
        
        # Balken zeichnen
        svg += f'<rect x="{col_geo_x}" y="{last_y}" width="{col_geo_w}" height="{h}" fill="url(#{pat})" stroke="black" stroke-width="0.5"/>'
        
        # Beschriftung Tiefe & Kurzzeichen
        svg += f'<text x="{col_geo_x-5}" y="{last_y+h}" font-size="10" text-anchor="end">{depth:.2f}</text>'
        svg += f'<line x1="{col_geo_x-10}" y1="{last_y+h}" x2="{col_geo_x}" y2="{last_y+h}" stroke="black"/>'
        
        # Kurzzeichen (groß, mittig wie im PDF bei "Mu") [cite: 85, 90]
        kz = row["Kurzzeichen"]
        if pd.notna(kz):
            svg += f'<text x="{col_geo_x+col_geo_w/2}" y="{last_y+h/2}" font-size="18" text-anchor="middle" fill="black" stroke="white" stroke-width="0.5" paint-order="stroke">{kz}</text>'

        last_y += h
        last_depth = depth

    # --- TECHNISCHER AUSBAU (Seite 4 Rechts) ---
    # Bohrloch (Ringraum)
    last_ring_y = start_y
    last_ring_depth = 0
    hole_radius = 60 # Visuelle Breite
    
    for _, row in ring_data.iterrows():
        depth_to = float(row["Bis (m)"])
        depth_from = float(row["Von (m)"])
        h = (depth_to - depth_from) * scale_y
        y = start_y + (depth_from * scale_y)
        
        mat = "pat-Filterkies"
        if "Ton" in row["Material"]: mat = "pat-Tonsperre"
        
        # Zeichnen (Ringraum = Volle Breite - Rohr) -> Hier vereinfacht: Volle Breite als Hintergrund
        svg += f'<rect x="{center_tech - hole_radius}" y="{y}" width="{hole_radius*2}" height="{h}" fill="url(#{mat})" stroke="black"/>'
        
        # Beschriftung Ringraum (rechts) [cite: 82, 101]
        svg += f'<text x="{center_tech + hole_radius + 10}" y="{y+h}" font-size="10">{depth_to:.2f} {row["Material"]}</text>'
        svg += f'<line x1="{center_tech + hole_radius}" y1="{y+h}" x2="{center_tech + hole_radius + 5}" y2="{y+h}" stroke="black"/>'

    # Rohre (Innen)
    pipe_radius = 30
    for _, row in pipe_data.iterrows():
        depth_to = float(row["Bis (m)"])
        depth_from = float(row["Von (m)"])
        h = (depth_to - depth_from) * scale_y
        y = start_y + (depth_from * scale_y)
        
        fill = "white"
        if "Filter" in row["Typ"]: fill = "url(#pat-Filterrohr)"
        elif "Sumpf" in row["Typ"]: fill = "#ddd"
        
        svg += f'<rect x="{center_tech - pipe_radius}" y="{y}" width="{pipe_radius*2}" height="{h}" fill="{fill}" stroke="black" stroke-width="1.5"/>'
        
        # Beschriftung Rohr (rechts, leicht versetzt) 
        if "Filter" in row["Typ"]:
             svg += f'<text x="{center_tech + pipe_radius + 80}" y="{y+h-5}" font-size="10" font-style="italic">Schlitzfilter</text>'

    # --- WASSERSTÄNDE  ---
    if meta["ws_ruhe"]:
        ws_y = start_y + (meta["ws_ruhe"] * scale_y)
        svg += f'<line x1="{col_geo_x-20}" y1="{ws_y}" x2="{col_geo_x+20}" y2="{ws_y}" stroke="blue" stroke-width="1.5"/>'
        svg += f'<path d="M{col_geo_x},{ws_y} l-5,-8 l10,0 z" fill="white" stroke="blue"/>'
        svg += f'<text x="{col_geo_x-25}" y="{ws_y}" font-size="10" fill="blue" text-anchor="end">{meta["ws_ruhe"]:.2f}</text>'

    # --- FOOTER ---
    foot_y = total_height - 60
    svg += f'<rect x="10" y="{foot_y}" width="{width-20}" height="50" fill="none" stroke="black"/>'
    svg += f'<text x="20" y="{foot_y+30}" font-size="24" font-weight="bold">{meta["firma"]}</text>'
    svg += f'<text x="400" y="{foot_y+30}" font-size="16">Tel.: 030-7822363</text>'

    svg += '</svg>'
    return svg

# --- OUTPUT BEREICH ---
st.divider()
st.subheader("4. Generierte Ergebnisse")

meta_data = {
    "projekt": projekt,
    "ort": ort,
    "firma": bohrfirma,
    "datum": f"{datum_start.strftime('%d.%m.%y')} - {datum_ende.strftime('%d.%m.%y')}",
    "ws_ruhe": ws_ruhe
}

if not df_geo.empty:
    svg_code = generate_svg_din4023(df_geo, df_rohr, df_ring, meta_data)
    
    c_prev, c_down = st.columns([2, 1])
    with c_prev:
        st.markdown("### Vorschau (Seite 4)")
        st.image(svg_code, use_column_width=True) # Trick: Streamlit rendert SVG Strings oft direkt oder via HTML
        st.components.v1.html(svg_code, height=800, scrolling=True)
        
    with c_down:
        st.success("Grafik generiert!")
        st.download_button(
            label="💾 SVG Plan herunterladen",
            data=svg_code,
            file_name=f"Bohrprofil_{projekt.replace(' ', '_')}.svg",
            mime="image/svg+xml"
        )
        st.info("Hinweis: Das SVG kann in Browsern geöffnet oder in CAD importiert werden.")
