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
    page_title="Analisis Volume Lalu Lintas",
    page_icon="🚦",
    layout="wide"
)

# Main header
st.title("🚦 Analisis Volume Lalu Lintas")
st.subheader("Estimasi & Analisis Distribusi Kendaraan Bulanan")

# Penjelasan singkat
with st.expander("ℹ️ Cara Penggunaan Aplikasi", expanded=False):
    st.markdown("""
    **Langkah Penggunaan:**
    1. **Upload Data Mingguan**: Unggah 7 file Excel (Senin-Minggu) untuk menghitung proporsi kendaraan di 10 titik.
    2. **Upload Data Bulanan**: Unggah 1 file Excel berisi volume kendaraan harian (1-31 Juli).
    3. **Hasil Estimasi**: Dapatkan distribusi volume kendaraan per titik berdasarkan proporsi mingguan.
    4. **Analisis**: Lihat dashboard rekap harian dan bulanan untuk analisis lebih lanjut.

    **Contoh:**
    - Data mingguan: Titik Diponegoro = 15%, Imam Bonjol = 20%, dst.
    - Data bulanan: Total 400 mobil pada 1 Juli.
    - Hasil: Diponegoro = 60 mobil, Imam Bonjol = 80 mobil, dst.
    """)

# Fungsi untuk cleaning sheet
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

# STEP 1: UPLOAD DATA MINGGUAN
st.header("📁 Langkah 1: Unggah Data Mingguan")
st.markdown("Unggah **7 file Excel** untuk data mingguan (Senin-Minggu). Pastikan nama file seperti `tanggal 1 juli.xlsx` hingga `tanggal 7 juli.xlsx`.")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("""
    **Ketentuan File:**
    - 7 file Excel, masing-masing untuk 1 hari (Senin-Minggu).
    - Setiap file berisi **10 sheet** untuk 10 titik checkpoint.
    - Data akan dibersihkan otomatis (header dan footer dihapus).
    """)
with col2:
    st.info("**10 Titik Checkpoint:**\n1. Diponegoro\n2. Imam Bonjol\n3. A Yani\n4. Gajah Mada\n5. Sudirman\n6. Brantas\n7. Patimura\n8. Trunojoyo\n9. Arumdalu\n10. Mojorejo")

uploaded_files = st.file_uploader(
    "📂 Unggah 7 File Excel (Data Mingguan)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Unggah 7 file Excel untuk Senin-Minggu"
)

# Progress indicator
if uploaded_files:
    file_count = len(uploaded_files)
    col1, col2 = st.columns(2)
    with col1:
        if file_count == 7:
            st.success(f"✅ {file_count}/7 file berhasil diunggah")
        elif file_count < 7:
            st.warning(f"⏳ {file_count}/7 file diunggah. Tambah {7-file_count} file lagi.")
        else:
            st.error(f"❌ {file_count}/7 file. Hanya 7 file yang diperbolehkan!")
    with col2:
        if file_count > 0:
            st.info(f"📋 File: {', '.join([f.name for f in uploaded_files[:3]])}" + 
                    (f" +{file_count-3} lainnya" if file_count > 3 else ""))

# Process weekly data
if uploaded_files and len(uploaded_files) == 7:
    with st.spinner("🔄 Memproses data mingguan..."):
        nama_checkpoint = [
            "diponegoro", "imam bonjol", "a yani", "gajah mada", "sudirman",
            "brantas", "patimura", "trunojoyo", "arumdalu", "mojorejo"
        ]
        df_mingguan_list = []
        sheet_warnings = []

        for uploaded_file in uploaded_files:
            nama_file = uploaded_file.name.lower()
            match = re.search(r"(\d{1,2})[\s\-_]*(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)", nama_file, re.IGNORECASE)
            if not match:
                st.error(f"❌ Nama file tidak sesuai: {nama_file}. Gunakan format seperti 'tanggal 1 juli.xlsx'.")
                sheet_warnings.append(f"Nama file tidak sesuai: {nama_file}")
                continue

            tanggal = int(match.group(1))
            bulan_str = match.group(2).lower()
            bulan_map = {
                "januari": 1, "februari": 2, "maret": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                "september": 9, "oktober": 10, "november": 11, "desember": 12
            }
            if bulan_str not in bulan_map:
                st.error(f"❌ Bulan tidak dikenali: {bulan_str} di {nama_file}")
                sheet_warnings.append(f"Bulan tidak dikenali: {bulan_str} di {nama_file}")
                continue
            bulan = bulan_map[bulan_str]
            tanggal_str = f"{tanggal:02d}-{bulan:02d}-2025"

            xls = pd.read_excel(uploaded_file, sheet_name=None, header=None)
            df_list = []
            for idx, (sheet_name, df) in enumerate(xls.items()):
                sheet_name_lower = sheet_name.lower()
                expected_sheet = f"{idx+1}. {tanggal} {bulan_str}"
                
                if sheet_name_lower == expected_sheet.lower():
                    df_cleaned = clean_sheet_advanced(df)
                    if len(df_cleaned) <= 1:
                        sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} kosong setelah pembersihan")
                        continue
                    
                    header_row = df_cleaned.iloc[0].tolist()
                    df_proper = pd.DataFrame(df_cleaned.iloc[1:].values, columns=header_row)
                    
                    if 'Jenis Kendaraan' not in df_proper.columns:
                        sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} tidak memiliki kolom 'Jenis Kendaraan'")
                        continue
                    
                    jam_cols = [col for col in df_proper.columns if ":" in str(col)]
                    if not jam_cols:
                        sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} tidak memiliki kolom jam")
                        continue
                    
                    for col in jam_cols:
                        df_proper[col] = pd.to_numeric(df_proper[col], errors='coerce').fillna(0)
                    
                    df_proper = df_proper[df_proper['Jenis Kendaraan'].notna()]
                    df_proper = df_proper[~df_proper['Jenis Kendaraan'].str.lower().str.contains('total|sum', na=False)]
                    
                    df_proper["Source"] = nama_checkpoint[idx]
                    df_proper["Tanggal"] = tanggal_str
                    df_list.append(df_proper)
                else:
                    sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} diabaikan (diharapkan {expected_sheet})")
                    if idx < len(nama_checkpoint):
                        df_cleaned = clean_sheet_advanced(df)
                        if len(df_cleaned) <= 1:
                            sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} kosong setelah pembersihan")
                            continue
                        
                        header_row = df_cleaned.iloc[0].tolist()
                        df_proper = pd.DataFrame(df_cleaned.iloc[1:].values, columns=header_row)
                        
                        if 'Jenis Kendaraan' not in df_proper.columns:
                            sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} tidak memiliki kolom 'Jenis Kendaraan'")
                            continue
                        
                        jam_cols = [col for col in df_proper.columns if ":" in str(col)]
                        if not jam_cols:
                            sheet_warnings.append(f"Sheet {sheet_name} di {nama_file} tidak memiliki kolom jam")
                            continue
                        
                        for col in jam_cols:
                            df_proper[col] = pd.to_numeric(df_proper[col], errors='coerce').fillna(0)
                        
                        df_proper = df_proper[df_proper['Jenis Kendaraan'].notna()]
                        df_proper = df_proper[~df_proper['Jenis Kendaraan'].str.lower().str.contains('total|sum', na=False)]
                        
                        df_proper["Source"] = nama_checkpoint[idx]
                        df_proper["Tanggal"] = tanggal_str
                        df_list.append(df_proper)

            if df_list:
                df_final = pd.concat(df_list, ignore_index=True)
                jam_cols = [col for col in df_final.columns if ":" in str(col)]
                if not jam_cols:
                    st.error(f"❌ Tidak ditemukan kolom jam di {nama_file}!")
                    sheet_warnings.append(f"Tidak ditemukan kolom jam di {nama_file}")
                    continue
                df_final = df_final.loc[~(df_final[jam_cols] == 0).all(axis=1)].copy()
                df_mingguan_list.append(df_final)
            else:
                st.error(f"❌ Tidak ada data valid di {nama_file}")
                sheet_warnings.append(f"Tidak ada data valid di {nama_file}")

        if sheet_warnings:
            with st.expander("⚠️ Peringatan Pemrosesan Data Mingguan", expanded=False):
                st.write("**Peringatan:**")
                for warning in sheet_warnings:
                    st.write(f"- {warning}")

        if df_mingguan_list:
            df_mingguan = pd.concat(df_mingguan_list, ignore_index=True)
            
            with st.expander("👁️ Lihat Data Mingguan (20 Baris Pertama)", expanded=False):
                st.write("Data setelah pembersihan:")
                st.dataframe(df_mingguan.head(20), use_container_width=True)
            
            jenis_map = {
                "Large-Sized Coach": "Bus", "Light Truck": "Truck", "Minivan": "Roda 4",
                "Pedestrian": "Pejalan kaki", "Pick-up Truck": "Pick-up", "SUV/MPV": "Roda 4",
                "Sedan": "Roda 4", "Tricycle": "Tossa", "Truck": "Truck", "Two Wheeler": "Sepeda motor"
            }
            df_mingguan["Jenis Kendaraan"] = df_mingguan["Jenis Kendaraan"].replace(jenis_map)

            keterangan_map = {
                "diponegoro": "Keluar Batu", "imam bonjol": "Batu", "a yani": "Batu", "gajah mada": "Batu",
                "sudirman": "Keluar Batu", "brantas": "Masuk Batu", "patimura": "Masuk Batu",
                "trunojoyo": "Masuk Batu", "arumdalu": "Masuk Batu", "mojorejo": "Masuk Batu"
            }
            df_mingguan["Keterangan"] = df_mingguan["Source"].map(keterangan_map)

            jam_cols = [col for col in df_mingguan.columns if ":" in str(col)]
            kolom_awal = ["Source", "Jenis Kendaraan", "Tanggal", "Keterangan"]
            for col in jam_cols:
                df_mingguan[col] = pd.to_numeric(df_mingguan[col], errors='coerce').fillna(0)
            
            df_grouped = df_mingguan.groupby(kolom_awal, as_index=False)[jam_cols].sum()
            
            df_grouped["Tanggal"] = pd.to_datetime(df_grouped["Tanggal"], format='mixed', dayfirst=True)
            df_grouped["Hari"] = df_grouped["Tanggal"].dt.day_name()
            df_grouped["Total"] = df_grouped[jam_cols].sum(axis=1)

            grouped_proporsi = df_grouped.groupby(["Hari", "Source", "Jenis Kendaraan"])["Total"].sum().reset_index()
            total_per_jenis_per_hari = (
                grouped_proporsi.groupby(["Hari", "Jenis Kendaraan"])["Total"]
                .sum().reset_index().rename(columns={"Total": "TotalJenis"})
            )
            
            df_proporsi = grouped_proporsi.merge(total_per_jenis_per_hari, on=["Hari", "Jenis Kendaraan"])
            df_proporsi["Proporsi"] = df_proporsi["Total"] / df_proporsi["TotalJenis"]
            df_proporsi["Proporsi"] = pd.to_numeric(df_proporsi["Proporsi"], errors='coerce').fillna(0)
            df_proporsi["Proporsi (%)"] = (df_proporsi["Proporsi"] * 100).round(2)

            st.success("✅ Data mingguan berhasil diproses!")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📅 Hari", df_proporsi['Hari'].nunique())
            with col2:
                st.metric("📍 Titik", df_proporsi['Source'].nunique())
            with col3:
                st.metric("🚗 Jenis", df_proporsi['Jenis Kendaraan'].nunique())
            with col4:
                st.metric("📊 Baris", len(df_proporsi))

            with st.expander("📊 Lihat Proporsi Mingguan", expanded=False):
                st.dataframe(df_proporsi, use_container_width=True)
                output_proporsi = io.BytesIO()
                with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
                    df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
                st.download_button(
                    "📥 Unduh Proporsi Mingguan", 
                    data=output_proporsi.getvalue(), 
                    file_name="proporsi_mingguan.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
        else:
            st.error("❌ Tidak ada data valid. Periksa format file mingguan.")
            st.stop()

# STEP 2: UPLOAD DATA BULANAN
st.header("📊 Langkah 2: Unggah Data Bulanan")
st.markdown("Unggah **1 file Excel** berisi data volume kendaraan untuk bulan Juli (31 hari).")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("""
    **Ketentuan File:**
    - 1 file Excel dengan **31 sheet** (tanggal 1-31).
    - Setiap sheet berisi total volume kendaraan per jenis dan jam.
    """)
with col2:
    st.info("**Format Sheet:**\n- Nama: 1, 2, ..., 31\n- Kolom: Jenis Kendaraan, 00:00 - 23:00\n- Data: Jumlah kendaraan")

uploaded_bulanan = st.file_uploader(
    "📈 Unggah File Data Bulanan (.xlsx)", 
    type=["xlsx"],
    help="File Excel berisi volume kendaraan bulan ..."
)

# Process estimation
if uploaded_bulanan and 'df_proporsi' in locals():
    with st.spinner("🔄 Memproses data bulanan..."):
        nama_file_bulanan = uploaded_bulanan.name.lower()
        
        # Extract month from filename
        match = re.search(r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)", nama_file_bulanan, re.IGNORECASE)
        bulan_map = {
            "januari": 1, "februari": 2, "maret": 3, "april": 4,
            "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
            "september": 9, "oktober": 10, "november": 11, "desember": 12
        }
        
        # Store month name for filename
        bulan_nama = "juli"  # default
        bulan = 7  # default
        
        if match and match.group(1).lower() in bulan_map:
            bulan_nama = match.group(1).lower()
            bulan = bulan_map[bulan_nama]
        
        xls = pd.read_excel(uploaded_bulanan, sheet_name=None, header=None)
        list_df = []
        sheet_warnings = []

        def dedup_columns(cols):
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

        processed_sheets = 0
        for sheet_name, df_raw in xls.items():
            try:
                sheet_num = int(sheet_name)
                if sheet_num < 1 or sheet_num > 31:
                    sheet_warnings.append(f"Sheet '{sheet_name}' diabaikan karena bukan tanggal valid")
                    continue
                
                tanggal_str = f"{sheet_num:02d}-{bulan:02d}-2025"
                try:
                    pd.to_datetime(tanggal_str, format='%d-%m-%Y')
                except ValueError:
                    sheet_warnings.append(f"Sheet '{sheet_name}' menghasilkan tanggal tidak valid: {tanggal_str}")
                    continue

            except ValueError:
                sheet_warnings.append(f"Sheet '{sheet_name}' diabaikan karena bukan angka")
                continue

            jenis_rows = df_raw[df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False)]
            if jenis_rows.empty:
                sheet_warnings.append(f"Sheet '{sheet_name}' tidak memiliki kolom 'Jenis Kendaraan'")
                continue
                
            start_idx = jenis_rows.index[0] + 1
            header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)
            if header_row.duplicated().any():
                header_row = dedup_columns(header_row)

            df_jenis = df_raw.iloc[start_idx:].copy()
            df_jenis.columns = header_row

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

        if sheet_warnings:
            with st.expander("⚠️ Peringatan Pemrosesan Data Bulanan", expanded=False):
                st.write("**Peringatan:**")
                for warning in sheet_warnings:
                    st.write(f"- {warning}")

        if not list_df:
            st.error("❌ Tidak ada data valid di file bulanan. Periksa format file.")
            st.stop()

        df_bulanan = pd.concat(list_df, ignore_index=True)
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

        jenis_map = {
            "Truk": "Truck", "Light Truck": "Truck", "Bus": "Bus", "Pick up Truck": "Pick-up",
            "Sedan": "Roda 4", "Minivan": "Roda 4", "SUV/MPV": "Roda 4",
            "Roda 3": "Tossa", "Roda 2": "Sepeda motor", "Pedestrian": "Pejalan kaki", "Unknown": "Unknown"
        }
        df_bulanan['Jenis Kendaraan'] = df_bulanan['Jenis Kendaraan'].map(jenis_map)

        for col in jam_list:
            if col in df_bulanan.columns:
                df_bulanan[col] = pd.to_numeric(df_bulanan[col], errors='coerce').fillna(0)
        
        if 'Total' in df_bulanan.columns:
            df_bulanan['Total'] = pd.to_numeric(df_bulanan['Total'], errors='coerce').fillna(0)
        
        df_bulanan = df_bulanan.groupby(['Tanggal', 'Jenis Kendaraan'], as_index=False)[groupby_cols].sum()
        df_bulanan = df_bulanan.sort_values(by=['Tanggal', 'Jenis Kendaraan']).reset_index(drop=True)

        try:
            df_bulanan["Tanggal"] = pd.to_datetime(df_bulanan["Tanggal"], format='mixed', dayfirst=True)
        except ValueError as e:
            st.error(f"❌ Gagal mengonversi tanggal: {str(e)}")
            st.stop()

        df_bulanan["Hari"] = df_bulanan["Tanggal"].dt.day_name()

        df_jenis_long = df_bulanan.melt(
            id_vars=["Tanggal", "Jenis Kendaraan", "Hari"],
            value_vars=jam_list,
            var_name="Jam",
            value_name="Jumlah"
        )
        
        df_jenis_long["Jumlah"] = pd.to_numeric(df_jenis_long["Jumlah"], errors='coerce').fillna(0)

        df_join = df_jenis_long.merge(df_proporsi[["Hari", "Source", "Jenis Kendaraan", "Proporsi"]], 
                                      on=["Hari", "Jenis Kendaraan"], how="left")

        df_join["Jumlah_Estimasi"] = df_join["Jumlah"] * df_join["Proporsi"]

        df_pivot = df_join.pivot_table(
            index=["Tanggal", "Jenis Kendaraan", "Source"],
            columns="Jam",
            values="Jumlah_Estimasi",
            aggfunc="sum"
        ).reset_index()

        df_pivot.iloc[:, 3:] = df_pivot.iloc[:, 3:].fillna(0).astype(int)

        df_pivot["Tanggal"] = pd.to_datetime(df_pivot["Tanggal"], errors="coerce")
        df_sorted = df_pivot.sort_values(by=["Tanggal", "Source"])
        df_sorted["Tanggal"] = df_sorted["Tanggal"].dt.strftime("%d-%m-%Y")
        df_final = df_sorted[df_sorted["Jenis Kendaraan"].str.lower() != "unknown"]

    st.success("🎉 Estimasi volume kendaraan berhasil dihitung!")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total Baris", len(df_final))
    with col2:
        st.metric("📍 Titik", df_final['Source'].nunique())
    with col3:
        st.metric("🚗 Jenis", df_final['Jenis Kendaraan'].nunique())
    with col4:
        st.metric("📅 Hari", df_final['Tanggal'].nunique())

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
                unique_vehicles = sorted(checkpoint_missing['Jenis Kendaraan'].unique())
                
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
                
                st.subheader("📊 Ringkasan per Titik")
                checkpoint_stats = []
                for checkpoint in sorted(missing_data['Source'].unique()):
                    checkpoint_missing = missing_data[missing_data['Source'] == checkpoint]
                    total_missing = len(checkpoint_missing)
                    unique_dates = checkpoint_missing['Tanggal'].nunique()
                    unique_vehicles = checkpoint_missing['Jenis Kendaraan'].nunique()
                    
                    checkpoint_stats.append({
                        'Titik': checkpoint,
                        'Total Data Hilang': total_missing,
                        'Tanggal Bermasalah': unique_dates,
                        'Jenis Kendaraan Terdampak': unique_vehicles,
                        'Tingkat Masalah': 'Tinggi' if total_missing > 50 else 'Sedang' if total_missing > 20 else 'Rendah'
                    })
                
                df_checkpoint_stats = pd.DataFrame(checkpoint_stats)
                st.dataframe(
                    df_checkpoint_stats,
                    column_config={
                        "Titik": st.column_config.TextColumn("📍 Titik"),
                        "Total Data Hilang": st.column_config.NumberColumn("🔢 Total Hilang"),
                        "Tanggal Bermasalah": st.column_config.NumberColumn("📅 Total Hari"),
                        "Jenis Kendaraan Terdampak": st.column_config.NumberColumn("🚗 Jenis"),
                        "Tingkat Masalah": st.column_config.TextColumn("🚦 Level")
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

    st.header("📋 Hasil Estimasi Volume Kendaraan")
    
    with st.expander("👁️ Lihat Hasil Estimasi (20 Baris Pertama)", expanded=True):
        st.dataframe(df_final.head(20), use_container_width=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Button 1: Hasil Estimasi Saja (tanpa sheet tambahan)
    with col1:
        output_estimasi_only = io.BytesIO()
        with pd.ExcelWriter(output_estimasi_only, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False, sheet_name="estimasi_volume")
        
        # Capitalize first letter of month name for filename
        bulan_nama_formatted = bulan_nama.capitalize()
        
        st.download_button(
            "🎯 Unduh Hasil Estimasi Saja", 
            data=output_estimasi_only.getvalue(), 
            file_name=f" hasil rekap {bulan_nama_formatted}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            help=f"Download hasil estimasi volume kendaraan bulan {bulan_nama_formatted} tanpa sheet tambahan"
        )
    
    # Button 2: Hasil Lengkap dengan sheet tambahan
    with col2:
        output_final = io.BytesIO()
        with pd.ExcelWriter(output_final, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False, sheet_name="estimasi_final")
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
            if len(missing_data) > 0:
                missing_data.to_excel(writer, index=False, sheet_name="data_hilang")
        
        st.download_button(
            "📊 Unduh Hasil Lengkap", 
            data=output_final.getvalue(), 
            file_name="estimasi_volume_lalu_lintas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download hasil estimasi dengan proporsi mingguan dan analisis data hilang"
        )
    
    # Button 3: Proporsi Mingguan saja
    with col3:
        output_proporsi = io.BytesIO()
        with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
        
        st.download_button(
            "📈 Unduh Proporsi Mingguan", 
            data=output_proporsi.getvalue(), 
            file_name="proporsi_mingguan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # DASHBOARD ANALISIS
    st.header("📊 Dashboard Analisis Lalu Lintas")

    @st.cache_data
    def prepare_dashboard_data(df):
        df = df.copy()
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], format='mixed', dayfirst=True, errors='coerce')
        df["Hari"] = df["Tanggal"].dt.day_name()
        keterangan_map = {
            "diponegoro": "Keluar Batu", "imam bonjol": "Batu", "a yani": "Batu", "gajah mada": "Batu",
            "sudirman": "Keluar Batu", "brantas": "Masuk Batu", "patimura": "Masuk Batu",
            "trunojoyo": "Masuk Batu", "arumdalu": "Masuk Batu", "mojorejo": "Masuk Batu"
        }
        df["Keterangan"] = df["Source"].map(keterangan_map)
        return df

    df_dashboard = prepare_dashboard_data(df_final)
    jam_cols = [col for col in df_dashboard.columns if col.endswith(":00:00")]

    tab1, tab2 = st.tabs(["📅 Rekap Harian", "📆 Rekap Bulanan"])

    with tab1:
        st.header("📅 Rekap Harian")
        col1, col2 = st.columns([1, 2])
        with col1:
            tanggal_terpilih = st.date_input("Pilih Tanggal", df_dashboard["Tanggal"].min(), key="daily_date_select")
        with col2:
            source_terpilih = st.selectbox("Pilih Lokasi", sorted(df_dashboard["Source"].unique()), key="daily_location_select")

        df_filtered = df_dashboard[(df_dashboard["Tanggal"] == pd.to_datetime(tanggal_terpilih)) & 
                                (df_dashboard["Source"] == source_terpilih)]

        if df_filtered.empty:
            st.warning("⚠️ Tidak ada data untuk tanggal dan lokasi yang dipilih.")
        else:
            st.subheader(f"Rekap **{source_terpilih}** - {tanggal_terpilih.strftime('%A, %d %B %Y')}")
            
            df_melted = df_filtered.melt(
                id_vars=["Tanggal", "Source", "Jenis Kendaraan"], 
                value_vars=jam_cols,
                var_name="Jam", 
                value_name="Jumlah"
            )

            total_per_kendaraan = df_melted.groupby("Jenis Kendaraan")["Jumlah"].sum().reset_index()
            total_per_kendaraan["Persen"] = (total_per_kendaraan["Jumlah"] / 
                                            total_per_kendaraan["Jumlah"].sum() * 100).round(2)
            total_per_kendaraan = total_per_kendaraan.sort_values(by="Jumlah", ascending=False)

            st.subheader("🚗 Jenis Kendaraan Terbanyak")
            for idx, row in total_per_kendaraan.head(3).iterrows():
                st.markdown(f"**{row['Jenis Kendaraan']}**: {int(row['Jumlah']):,} kendaraan ({row['Persen']}%)")

            col1, col2 = st.columns([1.2, 1])
            with col1:
                st.subheader("📄 Data Jenis Kendaraan")
                st.dataframe(total_per_kendaraan, use_container_width=True)

            with col2:
                st.subheader("📊 Diagram Jenis Kendaraan")

                # Hitung persen biar bisa dipakai di legend
                total_per_kendaraan["Persen"] = (
                    total_per_kendaraan["Jumlah"] / total_per_kendaraan["Jumlah"].sum() * 100
                ).round(1)

                fig1, ax1 = plt.subplots()
                wedges, texts = ax1.pie(
                    total_per_kendaraan["Jumlah"],
                    labels=None,  # tidak pakai label di pie
                    startangle=90,
                    counterclock=False,
                    colors=sns.color_palette("pastel")[0:len(total_per_kendaraan)],
                )
                ax1.axis('equal')

                # Legend dengan persentase di dalam teks
                legend_labels = [
                    f"{jenis} ({persen}%)" 
                    for jenis, persen in zip(total_per_kendaraan["Jenis Kendaraan"], total_per_kendaraan["Persen"])
                ]
                ax1.legend(
                    wedges,
                    legend_labels,
                    title="Jenis Kendaraan",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1),
                    frameon=False
                )
                st.pyplot(fig1)


            st.markdown("---")
            st.subheader("📈 Pola Waktu Kendaraan")
            kendaraan_pilih = st.selectbox("Pilih Jenis Kendaraan", total_per_kendaraan["Jenis Kendaraan"], key="daily_vehicle_select")
            df_jam = df_melted[df_melted["Jenis Kendaraan"] == kendaraan_pilih]

            fig2, ax2 = plt.subplots(figsize=(12, 4))
            sns.barplot(data=df_jam, x="Jam", y="Jumlah", ax=ax2, palette="Set2")
            ax2.set_title(f"Distribusi Waktu - {kendaraan_pilih}")
            ax2.set_ylabel("Jumlah Kendaraan")
            ax2.set_xlabel("Jam")
            plt.xticks(rotation=45)
            st.pyplot(fig2)

            st.markdown("---")
            st.subheader("📦 Total Kendaraan Masuk/Keluar Batu")
            df_tanggal = df_dashboard[df_dashboard["Tanggal"] == pd.to_datetime(tanggal_terpilih)]
            total_by_keterangan = (
                df_tanggal
                .melt(id_vars=["Keterangan"], value_vars=jam_cols, value_name="Jumlah")
                .groupby("Keterangan")["Jumlah"]
                .sum()
                .reset_index()
            )

            for _, row in total_by_keterangan.iterrows():
                st.markdown(f"**{row['Keterangan']}**: {int(row['Jumlah']):,} kendaraan")

    with tab2:
        st.header("📆 Rekap Bulanan")
        selected_month = st.selectbox(
            "Pilih Bulan", 
            sorted(df_dashboard["Tanggal"].dt.strftime("%B %Y").unique()),
            key="monthly_month_select"
        )
        month_filter = df_dashboard["Tanggal"].dt.strftime("%B %Y") == selected_month
        df_bulanan = df_dashboard[month_filter]

        if df_bulanan.empty:
            st.warning("⚠️ Tidak ada data untuk bulan yang dipilih.")
        else:
            df_melted_bulan = df_bulanan.melt(
                id_vars=["Source", "Jenis Kendaraan"], 
                value_vars=jam_cols,
                var_name="Jam", 
                value_name="Jumlah"
            )
            grouped = df_melted_bulan.groupby(["Source", "Jenis Kendaraan"])["Jumlah"].sum().reset_index()

            lokasi_terpilih = st.selectbox("Pilih Lokasi", sorted(grouped["Source"].unique()), key="monthly_location_select")
            df_source = grouped[grouped["Source"] == lokasi_terpilih]

            df_source["Persen"] = (df_source["Jumlah"] / df_source["Jumlah"].sum() * 100).round(2)
            
            total_kendaraan_bulan = df_source["Jumlah"].sum()
            st.subheader("🚗 Total Kendaraan Bulan Ini")
            st.metric(label="Total Kendaraan", value=f"{int(total_kendaraan_bulan):,} kendaraan")

            col1, col2 = st.columns([1.2, 1])
            with col1:
                st.subheader("📄 Data Jenis Kendaraan")
                st.dataframe(df_source, use_container_width=True)

            with col2:
                st.subheader(f"📊 Diagram Jenis Kendaraan - {lokasi_terpilih}")

                # Hitung persen biar bisa dipakai di legend
                df_source["Persen"] = (
                    df_source["Jumlah"] / df_source["Jumlah"].sum() * 100
                ).round(1)

                fig1, ax1 = plt.subplots()
                wedges, texts = ax1.pie(
                    df_source["Jumlah"],
                    labels=None,  # tidak pakai label di pie
                    startangle=90,
                    counterclock=False,
                    colors=sns.color_palette("pastel")[0:len(df_source)],
                )
                ax1.axis('equal')

                # Legend dengan persentase di dalam teks
                legend_labels = [
                    f"{jenis} ({persen}%)" 
                    for jenis, persen in zip(df_source["Jenis Kendaraan"], df_source["Persen"])
                ]
                ax1.legend(
                    wedges,
                    legend_labels,
                    title="Jenis Kendaraan",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1),
                    frameon=False
                )
                st.pyplot(fig1)


elif uploaded_bulanan and 'df_proporsi' not in locals():
    st.warning("⚠️ Unggah data mingguan terlebih dahulu untuk menghitung proporsi!")