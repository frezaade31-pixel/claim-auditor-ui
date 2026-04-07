import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import hashlib
import json
import os
import io

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="MediGuard Claim Auditor - RSPAD",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SISTEM AUTENTIKASI ---
USER_DB_FILE = "users.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load user database dari file JSON. Buat default superadmin jika belum ada."""
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    # Default users
    default_users = {
        "superadmin": {
            "password": hash_password("admin123"),
            "role": "superadmin",
            "nama": "Super Administrator"
        },
        "admin": {
            "password": hash_password("admin123"),
            "role": "admin",
            "nama": "Administrator"
        },
        "user": {
            "password": hash_password("user123"),
            "role": "user",
            "nama": "User Biasa"
        }
    }
    save_users(default_users)
    return default_users

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

def authenticate(username, password):
    users = load_users()
    if username in users and users[username]["password"] == hash_password(password):
        return users[username]
    return None

# Inisialisasi session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "user_nama" not in st.session_state:
    st.session_state.user_nama = None
if "active_page" not in st.session_state:
    st.session_state.active_page = "dashboard"

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

    /* Login Form */
    .login-container {
        max-width: 420px;
        margin: 60px auto;
        background: white;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }
    .login-title { font-size: 24px; font-weight: 800; color: #111827; text-align: center; margin-bottom: 8px; }
    .login-subtitle { font-size: 14px; color: #6b7280; text-align: center; margin-bottom: 24px; }

    /* Role Badge */
    .role-superadmin { background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .role-admin { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .role-user { background: #e5e7eb; color: #374151; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- HALAMAN LOGIN ---
def show_login_page():
    st.markdown("""
    <div class="login-container">
        <div class="login-title">🏥 MediGuard</div>
        <div class="login-subtitle">Claim Auditor System — RSPAD Gatot Soebroto</div>
    </div>
    """, unsafe_allow_html=True)

    col_space1, col_form, col_space2 = st.columns([1, 1.5, 1])
    with col_form:
        with st.form("login_form"):
            st.markdown("##### Masuk ke Akun Anda")
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Username dan password harus diisi!")
                else:
                    user_data = authenticate(username, password)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_role = user_data["role"]
                        st.session_state.user_nama = user_data["nama"]
                        st.session_state.active_page = "dashboard"
                        st.rerun()
                    else:
                        st.error("Username atau password salah!")

        st.markdown("""
        <div style="text-align:center; color:#9ca3af; font-size:12px; margin-top:16px;">
            Default Superadmin: <b>superadmin</b> / <b>admin123</b>
        </div>
        """, unsafe_allow_html=True)

# --- HALAMAN ADMIN PANEL (SUPERADMIN ONLY) ---
def show_admin_panel():
    st.markdown("### ⚙️ Admin Panel — Manajemen User")
    st.markdown("---")

    users = load_users()

    # Tabel User
    st.markdown("#### 👥 Daftar User")
    user_data_list = []
    for uname, udata in users.items():
        user_data_list.append({
            "Username": uname,
            "Nama": udata["nama"],
            "Role": udata["role"],
        })
    st.dataframe(pd.DataFrame(user_data_list), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Tambah User Baru
    st.markdown("#### ➕ Tambah User Baru")
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        new_username = col1.text_input("Username Baru")
        new_nama = col2.text_input("Nama Lengkap")
        col3, col4 = st.columns(2)
        new_password = col3.text_input("Password", type="password")
        new_role = col4.selectbox("Role", ["user", "admin", "superadmin"])
        add_submitted = st.form_submit_button("Tambah User", use_container_width=True)

        if add_submitted:
            if not new_username or not new_password or not new_nama:
                st.error("Semua field harus diisi!")
            elif new_username in users:
                st.error(f"Username '{new_username}' sudah ada!")
            else:
                users[new_username] = {
                    "password": hash_password(new_password),
                    "role": new_role,
                    "nama": new_nama
                }
                save_users(users)
                st.success(f"User '{new_username}' berhasil ditambahkan!")
                st.rerun()

    st.markdown("---")

    # Hapus User
    st.markdown("#### 🗑️ Hapus User")
    deletable_users = [u for u in users.keys() if u != st.session_state.username]
    if deletable_users:
        with st.form("delete_user_form"):
            del_user = st.selectbox("Pilih User untuk Dihapus", deletable_users)
            del_submitted = st.form_submit_button("Hapus User", use_container_width=True)
            if del_submitted:
                del users[del_user]
                save_users(users)
                st.success(f"User '{del_user}' berhasil dihapus!")
                st.rerun()
    else:
        st.info("Tidak ada user lain yang bisa dihapus.")

    st.markdown("---")

    # Reset Password
    st.markdown("#### 🔑 Reset Password User")
    with st.form("reset_pw_form"):
        reset_user = st.selectbox("Pilih User", list(users.keys()))
        reset_pw = st.text_input("Password Baru", type="password")
        reset_submitted = st.form_submit_button("Reset Password", use_container_width=True)
        if reset_submitted:
            if not reset_pw:
                st.error("Password baru harus diisi!")
            else:
                users[reset_user]["password"] = hash_password(reset_pw)
                save_users(users)
                st.success(f"Password untuk '{reset_user}' berhasil direset!")

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

# Cek Autentikasi: Tampilkan login jika belum login
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# --- SIDEBAR (SETELAH LOGIN) ---
with st.sidebar:
    role_class = f"role-{st.session_state.user_role}"
    st.markdown(f"""
    <div style="padding: 16px 0;">
        <div style="font-weight: 700; font-size: 16px;">👤 {st.session_state.user_nama}</div>
        <div style="margin-top: 4px;">
            <span class="{role_class}">{st.session_state.user_role}</span>
        </div>
        <div style="font-size: 12px; color: #9ca3af; margin-top: 4px;">@{st.session_state.username}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### Menu")

    if st.button("📊 Dashboard Audit", use_container_width=True):
        st.session_state.active_page = "dashboard"
        st.rerun()

    if st.session_state.user_role == "superadmin":
        if st.button("⚙️ Admin Panel", use_container_width=True):
            st.session_state.active_page = "admin"
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_nama = None
        st.session_state.active_page = "dashboard"
        st.rerun()

# --- ROUTING HALAMAN ---
if st.session_state.active_page == "admin" and st.session_state.user_role == "superadmin":
    show_admin_panel()
    st.stop()

# --- HALAMAN DASHBOARD (DEFAULT) ---

# Header Section
c1, c2 = st.columns([8, 2])
with c1:
    st.markdown("### 🏥 MediGuard Claim Auditor")
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
