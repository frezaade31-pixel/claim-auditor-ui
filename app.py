import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Claim Auditor - RSPAD",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (TAMPILAN CARD UI MODERN) ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200..800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
    .stApp { background-color: #f6f7f8; font-family: 'Manrope', sans-serif; }
    .block-container { padding-top: 2rem; }
    
    /* Card Style */
    .custom-card {
        background-color: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 16px;
    }
    
    /* Metrics */
    .metric-value { font-size: 32px; font-weight: 800; color: #111827; }
    .metric-label { font-size: 14px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Buttons & Inputs */
    .stButton>button { border-radius: 12px; height: 3em; font-weight: 600; }
    div[data-testid="stFileUploader"] { border-radius: 12px; }
    
    /* Custom Badge */
    .badge-red { background: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .badge-green { background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- LOGIKA PROGRAM (MESIN DETEKSI) ---
def clean_currency(x):
    if isinstance(x, str):
        return float(x.replace('.', '').replace(',', '.'))
    return x

def normalisasi_kartu(series):
    return series.astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False).str.replace('.0', '', regex=False).str.strip()

@st.cache_data
def process_data(file_ri, file_rj):
    # 1. Load Data Rawat Inap
    try:
        df_ri = pd.read_excel(file_ri)
    except:
        df_ri = pd.read_csv(file_ri, sep=None, engine='python') # Auto-detect separator
        
    # 2. Load Data Rawat Jalan
    try:
        df_rj = pd.read_csv(file_rj, sep=';') # Coba separator ; dulu
        if df_rj.shape[1] < 2: # Kalau gagal, coba koma
            df_rj = pd.read_csv(file_rj, sep=',')
    except:
        df_rj = pd.read_excel(file_rj)

    # 3. Normalisasi Nama Kolom (Agar standar)
    # Cari kolom yang mirip 'No_Kartu' atau 'NOKARTU'
    col_kartu_ri = [c for c in df_ri.columns if 'KARTU' in c.upper()][0]
    col_kartu_rj = [c for c in df_rj.columns if 'KARTU' in c.upper()][0]
    
    # Cari kolom Tanggal (Masuk/Pulang)
    col_tgl_ri = [c for c in df_ri.columns if 'MASUK' in c.upper() or 'ADMISSION' in c.upper()][0]
    col_tgl_plg_ri = [c for c in df_ri.columns if 'KELUAR' in c.upper() or 'DISCHARGE' in c.upper()][0]
    col_tgl_rj = [c for c in df_rj.columns if 'MASUK' in c.upper() or 'ADMISSION' in c.upper() or 'TGL' in c.upper()][0]

    # Rename agar seragam
    df_ri = df_ri.rename(columns={col_kartu_ri: 'No_Kartu', col_tgl_ri: 'Tgl_Masuk', col_tgl_plg_ri: 'Tgl_Keluar'})
    df_rj = df_rj.rename(columns={col_kartu_rj: 'No_Kartu', col_tgl_rj: 'Tgl_Pelayanan'})

    # 4. Normalisasi Data (Pembersihan Ekstrem)
    df_ri['No_Kartu'] = normalisasi_kartu(df_ri['No_Kartu'])
    df_rj['No_Kartu'] = normalisasi_kartu(df_rj['No_Kartu'])
    
    df_ri['Tgl_Masuk'] = pd.to_datetime(df_ri['Tgl_Masuk'], dayfirst=True, errors='coerce')
    df_ri['Tgl_Keluar'] = pd.to_datetime(df_ri['Tgl_Keluar'], dayfirst=True, errors='coerce')
    df_rj['Tgl_Pelayanan'] = pd.to_datetime(df_rj['Tgl_Pelayanan'], dayfirst=True, errors='coerce')

    # 5. Deteksi Irisan (Merging)
    # Gabungkan data berdasarkan No_Kartu dulu
    merged = pd.merge(df_rj, df_ri, on='No_Kartu', how='inner', suffixes=('_RJ', '_RI'))
    
    # Filter: Pasien RJ yang datang saat dia sedang Rawat Inap (Di antara Masuk & Keluar)
    # Logika: Tgl_RJ >= Tgl_Masuk_RI AND Tgl_RJ <= Tgl_Keluar_RI
    irisan = merged[
        (merged['Tgl_Pelayanan'] >= merged['Tgl_Masuk']) & 
        (merged['Tgl_Pelayanan'] <= merged['Tgl_Keluar'])
    ].copy()

    # Hitung Potensi Biaya (Jika ada kolom tarif)
    total_potensi = 0
    col_tarif = [c for c in df_rj.columns if 'TARIF' in c.upper() or 'BIAYA' in c.upper()]
    if col_tarif:
        # Ambil kolom tarif pertama yang ditemukan
        merged_tarif_col = col_tarif[0] + '_RJ' if col_tarif[0] in irisan.columns else col_tarif[0]
        if merged_tarif_col in irisan.columns:
            irisan[merged_tarif_col] = irisan[merged_tarif_col].apply(clean_currency)
            total_potensi = irisan[merged_tarif_col].sum()

    return df_ri, df_rj, irisan, total_potensi

# --- LAYOUT UI ---

# Header Section
c1, c2 = st.columns([8, 2])
with c1:
    st.markdown("### 🏥 Claim Auditor System")
    st.markdown("**RSPAD Gatot Soebroto** • Internal Audit Dashboard")
with c2:
    st.markdown('<div style="text-align: right; color: #6b7280; font-size: 12px; margin-top: 5px;">v2.0 Pro Edition</div>', unsafe_allow_html=True)

st.markdown("---")

# File Upload Section (Sidebar or Top Expandable)
with st.expander("📂 **Upload Data Klaim (Klik Disini)**", expanded=True):
    c_up1, c_up2 = st.columns(2)
    ri_file = c_up1.file_uploader("Upload Data Rawat Inap (Excel/CSV)", type=['xlsx', 'csv'])
    rj_file = c_up2.file_uploader("Upload Data Rawat Jalan (Excel/CSV)", type=['xlsx', 'csv'])

# Main Dashboard Logic
if ri_file and rj_file:
    # Proses Data
    with st.spinner('Sedang melakukan audit data...'):
        try:
            df_ri, df_rj, hasil_irisan, potensi_rp = process_data(ri_file, rj_file)
            
            # --- DASHBOARD METRICS ---
            st.markdown("#### 📊 Hasil Audit")
            m1, m2, m3 = st.columns(3)
            
            # Metrik 1: Total Pasien
            with m1:
                st.markdown(f"""
                <div class="custom-card">
                    <p class="metric-label">Total Data Diproses</p>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="metric-value">{len(df_ri) + len(df_rj):,}</span>
                        <span class="material-symbols-outlined" style="font-size:36px; color:#3b82f6;">dataset</span>
                    </div>
                    <div style="font-size:12px; color:#6b7280; margin-top:8px;">
                        RI: {len(df_ri):,} | RJ: {len(df_rj):,}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Metrik 2: Temuan Irisan
            with m2:
                warna_badge = "#ef4444" if len(hasil_irisan) > 0 else "#22c55e"
                status_icon = "warning" if len(hasil_irisan) > 0 else "check_circle"
                st.markdown(f"""
                <div class="custom-card" style="border: 1px solid {warna_badge};">
                    <p class="metric-label">Temuan Irisan</p>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="metric-value" style="color:{warna_badge}">{len(hasil_irisan):,}</span>
                        <span class="material-symbols-outlined" style="font-size:36px; color:{warna_badge};">{status_icon}</span>
                    </div>
                    <div style="font-size:12px; color:#6b7280; margin-top:8px;">
                        Kasus Ganda (Double Billing)
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            # Metrik 3: Status
            with m3:
                status_text = "PERLU PERBAIKAN" if len(hasil_irisan) > 0 else "SIAP KIRIM (CLEAN)"
                bg_color = "#fee2e2" if len(hasil_irisan) > 0 else "#dcfce7"
                text_color = "#991b1b" if len(hasil_irisan) > 0 else "#166534"
                
                st.markdown(f"""
                <div class="custom-card">
                    <p class="metric-label">Status File</p>
                    <div style="margin-top:10px;">
                        <span style="background:{bg_color}; color:{text_color}; padding:8px 16px; border-radius:8px; font-weight:700; font-size:14px;">
                            {status_text}
                        </span>
                    </div>
                    <div style="font-size:12px; color:#6b7280; margin-top:16px;">
                        Berdasarkan analisa hari ini
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # --- VISUALISASI CHART ---
            c_chart1, c_chart2 = st.columns([1, 2])
            
            with c_chart1:
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.markdown("**Komposisi Data**")
                
                # Data untuk Chart Donat
                labels = ['Clean', 'Irisan (Masalah)']
                values = [(len(df_ri) + len(df_rj)) - len(hasil_irisan), len(hasil_irisan)]
                colors = ['#3b82f6', '#ef4444']
                
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker=dict(colors=colors))])
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with c_chart2:
                # Tabel Preview
                if len(hasil_irisan) > 0:
                    st.warning(f"⚠️ Ditemukan {len(hasil_irisan)} Pasien Rawat Jalan yang berkunjung saat periode Rawat Inap!")
                    st.dataframe(hasil_irisan[['No_Kartu', 'Tgl_Pelayanan', 'Tgl_Masuk', 'Tgl_Keluar']].head(50), use_container_width=True)
                else:
                    st.success("✅ Tidak ada irisan ditemukan. Data Rawat Inap & Jalan aman.")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca file: {e}")
            st.info("Pastikan format kolom Excel/CSV sudah sesuai standar (Ada kolom 'No_Kartu', 'Tgl_Masuk', dll).")

else:
    # Tampilan Awal (Belum Upload)
    st.info("👋 Silakan upload file Data Rawat Inap & Rawat Jalan di atas untuk memulai audit.")
    
    # Dummy Preview (Agar UI terlihat)
    st.markdown("#### Preview Dashboard (Contoh Tampilan)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="custom-card"><h3 style="color:#e5e7eb">0</h3><p style="color:#9ca3af">Menunggu Data...</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="custom-card"><h3 style="color:#e5e7eb">0</h3><p style="color:#9ca3af">Menunggu Data...</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="custom-card"><h3 style="color:#e5e7eb">Ready</h3><p style="color:#9ca3af">Sistem Siap</p></div>', unsafe_allow_html=True)
