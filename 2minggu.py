import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import re
import itertools
from datetime import datetime
import uuid

# Page config
st.set_page_config(
    page_title="Analisis Volume Lalu Lintas - 2 Minggu",
    page_icon="🚦",
    layout="wide"
)

# Main header
st.title("🚦 Analisis Volume Lalu Lintas - 2 Minggu")
st.subheader("Estimasi & Analisis Distribusi Kendaraan Bulanan Berdasarkan 2 Minggu Sample")

# Penjelasan singkat
with st.expander("ℹ️ Cara Penggunaan Aplikasi", expanded=False):
    st.markdown("""
    **Langkah Penggunaan:**
    1. **Upload Data Minggu 1**: Unggah 7 file Excel (Minggu pertama) untuk menghitung proporsi kendaraan di 10 titik.
    2. **Upload Data Minggu 3**: Unggah 7 file Excel (Minggu ketiga) untuk melengkapi data proporsi.
    3. **Upload Data Bulanan**: Unggah 1 file Excel berisi volume kendaraan harian untuk keseluruhan bulan.
    4. **Hasil Estimasi**: Dapatkan distribusi volume kendaraan per titik berdasarkan rata-rata proporsi 2 minggu.
    5. **Analisis**: Lihat dashboard rekap harian dan bulanan untuk analisis lebih lanjut.

    **Keunggulan 2 Minggu:**
    - Data proporsi lebih akurat dan representatif
    - Menghindari bias dari data 1 minggu saja
    - Pola lalu lintas lebih stabil dan dapat diandalkan
    """)

# Konfigurasi global
NAMA_CHECKPOINT = [
    "diponegoro", "imam bonjol", "a yani", "gajah mada", "sudirman",
    "brantas", "patimura", "trunojoyo", "arumdalu", "mojorejo"
]

JENIS_MAP = {
    "Large-Sized Coach": "Bus",
    "Light Truck": "Truck", 
    "Minivan": "Roda 4",
    "Pedestrian": "Pejalan kaki",
    "Pick-up Truck": "Pick-up",
    "SUV/MPV": "Roda 4",
    "Sedan": "Roda 4",
    "Tricycle": "Tossa",
    "Truck": "Truck",
    "Two Wheeler": "Sepeda motor"
}

KETERANGAN_MAP = {
    "diponegoro": "Keluar Batu", "imam bonjol": "Batu", "a yani": "Batu", 
    "gajah mada": "Batu", "sudirman": "Keluar Batu", "brantas": "Masuk Batu",
    "patimura": "Masuk Batu", "trunojoyo": "Masuk Batu", 
    "arumdalu": "Masuk Batu", "mojorejo": "Masuk Batu"
}

JENIS_MAP_BULANAN = {
    "Truk": "Truck", "Light Truck": "Truck", "Bus": "Bus", "Pick up Truck": "Pick-up",
    "Sedan": "Roda 4", "Minivan": "Roda 4", "SUV/MPV": "Roda 4",
    "Roda 3": "Tossa", "Roda 2": "Sepeda motor", "Pedestrian": "Pejalan kaki", 
    "Unknown": "Unknown"
}

# Fungsi helper
def clean_sheet_advanced(df):
    """Fungsi untuk cleaning sheet dengan aturan:
    1. Hapus 3 baris pertama
    2. Baris pertama setelah hapus 3 baris = header kosong, isi dengan 'No' dan 'Jenis Kendaraan'
    3. Hapus dari baris 'Vehicle Type' sampai bawah
    """
    df_cleaned = df.iloc[3:].copy().reset_index(drop=True)
    
    vehicle_type_row = None
    for idx, row in df_cleaned.iterrows():
        for col in df_cleaned.columns:
            if 'vehicle type' in str(row[col]).strip().lower():
                vehicle_type_row = idx
                break
        if vehicle_type_row is not None:
            break
    
    if vehicle_type_row is not None:
        df_cleaned = df_cleaned.iloc[:vehicle_type_row].reset_index(drop=True)
    
    if len(df_cleaned) > 0 and len(df_cleaned.columns) >= 2:
        df_cleaned.iloc[0, 0] = 'No'
        df_cleaned.iloc[0, 1] = 'Jenis Kendaraan'
    
    return df_cleaned

def dedup_columns(cols):
    """Fungsi untuk rename header duplikat"""
    counts = {}
    new_cols = []
    for col in cols:
        if col not in counts:
            counts[col] = 1
            new_cols.append(col)
        else:
            counts[col] += 1
            new_cols.append(f"{col}.{counts[col]}")
    return new_cols

def process_weekly_data(uploaded_files, minggu_label):
    """Fungsi untuk memproses data mingguan"""
    
    if not uploaded_files or len(uploaded_files) != 7:
        st.error(f"❌ {minggu_label}: Harus mengunggah tepat 7 file!")
        return None
    
    df_mingguan_list = []
    sheet_warnings = []
    
    with st.spinner(f"🔄 Memproses data {minggu_label}..."):
        for uploaded_file in uploaded_files:
            nama_file = uploaded_file.name.lower()
            
            # Extract tanggal dari nama file
            match = re.search(r"(\d{1,2})[\s\-_]*(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)", nama_file, re.IGNORECASE)
            if not match:
                st.error(f"❌ Nama file tidak sesuai: {nama_file}. Gunakan format seperti 'tanggal 1 juli.xlsx'.")
                continue

            tanggal = int(match.group(1))
            bulan_str = match.group(2).lower()
            bulan_map = {
                "januari": 1, "februari": 2, "maret": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                "september": 9, "oktober": 10, "november": 11, "desember": 12
            }
            bulan = bulan_map.get(bulan_str, 7)
            tanggal_str = f"{tanggal:02d}-{bulan:02d}-2025"

            try:
                xls = pd.read_excel(uploaded_file, sheet_name=None, header=None)
                df_list = []
                
                for idx, (sheet_name, df) in enumerate(xls.items()):
                    if idx >= 10:  # Hanya proses 10 sheet pertama
                        break
                        
                    df_cleaned = clean_sheet_advanced(df)
                    if len(df_cleaned) <= 1:
                        sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} kosong")
                        continue
                    
                    # Buat header yang proper
                    header_row = df_cleaned.iloc[0].tolist()
                    df_proper = pd.DataFrame(df_cleaned.iloc[1:].values, columns=header_row)
                    
                    if 'Jenis Kendaraan' not in df_proper.columns:
                        sheet_warnings.append(f"Sheet {sheet_name} tidak memiliki kolom 'Jenis Kendaraan'")
                        continue
                    
                    # Identifikasi kolom jam
                    jam_cols = [col for col in df_proper.columns if ":" in str(col)]
                    if not jam_cols:
                        sheet_warnings.append(f"Sheet {sheet_name} tidak memiliki kolom jam")
                        continue
                    
                    # Konversi kolom jam ke numerik
                    for col in jam_cols:
                        df_proper[col] = pd.to_numeric(df_proper[col], errors='coerce').fillna(0)
                    
                    # Bersihkan data
                    df_proper = df_proper[df_proper['Jenis Kendaraan'].notna()]
                    df_proper = df_proper[~df_proper['Jenis Kendaraan'].str.lower().str.contains('total|sum', na=False)]
                    
                    # Tambahkan metadata
                    df_proper["Source"] = NAMA_CHECKPOINT[idx] if idx < len(NAMA_CHECKPOINT) else f"checkpoint_{idx+1}"
                    df_proper["Tanggal"] = tanggal_str
                    df_proper["Minggu"] = minggu_label
                    
                    df_list.append(df_proper)
                
                if df_list:
                    df_combined = pd.concat(df_list, ignore_index=True)
                    # Hapus baris dengan semua jam = 0
                    jam_cols = [col for col in df_combined.columns if ":" in str(col)]
                    df_combined = df_combined.loc[~(df_combined[jam_cols] == 0).all(axis=1)].copy()
                    df_mingguan_list.append(df_combined)
                
            except Exception as e:
                st.error(f"❌ Error memproses {nama_file}: {str(e)}")
                sheet_warnings.append(f"Error di {nama_file}: {str(e)}")
    
    if sheet_warnings:
        with st.expander(f"⚠️ Peringatan {minggu_label}", expanded=False):
            for warning in sheet_warnings:
                st.write(f"- {warning}")
    
    if df_mingguan_list:
        df_final = pd.concat(df_mingguan_list, ignore_index=True)
        
        # Mapping jenis kendaraan
        df_final["Jenis Kendaraan"] = df_final["Jenis Kendaraan"].replace(JENIS_MAP)
        df_final["Keterangan"] = df_final["Source"].map(KETERANGAN_MAP)
        
        # Konversi tanggal
        df_final["Tanggal"] = pd.to_datetime(df_final["Tanggal"], format='mixed', dayfirst=True)
        df_final["Hari"] = df_final["Tanggal"].dt.day_name()
        
        st.success(f"✅ {minggu_label} berhasil diproses: {len(df_final)} baris data")
        return df_final
    else:
        st.error(f"❌ {minggu_label}: Tidak ada data valid")
        return None

# STEP 1: UPLOAD DATA MINGGU 1
st.header("📁 Langkah 1: Unggah Data Minggu 1")
st.markdown("Unggah **7 file Excel** untuk minggu pertama (contoh: tanggal 1-7 Juli)")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("""
    **Ketentuan File Minggu 1:**
    - 7 file Excel, masing-masing untuk 1 hari dalam minggu pertama
    - Setiap file berisi **10 sheet** untuk 10 titik checkpoint  
    - Nama file: `tanggal X bulan.xlsx` (contoh: `tanggal 1 juli.xlsx`)
    """)
with col2:
    st.info("**10 Titik Checkpoint:**\n1. Diponegoro\n2. Imam Bonjol\n3. A Yani\n4. Gajah Mada\n5. Sudirman\n6. Brantas\n7. Patimura\n8. Trunojoyo\n9. Arumdalu\n10. Mojorejo")

uploaded_minggu1 = st.file_uploader(
    "📂 Unggah 7 File Excel (Minggu 1)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Unggah 7 file Excel untuk minggu pertama",
    key="minggu1_uploader"
)

# Progress indicator minggu 1
if uploaded_minggu1:
    file_count = len(uploaded_minggu1)
    col1, col2 = st.columns(2)
    with col1:
        if file_count == 7:
            st.success(f"✅ Minggu 1: {file_count}/7 file")
        elif file_count < 7:
            st.warning(f"⏳ Minggu 1: {file_count}/7 file")
        else:
            st.error(f"❌ Minggu 1: {file_count}/7 file (maksimal 7)")
    with col2:
        if file_count > 0:
            st.info(f"📋 File: {', '.join([f.name for f in uploaded_minggu1[:3]])}" + 
                    (f" +{file_count-3} lainnya" if file_count > 3 else ""))

# Process minggu 1
df_minggu1 = None
if uploaded_minggu1 and len(uploaded_minggu1) == 7:
    df_minggu1 = process_weekly_data(uploaded_minggu1, "Minggu1")

# STEP 2: UPLOAD DATA MINGGU 3
st.header("📁 Langkah 2: Unggah Data Minggu 3")  
st.markdown("Unggah **7 file Excel** untuk minggu ketiga (contoh: tanggal 15-21 Juli)")

uploaded_minggu3 = st.file_uploader(
    "📂 Unggah 7 File Excel (Minggu 3)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Unggah 7 file Excel untuk minggu ketiga",
    key="minggu3_uploader"
)

# Progress indicator minggu 3
if uploaded_minggu3:
    file_count = len(uploaded_minggu3)
    col1, col2 = st.columns(2)
    with col1:
        if file_count == 7:
            st.success(f"✅ Minggu 3: {file_count}/7 file")
        elif file_count < 7:
            st.warning(f"⏳ Minggu 3: {file_count}/7 file")
        else:
            st.error(f"❌ Minggu 3: {file_count}/7 file (maksimal 7)")
    with col2:
        if file_count > 0:
            st.info(f"📋 File: {', '.join([f.name for f in uploaded_minggu3[:3]])}" + 
                    (f" +{file_count-3} lainnya" if file_count > 3 else ""))

# Process minggu 3
df_minggu3 = None
if uploaded_minggu3 and len(uploaded_minggu3) == 7:
    df_minggu3 = process_weekly_data(uploaded_minggu3, "Minggu3")

# STEP 3: GABUNGKAN 2 MINGGU DAN HITUNG PROPORSI
if df_minggu1 is not None and df_minggu3 is not None:
    st.header("🔗 Langkah 3: Penggabungan Data 2 Minggu")
    
    with st.spinner("🔄 Menggabungkan data 2 minggu dan menghitung proporsi..."):
        # Gabungkan 2 minggu
        df_2minggu = pd.concat([df_minggu1, df_minggu3], ignore_index=True)
        
        # Identifikasi kolom jam
        jam_cols = [col for col in df_2minggu.columns if ":" in str(col)]
        
        # Hitung rata-rata per Hari + Jenis Kendaraan + Source
        df_avg_hari = (
            df_2minggu.groupby(["Hari", "Source", "Jenis Kendaraan", "Keterangan"], as_index=False)
            [jam_cols].mean()
        )
        
        # Tambahkan kolom Total per baris
        df_avg_hari["Total"] = df_avg_hari[jam_cols].sum(axis=1)
        
        # Hitung total per jenis kendaraan per hari
        total_per_jenis_per_hari = (
            df_avg_hari.groupby(["Hari", "Jenis Kendaraan"])["Total"]
            .sum().reset_index().rename(columns={"Total": "TotalJenis"})
        )
        
        # Gabungkan dan hitung proporsi
        df_proporsi = df_avg_hari.merge(total_per_jenis_per_hari, on=["Hari", "Jenis Kendaraan"])
        df_proporsi["Proporsi"] = df_proporsi["Total"] / df_proporsi["TotalJenis"]
        df_proporsi["Proporsi (%)"] = (df_proporsi["Proporsi"] * 100).round(2)
    
    st.success("🎉 Data 2 minggu berhasil digabungkan!")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Hari", df_proporsi['Hari'].nunique())
    with col2:
        st.metric("📍 Titik", df_proporsi['Source'].nunique())
    with col3:
        st.metric("🚗 Jenis", df_proporsi['Jenis Kendaraan'].nunique())
    with col4:
        st.metric("📊 Baris", len(df_proporsi))
    
    with st.expander("📊 Lihat Proporsi 2 Minggu", expanded=False):
        st.dataframe(df_proporsi, use_container_width=True)
        
        # Download proporsi
        output_proporsi = io.BytesIO()
        with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_2minggu")
            df_2minggu.to_excel(writer, index=False, sheet_name="data_2minggu_gabungan")
        
        st.download_button(
            "📥 Unduh Data Proporsi 2 Minggu", 
            data=output_proporsi.getvalue(), 
            file_name="proporsi_2minggu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

# STEP 4: UPLOAD DATA BULANAN
if 'df_proporsi' in locals():
    st.header("📊 Langkah 4: Unggah Data Volume Bulanan")
    st.markdown("Unggah **1 file Excel** berisi data volume kendaraan untuk keseluruhan bulan")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        **Ketentuan File Bulanan:**
        - 1 file Excel dengan sheet sesuai jumlah hari dalam bulan
        - Setiap sheet berisi total volume kendaraan per jenis dan jam
        - Nama sheet: 1, 2, 3, ..., dst (sesuai tanggal)
        """)
    with col2:
        st.info("**Format Sheet:**\n- Nama: 1, 2, ..., 31\n- Kolom: Jenis Kendaraan, 00:00 - 23:00\n- Data: Jumlah kendaraan")

    uploaded_bulanan = st.file_uploader(
        "📈 Unggah File Data Volume Bulanan (.xlsx)", 
        type=["xlsx"],
        help="File Excel berisi volume kendaraan bulanan"
    )

    # STEP 5: PROSES ESTIMASI
    if uploaded_bulanan:
        with st.spinner("🔄 Memproses estimasi volume bulanan berdasarkan proporsi 2 minggu..."):
            
            # Deteksi bulan dari nama file
            nama_file_bulanan = uploaded_bulanan.name.lower()
            match = re.search(r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)", nama_file_bulanan, re.IGNORECASE)
            bulan_map = {
                "januari": 1, "februari": 2, "maret": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                "september": 9, "oktober": 10, "november": 11, "desember": 12
            }
            bulan = 7
            if match and match.group(1).lower() in bulan_map:
                bulan = bulan_map[match.group(1).lower()]
                bulan_nama = match.group(1).title()
            else:
                bulan_nama = "Juli"
            
            # Baca semua sheet
            xls = pd.read_excel(uploaded_bulanan, sheet_name=None, header=None)
            list_df = []
            sheet_warnings = []
            
            processed_sheets = 0
            for sheet_name, df_raw in xls.items():
                try:
                    sheet_num = int(sheet_name)
                    if sheet_num < 1 or sheet_num > 31:
                        continue
                    
                    tanggal_str = f"{sheet_num:02d}-{bulan:02d}-2025"
                    
                    # Cari header "Jenis Kendaraan"
                    jenis_rows = df_raw[df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False)]
                    if jenis_rows.empty:
                        sheet_warnings.append(f"Sheet '{sheet_name}' tidak memiliki kolom 'Jenis Kendaraan'")
                        continue
                        
                    start_idx = jenis_rows.index[0] + 1
                    header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)
                    
                    # Handle duplikat header
                    if header_row.duplicated().any():
                        header_row = dedup_columns(header_row)

                    df_jenis = df_raw.iloc[start_idx:].copy()
                    df_jenis.columns = header_row

                    # Bersihkan data
                    mask_arah = df_jenis.apply(
                        lambda row: row.astype(str).str.contains(r"Arah|Keterangan|:", case=False, na=False).any(),
                        axis=1
                    )
                    df_jenis = df_jenis[~mask_arah]
                    df_jenis = df_jenis[df_jenis["Jenis Kendaraan"].notna()]
                    df_jenis = df_jenis[~df_jenis["Jenis Kendaraan"].astype(str).str.lower().str.contains("total|sum")]

                    df_jenis["Tanggal"] = tanggal_str
                    list_df.append(df_jenis)
                    processed_sheets += 1
                    
                except ValueError:
                    sheet_warnings.append(f"Sheet '{sheet_name}' diabaikan karena bukan angka")
                    continue
                except Exception as e:
                    sheet_warnings.append(f"Error di sheet '{sheet_name}': {str(e)}")
                    continue

            if sheet_warnings:
                with st.expander("⚠️ Peringatan Pemrosesan Data Bulanan", expanded=False):
                    for warning in sheet_warnings:
                        st.write(f"- {warning}")

            if not list_df:
                st.error("❌ Tidak ada data valid di file bulanan. Periksa format file.")
                st.stop()

            # Gabungkan semua sheet
            df_bulanan = pd.concat(list_df, ignore_index=True)
            
            # Set nama kolom jam
            jam_list = [f"{str(i).zfill(2)}:00:00" for i in range(24)]
            columns = list(df_bulanan.columns)
            
            if len(columns) >= 25:
                columns[1:25] = jam_list
                df_bulanan.columns = columns
                groupby_cols = jam_list.copy()
                if 'Total' in df_bulanan.columns:
                    groupby_cols.append('Total')
            else:
                st.error(f"❌ File bulanan memiliki {len(columns)} kolom, minimal 25 kolom diperlukan.")
                st.stop()

            # Mapping jenis kendaraan
            df_bulanan['Jenis Kendaraan'] = df_bulanan['Jenis Kendaraan'].map(JENIS_MAP_BULANAN)

            # Konversi ke numerik
            for col in jam_list:
                if col in df_bulanan.columns:
                    df_bulanan[col] = pd.to_numeric(df_bulanan[col], errors='coerce').fillna(0)
            
            if 'Total' in df_bulanan.columns:
                df_bulanan['Total'] = pd.to_numeric(df_bulanan['Total'], errors='coerce').fillna(0)
            
            # Groupby dan sum
            df_bulanan = df_bulanan.groupby(['Tanggal', 'Jenis Kendaraan'], as_index=False)[groupby_cols].sum()
            df_bulanan = df_bulanan.sort_values(by=['Tanggal', 'Jenis Kendaraan']).reset_index(drop=True)

            # Konversi tanggal dan tambah kolom Hari
            df_bulanan["Tanggal"] = pd.to_datetime(df_bulanan["Tanggal"], format='mixed', dayfirst=True)
            df_bulanan["Hari"] = df_bulanan["Tanggal"].dt.day_name()

            # Melt ke long format
            df_jenis_long = df_bulanan.melt(
                id_vars=["Tanggal", "Jenis Kendaraan", "Hari"],
                value_vars=jam_list,
                var_name="Jam",
                value_name="Jumlah"
            )
            
            df_jenis_long["Jumlah"] = pd.to_numeric(df_jenis_long["Jumlah"], errors='coerce').fillna(0)

            # Join dengan proporsi
            df_join = df_jenis_long.merge(
                df_proporsi[["Hari", "Source", "Jenis Kendaraan", "Proporsi"]], 
                on=["Hari", "Jenis Kendaraan"], 
                how="left"
            )

            # Hitung estimasi
            df_join["Jumlah_Estimasi"] = df_join["Jumlah"] * df_join["Proporsi"]

            # Pivot kembali ke wide format
            df_pivot = df_join.pivot_table(
                index=["Tanggal", "Jenis Kendaraan", "Source"],
                columns="Jam",
                values="Jumlah_Estimasi",
                aggfunc="sum"
            ).reset_index()

            # Bulatkan dan konversi ke integer
            jam_columns = [col for col in df_pivot.columns if col.endswith(":00:00")]
            df_pivot[jam_columns] = df_pivot[jam_columns].fillna(0).round().astype(int)

            # Format tanggal dan filter
            df_pivot["Tanggal"] = pd.to_datetime(df_pivot["Tanggal"], errors="coerce")
            df_final = df_pivot.sort_values(by=["Tanggal", "Source"])
            df_final["Tanggal"] = df_final["Tanggal"].dt.strftime("%d-%m-%Y")
            df_final = df_final[df_final["Jenis Kendaraan"].str.lower() != "unknown"]

        st.success("🎉 Estimasi volume kendaraan berhasil dihitung!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Total Baris", len(df_final))
        with col2:
            st.metric("📍 Titik", df_final['Source'].nunique())
        with col3:
            st.metric("🚗 Jenis", df_final['Jenis Kendaraan'].nunique())
        with col4:
            st.metric("📅 Hari", processed_sheets)

        # Quality check
        st.header("🔍 Kualitas Data")
        
        all_tanggal = df_final["Tanggal"].unique()
        all_source = df_final["Source"].unique()
        all_jenis = df_final["Jenis Kendaraan"].unique()
        
        full_combinations = pd.DataFrame(
            list(itertools.product(all_tanggal, all_source, all_jenis)),
            columns=["Tanggal", "Source", "Jenis Kendaraan"]
        )
        
        merged_check = full_combinations.merge(
            df_final[["Tanggal", "Source", "Jenis Kendaraan"]],
            on=["Tanggal", "Source", "Jenis Kendaraan"],
            how="left",
            indicator=True
        )
        
        missing_data = merged_check[merged_check["_merge"] == "left_only"].drop(columns=["_merge"])
        
        col1, col2, col3 = st.columns(3)
        completeness = ((len(full_combinations) - len(missing_data)) / len(full_combinations) * 100) if len(full_combinations) > 0 else 100
        
        with col1:
            if completeness == 100:
                st.success(f"✅ Kelengkapan Data: {completeness:.1f}%")
            elif completeness >= 90:
                st.warning(f"⚠️ Kelengkapan Data: {completeness:.1f}%")
            else:
                st.error(f"❌ Kelengkapan Data: {completeness:.1f}%")
        
        with col2:
            st.info(f"🎯 Data Lengkap: {len(full_combinations) - len(missing_data):,}")
        
        with col3:
            if len(missing_data) == 0:
                st.success("🎉 Tidak Ada Data Hilang!")
            else:
                st.error(f"⚠️ Data Hilang: {len(missing_data):,}")

        if len(missing_data) > 0:
            with st.expander("🔍 Detail Data Hilang", expanded=False):
                st.subheader("📋 Tabel Data Hilang per Titik")
                missing_summary = []
                for checkpoint in sorted(missing_data['Source'].unique()):
                    checkpoint_missing = missing_data[missing_data['Source'] == checkpoint]
                    unique_dates = sorted(checkpoint_missing['Tanggal'].unique())
                    
                    for date in unique_dates:
                        date_missing = checkpoint_missing[checkpoint_missing['Tanggal'] == date]
                        vehicles_missing = sorted(date_missing['Jenis Kendaraan'].unique())
                        
                        missing_summary.append({
                            'Titik': checkpoint,
                            'Tanggal': date,
                            'Jumlah Jenis Hilang': len(vehicles_missing),
                            'Jenis Kendaraan Hilang': ', '.join(vehicles_missing)
                        })
                
                if missing_summary:
                    df_missing_summary = pd.DataFrame(missing_summary)
                    st.dataframe(
                        df_missing_summary,
                        column_config={
                            "Titik": st.column_config.TextColumn("📍 Titik", width="medium"),
                            "Tanggal": st.column_config.TextColumn("📅 Tanggal", width="small"),
                            "Jumlah Jenis Hilang": st.column_config.NumberColumn("🔢 Jenis Hilang", width="small"),
                            "Jenis Kendaraan Hilang": st.column_config.TextColumn("🚗 Jenis Kendaraan", width="large")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    output_missing = io.BytesIO()
                    with pd.ExcelWriter(output_missing, engine='openpyxl') as writer:
                        missing_data.to_excel(writer, index=False, sheet_name="data_hilang_detail")
                        df_missing_summary.to_excel(writer, index=False, sheet_name="ringkasan_per_titik")
                    
                    st.download_button(
                        "📥 Unduh Analisis Data Hilang", 
                        data=output_missing.getvalue(), 
                        file_name="analisis_data_hilang.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        # HASIL AKHIR DAN DOWNLOAD
        st.header("📋 Hasil Estimasi Volume Kendaraan")
        
        with st.expander("👁️ Lihat Hasil Estimasi (20 Baris Pertama)", expanded=True):
            st.dataframe(df_final.head(20), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            output_final = io.BytesIO()
            with pd.ExcelWriter(output_final, engine="openpyxl") as writer:
                df_final.to_excel(writer, index=False, sheet_name="estimasi_final")
                df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_2minggu")
                df_2minggu.to_excel(writer, index=False, sheet_name="data_2minggu_gabungan")
                if len(missing_data) > 0:
                    missing_data.to_excel(writer, index=False, sheet_name="data_hilang")
            
            st.download_button(
                "🎉 Unduh Hasil Lengkap", 
                data=output_final.getvalue(), 
                file_name=f"estimasi_volume_lalu_lintas_{bulan_nama}_2minggu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        
        with col2:
            output_proporsi = io.BytesIO()
            with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
                df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_2minggu")
            
            st.download_button(
                "📊 Unduh Proporsi 2 Minggu", 
                data=output_proporsi.getvalue(), 
                file_name=f"proporsi_2minggu_{bulan_nama}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # DASHBOARD ANALISIS
        st.header("📊 Dashboard Analisis Lalu Lintas")

        @st.cache_data
        def prepare_dashboard_data(df):
            df = df.copy()
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], format='mixed', dayfirst=True, errors='coerce')
            df["Hari"] = df["Tanggal"].dt.day_name()
            df["Keterangan"] = df["Source"].map(KETERANGAN_MAP)
            return df

        df_dashboard = prepare_dashboard_data(df_final)
        jam_cols_dashboard = [col for col in df_dashboard.columns if col.endswith(":00:00")]

        tab1, tab2, tab3 = st.tabs(["📅 Rekap Harian", "📆 Rekap Bulanan", "📈 Analisis 2 Minggu"])

        with tab1:
            st.header("📅 Rekap Harian")
            col1, col2 = st.columns([1, 2])
            with col1:
                tanggal_terpilih = st.date_input(
                    "Pilih Tanggal", 
                    df_dashboard["Tanggal"].min(), 
                    min_value=df_dashboard["Tanggal"].min(),
                    max_value=df_dashboard["Tanggal"].max(),
                    key="daily_date_select"
                )
            with col2:
                source_terpilih = st.selectbox(
                    "Pilih Lokasi", 
                    sorted(df_dashboard["Source"].unique()), 
                    key="daily_location_select"
                )

            df_filtered = df_dashboard[
                (df_dashboard["Tanggal"] == pd.to_datetime(tanggal_terpilih)) & 
                (df_dashboard["Source"] == source_terpilih)
            ]

            if df_filtered.empty:
                st.warning("⚠️ Tidak ada data untuk tanggal dan lokasi yang dipilih.")
            else:
                st.subheader(f"Rekap **{source_terpilih}** - {tanggal_terpilih.strftime('%A, %d %B %Y')}")
                
                df_melted = df_filtered.melt(
                    id_vars=["Tanggal", "Source", "Jenis Kendaraan"], 
                    value_vars=jam_cols_dashboard,
                    var_name="Jam", 
                    value_name="Jumlah"
                )

                total_per_kendaraan = df_melted.groupby("Jenis Kendaraan")["Jumlah"].sum().reset_index()
                total_per_kendaraan["Persen"] = (
                    total_per_kendaraan["Jumlah"] / total_per_kendaraan["Jumlah"].sum() * 100
                ).round(2)
                total_per_kendaraan = total_per_kendaraan.sort_values(by="Jumlah", ascending=False)

                # Metrics harian
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🚗 Total Kendaraan", f"{int(total_per_kendaraan['Jumlah'].sum()):,}")
                with col2:
                    if len(total_per_kendaraan) > 0:
                        top_vehicle = total_per_kendaraan.iloc[0]
                        st.metric("🥇 Kendaraan Terbanyak", f"{top_vehicle['Jenis Kendaraan']}")
                with col3:
                    if len(total_per_kendaraan) > 0:
                        top_vehicle = total_per_kendaraan.iloc[0]
                        st.metric("📊 Persentase Tertinggi", f"{top_vehicle['Persen']}%")

                col1, col2 = st.columns([1.2, 1])
                with col1:
                    st.subheader("📄 Data Jenis Kendaraan")
                    st.dataframe(total_per_kendaraan, use_container_width=True)

                with col2:
                    st.subheader("📊 Diagram Jenis Kendaraan")
                    fig1, ax1 = plt.subplots(figsize=(8, 8))
                    
                    wedges, texts = ax1.pie(
                        total_per_kendaraan["Jumlah"],
                        labels=None,
                        startangle=90,
                        counterclock=False,
                        colors=sns.color_palette("Set3", len(total_per_kendaraan))
                    )
                    ax1.axis('equal')

                    legend_labels = [
                        f"{jenis} ({persen}%)" 
                        for jenis, persen in zip(
                            total_per_kendaraan["Jenis Kendaraan"], 
                            total_per_kendaraan["Persen"]
                        )
                    ]
                    ax1.legend(
                        wedges,
                        legend_labels,
                        title="Jenis Kendaraan",
                        loc="center left",
                        bbox_to_anchor=(1, 0, 0.5, 1),
                        frameon=False,
                        fontsize=9
                    )
                    st.pyplot(fig1)

                st.markdown("---")
                st.subheader("📈 Pola Waktu Kendaraan")
                kendaraan_pilih = st.selectbox(
                    "Pilih Jenis Kendaraan", 
                    total_per_kendaraan["Jenis Kendaraan"], 
                    key="daily_vehicle_select"
                )
                df_jam = df_melted[df_melted["Jenis Kendaraan"] == kendaraan_pilih]

                fig2, ax2 = plt.subplots(figsize=(15, 6))
                sns.barplot(data=df_jam, x="Jam", y="Jumlah", ax=ax2, palette="viridis")
                ax2.set_title(f"Distribusi Waktu - {kendaraan_pilih}", fontsize=14, fontweight='bold')
                ax2.set_ylabel("Jumlah Kendaraan")
                ax2.set_xlabel("Jam")
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig2)

                st.markdown("---")
                st.subheader("📦 Total Kendaraan Masuk/Keluar Batu")
                df_tanggal = df_dashboard[df_dashboard["Tanggal"] == pd.to_datetime(tanggal_terpilih)]
                total_by_keterangan = (
                    df_tanggal
                    .melt(id_vars=["Keterangan"], value_vars=jam_cols_dashboard, value_name="Jumlah")
                    .groupby("Keterangan")["Jumlah"]
                    .sum()
                    .reset_index()
                )

                col1, col2 = st.columns(2)
                for idx, (_, row) in enumerate(total_by_keterangan.iterrows()):
                    with col1 if idx % 2 == 0 else col2:
                        st.metric(f"🚦 {row['Keterangan']}", f"{int(row['Jumlah']):,} kendaraan")

        with tab2:
            st.header("📆 Rekap Bulanan")
            selected_month = st.selectbox(
                "Pilih Bulan", 
                sorted(df_dashboard["Tanggal"].dt.strftime("%B %Y").unique()),
                key="monthly_month_select"
            )
            month_filter = df_dashboard["Tanggal"].dt.strftime("%B %Y") == selected_month
            df_bulanan_view = df_dashboard[month_filter]

            if df_bulanan_view.empty:
                st.warning("⚠️ Tidak ada data untuk bulan yang dipilih.")
            else:
                df_melted_bulan = df_bulanan_view.melt(
                    id_vars=["Source", "Jenis Kendaraan", "Keterangan"], 
                    value_vars=jam_cols_dashboard,
                    var_name="Jam", 
                    value_name="Jumlah"
                )
                grouped = df_melted_bulan.groupby(["Source", "Jenis Kendaraan", "Keterangan"])["Jumlah"].sum().reset_index()

                lokasi_terpilih = st.selectbox(
                    "Pilih Lokasi", 
                    sorted(grouped["Source"].unique()), 
                    key="monthly_location_select"
                )
                df_source = grouped[grouped["Source"] == lokasi_terpilih]
                df_source["Persen"] = (df_source["Jumlah"] / df_source["Jumlah"].sum() * 100).round(2)
                
                total_kendaraan_bulan = df_source["Jumlah"].sum()
                
                # Metrics bulanan
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🚗 Total Kendaraan Bulan", f"{int(total_kendaraan_bulan):,}")
                with col2:
                    if len(df_source) > 0:
                        top_vehicle_month = df_source.nlargest(1, "Jumlah").iloc[0]
                        st.metric("🥇 Kendaraan Terbanyak", f"{top_vehicle_month['Jenis Kendaraan']}")
                with col3:
                    keterangan_lokasi = df_source["Keterangan"].iloc[0] if len(df_source) > 0 else "N/A"
                    st.metric("📍 Arah", keterangan_lokasi)

                col1, col2 = st.columns([1.2, 1])
                with col1:
                    st.subheader("📄 Data Jenis Kendaraan")
                    st.dataframe(df_source[["Jenis Kendaraan", "Jumlah", "Persen"]].sort_values("Jumlah", ascending=False), use_container_width=True)

                with col2:
                    st.subheader(f"📊 Diagram - {lokasi_terpilih}")
                    fig3, ax3 = plt.subplots(figsize=(8, 8))
                    
                    wedges, texts = ax3.pie(
                        df_source["Jumlah"],
                        labels=None,
                        startangle=90,
                        counterclock=False,
                        colors=sns.color_palette("Set2", len(df_source))
                    )
                    ax3.axis('equal')

                    legend_labels = [
                        f"{jenis} ({persen}%)" 
                        for jenis, persen in zip(df_source["Jenis Kendaraan"], df_source["Persen"])
                    ]
                    ax3.legend(
                        wedges,
                        legend_labels,
                        title="Jenis Kendaraan",
                        loc="center left",
                        bbox_to_anchor=(1, 0, 0.5, 1),
                        frameon=False,
                        fontsize=9
                    )
                    st.pyplot(fig3)

                st.markdown("---")
                st.subheader("📊 Perbandingan Antar Lokasi")
                df_all_locations = grouped.groupby(["Source", "Keterangan"])["Jumlah"].sum().reset_index()
                df_all_locations = df_all_locations.sort_values("Jumlah", ascending=True)

                fig4, ax4 = plt.subplots(figsize=(12, 8))
                bars = sns.barplot(
                    data=df_all_locations, 
                    y="Source", 
                    x="Jumlah", 
                    hue="Keterangan",
                    ax=ax4, 
                    palette="Set1"
                )
                ax4.set_title(f"Total Kendaraan per Lokasi - {selected_month}", fontsize=14, fontweight='bold')
                ax4.set_xlabel("Jumlah Kendaraan")
                ax4.set_ylabel("Lokasi")
                
                # Add value labels on bars
                for container in ax4.containers:
                    ax4.bar_label(container, fmt='%,.0f', padding=3)
                    
                plt.tight_layout()
                st.pyplot(fig4)

        with tab3:
            st.header("📈 Analisis Data 2 Minggu")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Ringkasan Proporsi")
                proporsi_summary = df_proporsi.groupby(["Source", "Keterangan"])["Proporsi"].mean().reset_index()
                proporsi_summary["Proporsi (%)"] = (proporsi_summary["Proporsi"] * 100).round(2)
                proporsi_summary = proporsi_summary.sort_values("Proporsi", ascending=False)
                
                st.dataframe(
                    proporsi_summary,
                    column_config={
                        "Source": st.column_config.TextColumn("📍 Lokasi"),
                        "Keterangan": st.column_config.TextColumn("🚦 Arah"),
                        "Proporsi (%)": st.column_config.NumberColumn("📊 Proporsi (%)", format="%.2f%%")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            
            with col2:
                st.subheader("🎯 Lokasi Terpadat")
                top_locations = proporsi_summary.head(5)
                
                for idx, row in top_locations.iterrows():
                    st.metric(
                        f"#{idx+1} {row['Source']}", 
                        f"{row['Proporsi (%)']:.2f}%",
                        delta=f"{row['Keterangan']}"
                    )

            st.markdown("---")
            st.subheader("📈 Distribusi Proporsi per Hari")
            
            hari_pilihan = st.selectbox(
                "Pilih Hari untuk Analisis", 
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                key="weekly_day_select"
            )
            
            df_hari = df_proporsi[df_proporsi["Hari"] == hari_pilihan]
            if not df_hari.empty:
                df_hari_grouped = df_hari.groupby(["Source", "Keterangan"])["Proporsi (%)"].mean().reset_index()
                df_hari_grouped = df_hari_grouped.sort_values("Proporsi (%)", ascending=True)
                
                fig5, ax5 = plt.subplots(figsize=(12, 8))
                bars = sns.barplot(
                    data=df_hari_grouped, 
                    y="Source", 
                    x="Proporsi (%)",
                    hue="Keterangan",
                    ax=ax5, 
                    palette="coolwarm"
                )
                ax5.set_title(f"Proporsi Kendaraan per Lokasi - Hari {hari_pilihan}", fontsize=14, fontweight='bold')
                ax5.set_xlabel("Proporsi (%)")
                ax5.set_ylabel("Lokasi")
                
                for container in ax5.containers:
                    ax5.bar_label(container, fmt='%.1f%%', padding=3)
                    
                plt.tight_layout()
                st.pyplot(fig5)
            else:
                st.warning(f"⚠️ Tidak ada data untuk hari {hari_pilihan}")

        # RINGKASAN AKHIR
        st.header("📋 Ringkasan Analisis")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "📅 Total Hari Dianalisis", 
                df_final['Tanggal'].nunique(),
                delta=f"Bulan {bulan_nama}"
            )
        with col2:
            st.metric(
                "📍 Titik Monitoring", 
                df_final['Source'].nunique(),
                delta="10 Checkpoint"
            )
        with col3:
            st.metric(
                "🚗 Jenis Kendaraan", 
                df_final['Jenis Kendaraan'].nunique(),
                delta="Semua kategori"
            )
        with col4:
            total_estimasi = 0
            for col in jam_columns:
                if col in df_final.columns:
                    total_estimasi += df_final[col].sum()
            st.metric(
                "🚦 Total Estimasi", 
                f"{total_estimasi:,.0f}",
                delta="Kendaraan/bulan"
            )

        # Info final
        st.info(f"""
        🎯 **Analisis Selesai!** 
        
        Estimasi volume lalu lintas telah dihitung berdasarkan:
        - **Proporsi dari 2 minggu sample data** (Minggu 1 & Minggu 3)
        - **Data volume bulanan {bulan_nama}** ({processed_sheets} hari)
        - **10 titik checkpoint** dengan arah masuk/keluar Batu
        
        📊 Tingkat kelengkapan data: **{completeness:.1f}%**
        """)

elif uploaded_minggu1 and uploaded_minggu3:
    st.warning("⚠️ Silakan unggah data volume bulanan untuk melanjutkan estimasi!")
elif uploaded_minggu1:
    st.warning("⚠️ Silakan unggah data Minggu 3 untuk melengkapi proporsi!")
else:
    st.info("📝 Silakan mulai dengan mengunggah data Minggu 1 (7 file Excel)")