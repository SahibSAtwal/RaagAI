import streamlit as st
import pandas as pd
import os
import RaagEngine as engine
from RaagScraper import run_scraper
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Raag AI Dashboard", layout="wide", page_icon="🎼")

# Custom CSS to make it look "Predator" themed
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    stMetric { background-color: #1e2130; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎼 Raag AI: Research & Mapping Dashboard")
st.caption("Running on i9-14900HX High-Performance Engine")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("🛠️ Data Controls")

# 1. Scraper Section
with st.sidebar.expander("🌐 Web Scraper", expanded=False):
    st.info("Scraper uses the logic from RaagScraper.py")
    if st.button("Launch Scraper Interface"):
        run_scraper()
        st.success("Scrape Session Finished.")

st.sidebar.markdown("---")

# 2. Dataset Selection
raw_files = [f for f in os.listdir(engine.RAW_FOLDER) if f.endswith('.csv')]
if not raw_files:
    st.sidebar.error("No CSVs found in RawRaagData!")
    selected_file = None
else:
    selected_file = st.sidebar.selectbox("📂 Select Raw Dataset", raw_files)

st.sidebar.markdown("---")

# 3. Gravity Weights with Validation Logic
st.sidebar.subheader("⚖️ Gravity Weights")
st.sidebar.caption("Adjust how musical attributes pull Raags together.")

w_mukhya = st.sidebar.slider("Mukhya Ang", 0.0, 1.0, 0.40, step=0.05)
w_aroh = st.sidebar.slider("Aaroh/Avroh", 0.0, 1.0, 0.30, step=0.05)
w_vadi = st.sidebar.slider("Vadi/Samvadi", 0.0, 1.0, 0.20, step=0.05)
w_vish = st.sidebar.slider("Vishranti Sthan", 0.0, 1.0, 0.10, step=0.05)

# Calculate Total
total_weight = round(w_mukhya + w_aroh + w_vadi + w_vish, 2)

# Validation Check
if total_weight == 1.0:
    st.sidebar.success(f"Total Weight: {total_weight} ✅")
    ready_to_run = True
else:
    diff = round(1.0 - total_weight, 2)
    st.sidebar.error(f"Total Weight: {total_weight}")
    if diff > 0:
        st.sidebar.warning(f"Add {diff} more to reach 1.0")
    else:
        st.sidebar.warning(f"Remove {abs(diff)} to reach 1.0")
    ready_to_run = False

# --- MAIN AREA ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Dataset Analysis")
    if selected_file:
        df_raw = pd.read_csv(os.path.join(engine.RAW_FOLDER, selected_file))
        
        # Quick Stats
        c1, c2 = st.columns(2)
        c1.metric("Total Raags", len(df_raw))
        c2.metric("Source", selected_file.split('_')[0])
        
        st.markdown("---")
        
        # Processing Button
        st.write("✨ **Update 3D Coordinates**")
        if st.button("🚀 Run Gravity Engine", disabled=not ready_to_run, use_container_width=True):
            with st.spinner("Crunching Math on i9..."):
                # Load the specific raags
                raags = engine.load_data([selected_file])
                
                # Create custom weights dict from sliders
                custom_weights = {
                    'mukhya': w_mukhya, 
                    'aroh_avroh': w_aroh, 
                    'vadi_samvadi': w_vadi,
                    'vishranti': w_vish
                }
                
                # Run engine (Assumes engine.run_gravity_processing accepts a weights dict)
                processed = engine.run_gravity_processing(raags)
                engine.save_processed_files(processed, [selected_file])
                st.balloons()
                st.success("Gravity Processing Complete!")

with col2:
    st.subheader("🌐 3D Relationship Map")
    if selected_file:
        # Determine the name of the processed file
        if "MASTER" in selected_file:
            p_name = "MASTER_COMBINED_CALCULATED.csv"
        else:
            p_name = f"CALCULATED_{selected_file}"
            
        processed_path = os.path.join(engine.PROCESSED_FOLDER, p_name)
        
        if os.path.exists(processed_path):
            df_plot = pd.read_csv(processed_path)
            
            # Interactive 3D Plot
            fig = px.scatter_3d(
                df_plot, 
                x='Final_X', y='Final_Y', z='Final_Z',
                color='Magnitude', 
                hover_name='Raag Name',
                text='Raag Name',
                color_continuous_scale="Magma",
                height=650
            )
            
            fig.update_layout(
                template="plotly_dark",
                scene=dict(
                    xaxis=dict(title='Tivar (Sharp)'),
                    yaxis=dict(title='Shudh (Natural)'),
                    zaxis=dict(title='Komal (Flat)')
                ),
                margin=dict(l=0, r=0, b=0, t=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No processed data found for this file. Click 'Run Gravity Engine' on the left.")

# --- DATA INSPECTOR ---
st.markdown("---")
st.subheader("🔍 Raag Data Inspector")
if selected_file:
    search = st.text_input("Search Raag by name...", placeholder="e.g. Bhairav")
    if search:
        display_df = df_raw[df_raw['Raag Name'].str.contains(search, case=False, na=False)]
    else:
        display_df = df_raw
    
    st.dataframe(display_df, use_container_width=True)