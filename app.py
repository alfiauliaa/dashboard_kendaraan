import streamlit as st
import pandas as pd
import io
import re
import itertools
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Traffic Volume Analyzer",
    page_icon="🚦",
    layout="wide"
)

# Main header
st.title("🚦 Analisis Volume Lalu Lintas")
st.subheader("Estimasi Distribusi Bulanan Berdasarkan Proporsi Mingguan")

# Penjelasan singkat
with st.expander("ℹ️ Cara Kerja Aplikasi", expanded=False):
    st.markdown("""
    **Konsep:**
    1. **Data Mingguan (Sen-Ming)** → Ambil proporsi % kendaraan di setiap titik
    2. **Data Volume Bulanan** → Total kendaraan per hari (belum tahu distribusinya)
    3. **Hasil Estimasi** → Distribusi kendaraan bulanan ke 10 titik berdasarkan proporsi mingguan
    
    **Contoh:**
    - Data volume: 400 mobil tanggal 1 (total dari 10 titik)
    - Proporsi mingguan: Titik A = 15%, Titik B = 20%, dst...
    - Hasil: Titik A = 60 mobil, Titik B = 80 mobil, dst...
    """)

# STEP 1: UPLOAD DATA MINGGUAN
st.header("📁 STEP 1: Upload Data Mingguan (Proporsi)")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    **Ketentuan File Mingguan:**
    - Upload **7 file Excel** (Senin - Minggu, urutan bebas)
    - Format nama file: `tanggal [angka] [bulan].xlsx` ada 7 file, senin - minggu
      - Contoh: `tanggal 23 juli.xlsx - tanggal 27 juli.xlsx`
    - Setiap file berisi **10 sheet** (10 titik checkpoint) di list biru disamping
    - Format nama sheet: `1. 23 juli`, `2. 23 juli`, dst... (1. 23 juli = Diponegoro tanggal 23 juli)
    - Pastikan setiap sheet memiliki format yang konsisten
    """)

with col2:
    st.info("**10 Checkpoint:**\n1. Diponegoro\n2. Imam Bonjol\n3. A Yani\n4. Gajah Mada\n5. Sudirman\n6. Brantas\n7. Patimura\n8. Trunojoyo\n9. Arumdalu\n10. Mojorejo")

uploaded_files = st.file_uploader(
    "📂 Pilih 7 File Excel (Data Mingguan)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Upload file Excel untuk 7 hari (Senin-Minggu)"
)

# Progress indicator
if uploaded_files:
    progress_col1, progress_col2, progress_col3 = st.columns(3)
    
    with progress_col1:
        file_count = len(uploaded_files)
        if file_count == 7:
            st.success(f"✅ {file_count}/7 files uploaded")
        elif file_count < 7:
            st.warning(f"⏳ {file_count}/7 files uploaded")
        else:
            st.error(f"❌ {file_count}/7 files - Terlalu banyak!")
    
    with progress_col2:
        if file_count > 0:
            st.info(f"📋 Files: {', '.join([f.name for f in uploaded_files[:3]])}" + 
                   (f" +{file_count-3} more" if file_count > 3 else ""))
    
    with progress_col3:
        if file_count == 7:
            st.success("🚀 Ready to process!")

# Process weekly data
if uploaded_files and len(uploaded_files) == 7:
    
    with st.spinner("🔄 Memproses data mingguan..."):
        nama_checkpoint = [
            "diponegoro", "imam bonjol", "a yani", "gajah mada", "sudirman",
            "brantas", "patimura", "trunojoyo", "arumdalu", "mojorejo"
        ]

        df_mingguan_list = []

        for uploaded_file in uploaded_files:
            # Deteksi tanggal dari nama file
            nama_file = uploaded_file.name.lower()
            match = re.search(r"(\d{1,2})[\s\-_]*(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)", nama_file)

            if match:
                tanggal = int(match.group(1))
                bulan_str = match.group(2)
                bulan_map = {
                    "januari": 1, "februari": 2, "maret": 3, "april": 4,
                    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                    "september": 9, "oktober": 10, "november": 11, "desember": 12
                }
                bulan = bulan_map[bulan_str]
                tanggal_str = f"{tanggal:02d}-{bulan:02d}-2025"
            else:
                st.error(f"❌ Format nama file tidak sesuai: {nama_file}")
                continue

            xls = pd.read_excel(uploaded_file, sheet_name=None)
            mapping = {f"{i+1}. {tanggal} {bulan_str}": nama_checkpoint[i] for i in range(10)}
            df_list = []

            for sheet_name, df in xls.items():
                if sheet_name in mapping:
                    df["Source"] = mapping[sheet_name]
                    df_list.append(df)

            if df_list:
                df_final = pd.concat(df_list, ignore_index=True)
                jam_cols = [col for col in df_final.columns if ":" in str(col)]
                df_final = df_final.loc[~(df_final[jam_cols] == 0).all(axis=1)].copy()
                df_final["Tanggal"] = tanggal_str
                df_mingguan_list.append(df_final)

        if df_mingguan_list:
            df_mingguan = pd.concat(df_mingguan_list, ignore_index=True)
            
            # Mapping dan grouping
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
            df_grouped = df_mingguan.groupby(kolom_awal, as_index=False)[jam_cols].sum()
            
            # Hitung proporsi
            df_grouped["Tanggal"] = pd.to_datetime(df_grouped["Tanggal"], format='%d-%m-%Y')
            df_grouped["Hari"] = df_grouped["Tanggal"].dt.day_name()
            df_grouped["Total"] = df_grouped[jam_cols].sum(axis=1)

            grouped_proporsi = df_grouped.groupby(["Hari", "Source", "Jenis Kendaraan"])["Total"].sum().reset_index()
            total_per_jenis_per_hari = (
                grouped_proporsi.groupby(["Hari", "Jenis Kendaraan"])["Total"]
                .sum().reset_index().rename(columns={"Total": "TotalJenis"})
            )
            
            df_proporsi = grouped_proporsi.merge(total_per_jenis_per_hari, on=["Hari", "Jenis Kendaraan"])
            df_proporsi["Proporsi"] = df_proporsi["Total"] / df_proporsi["TotalJenis"]
            df_proporsi["Proporsi (%)"] = (df_proporsi["Proporsi"] * 100).round(2)

    # Success message with summary
    st.success("✅ Data mingguan berhasil diproses!")
    
    # Quick summary
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    with summary_col1:
        st.metric("📅 Hari Terproses", df_proporsi['Hari'].nunique())
    with summary_col2:
        st.metric("📍 Checkpoint", df_proporsi['Source'].nunique())
    with summary_col3:
        st.metric("🚗 Jenis Kendaraan", df_proporsi['Jenis Kendaraan'].nunique())
    with summary_col4:
        st.metric("📊 Total Records", len(df_proporsi))

    # Preview proporsi (collapsible)
    with st.expander("👁️ Preview Proporsi Mingguan", expanded=False):
        st.dataframe(df_proporsi, use_container_width=True)
        
        # Download button
        output_proporsi = io.BytesIO()
        with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
        st.download_button(
            "📥 Download Proporsi Mingguan", 
            data=output_proporsi.getvalue(), 
            file_name="proporsi_mingguan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif uploaded_files and len(uploaded_files) != 7:
    st.warning(f"⚠️ Upload tepat 7 file! Saat ini: {len(uploaded_files)} file")

# STEP 2: UPLOAD DATA BULANAN
st.header("📊 STEP 2: Upload Data Volume Bulanan")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    **Ketentuan File Bulanan:**
    - 1 file Excel dengan **30-31 sheet** (tanggal 1-31)
    - Setiap sheet berisi total volume kendaraan untuk hari tersebut
    """)

with col2:
    st.info("**Format yang Diharapkan:**\n- Sheet: 1, 2, 3, ..., 31\n- Kolom: Jenis Kendaraan + jam (00:00 - 23:00)\n- Data: Total volume per jenis kendaraan")

uploaded_bulanan = st.file_uploader(
    "📈 Pilih File Data Volume Bulanan (.xlsx)", 
    type=["xlsx"],
    help="File Excel berisi data volume lalu lintas bulanan"
)

# Process estimation
if uploaded_bulanan and 'df_proporsi' in locals():
    
    with st.spinner("🔄 Memproses estimasi bulanan..."):
        
        # Process monthly data (same logic as original)
        xls = pd.read_excel(uploaded_bulanan, sheet_name=None, header=None)
        list_df = []

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

        # Process each sheet (same logic as original)
        processed_sheets = 0
        for sheet_name, df_raw in xls.items():
            try:
                sheet_num = int(sheet_name)
            except:
                continue

            if sheet_num < 1 or sheet_num > 31:
                continue

            # Find "Jenis Kendaraan" row
            jenis_rows = df_raw[df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False)]
            if jenis_rows.empty:
                continue
                
            start_idx = jenis_rows.index[0] + 1
            header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)

            if header_row.duplicated().any():
                header_row = dedup_columns(header_row)

            df_jenis = df_raw.iloc[start_idx:].copy()
            df_jenis.columns = header_row

            # Clean data
            mask_arah = df_jenis.apply(
                lambda row: row.astype(str).str.contains(r"Arah|Keterangan|:", case=False, na=False).any(),
                axis=1
            )
            df_jenis = df_jenis[~mask_arah]
            df_jenis = df_jenis[df_jenis["Jenis Kendaraan"].notna()]
            df_jenis = df_jenis[~df_jenis["Jenis Kendaraan"].astype(str).str.lower().str.contains("total")]

            df_jenis["Tanggal"] = f"{sheet_num}-06-2025"
            list_df.append(df_jenis)
            processed_sheets += 1

        if not list_df:
            st.error("❌ Tidak ada data yang berhasil diproses dari file bulanan.")
            st.stop()

        df_bulanan = pd.concat(list_df, ignore_index=True)

        # Column processing
        jam_list = [f"{str(i).zfill(2)}:00:00" for i in range(24)]
        columns = list(df_bulanan.columns)
        
        if len(columns) >= 25:
            columns[1:25] = jam_list
            df_bulanan.columns = columns
            groupby_cols = jam_list.copy()
            if 'Total' in df_bulanan.columns:
                groupby_cols.append('Total')
        else:
            st.error(f"❌ Jumlah kolom tidak mencukupi: {len(columns)}. Dibutuhkan minimal 25 kolom.")
            st.stop()

        # Vehicle type mapping
        jenis_map = {
            "Truk": "Truck", "Light Truck": "Truck", "Bus": "Bus", "Pick up Truck": "Pick-up",
            "Sedan": "Roda 4", "Minivan": "Roda 4", "SUV/MPV": "Roda 4",
            "Roda 3": "Tossa", "Roda 2": "Sepeda motor", "Pedestrian": "Pejalan kaki", "Unknown": "Unknown"
        }
        df_bulanan['Jenis Kendaraan'] = df_bulanan['Jenis Kendaraan'].map(jenis_map)

        # Convert to numeric
        for col in jam_list:
            if col in df_bulanan.columns:
                df_bulanan[col] = pd.to_numeric(df_bulanan[col], errors='coerce').fillna(0)
        
        if 'Total' in df_bulanan.columns:
            df_bulanan['Total'] = pd.to_numeric(df_bulanan['Total'], errors='coerce').fillna(0)
        
        df_bulanan = df_bulanan.groupby(['Tanggal', 'Jenis Kendaraan'], as_index=False)[groupby_cols].sum()
        df_bulanan = df_bulanan.sort_values(by=['Tanggal', 'Jenis Kendaraan']).reset_index(drop=True)

        # Add day column
        df_bulanan["Tanggal"] = pd.to_datetime(df_bulanan["Tanggal"], format='%d-%m-%Y')
        df_bulanan["Hari"] = df_bulanan["Tanggal"].dt.day_name()

        # Convert to long format
        df_jenis_long = df_bulanan.melt(
            id_vars=["Tanggal", "Jenis Kendaraan", "Hari"],
            value_vars=jam_list,
            var_name="Jam",
            value_name="Jumlah"
        )
        
        df_jenis_long["Jumlah"] = pd.to_numeric(df_jenis_long["Jumlah"], errors='coerce').fillna(0)

        # Merge with proportions
        df_join = df_jenis_long.merge(df_proporsi[["Hari", "Source", "Jenis Kendaraan", "Proporsi"]], 
                                      on=["Hari", "Jenis Kendaraan"], how="left")

        df_join["Jumlah_Estimasi"] = df_join["Jumlah"] * df_join["Proporsi"]

        # Pivot back to wide format
        df_pivot = df_join.pivot_table(
            index=["Tanggal", "Jenis Kendaraan", "Source"],
            columns="Jam",
            values="Jumlah_Estimasi",
            aggfunc="sum"
        ).reset_index()

        df_pivot.iloc[:, 3:] = df_pivot.iloc[:, 3:].fillna(0).astype(int)

        # Final cleaning
        df_pivot["Tanggal"] = pd.to_datetime(df_pivot["Tanggal"], errors="coerce")
        df_sorted = df_pivot.sort_values(by=["Tanggal", "Source"])
        df_sorted["Tanggal"] = df_sorted["Tanggal"].dt.strftime("%d-%m-%Y")
        df_final = df_sorted[df_sorted["Jenis Kendaraan"].str.lower() != "unknown"]

    # Success message
    st.success("🎉 Estimasi berhasil dihitung!")
    
    # Main results summary
    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
    with result_col1:
        st.metric("📋 Total Records", len(df_final))
    with result_col2:
        st.metric("📍 Checkpoint", df_final['Source'].nunique())
    with result_col3:
        st.metric("🚗 Jenis Kendaraan", df_final['Jenis Kendaraan'].nunique())
    with result_col4:
        st.metric("📅 Hari Terproses", processed_sheets)

    # Data quality analysis
    st.header("🔍 Analisis Kualitas Data")
    
    # Check for missing data
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
    
    # Data quality metrics
    quality_col1, quality_col2, quality_col3 = st.columns(3)
    
    completeness = ((len(full_combinations) - len(missing_data)) / len(full_combinations) * 100) if len(full_combinations) > 0 else 100
    
    with quality_col1:
        if completeness == 100:
            st.success(f"✅ Kelengkapan Data: {completeness:.1f}%")
        elif completeness >= 90:
            st.warning(f"⚠️ Kelengkapan Data: {completeness:.1f}%")
        else:
            st.error(f"❌ Kelengkapan Data: {completeness:.1f}%")
    
    with quality_col2:
        st.info(f"🎯 Data Lengkap: {len(full_combinations) - len(missing_data):,}")
    
    with quality_col3:
        if len(missing_data) == 0:
            st.success("🎉 Tidak Ada Data Hilang!")
        else:
            st.error(f"⚠️ Data Hilang: {len(missing_data):,}")

    # Missing data analysis (only show if there are issues)
    if len(missing_data) > 0:
        with st.expander("🔍 Detail Data yang Hilang", expanded=True):
            
            # Create detailed analysis table
            st.subheader("📋 Tabel Data yang Hilang per Checkpoint")
            
            # Group missing data by checkpoint and create summary
            missing_summary = []
            for checkpoint in sorted(missing_data['Source'].unique()):
                checkpoint_missing = missing_data[missing_data['Source'] == checkpoint]
                
                # Get unique dates and vehicle types for this checkpoint
                unique_dates = sorted(checkpoint_missing['Tanggal'].unique())
                unique_vehicles = sorted(checkpoint_missing['Jenis Kendaraan'].unique())
                
                # Create detailed rows for each date
                for date in unique_dates:
                    date_missing = checkpoint_missing[checkpoint_missing['Tanggal'] == date]
                    vehicles_missing = sorted(date_missing['Jenis Kendaraan'].unique())
                    
                    missing_summary.append({
                        'Checkpoint': checkpoint,
                        'Tanggal': date,
                        'Jumlah Jenis Hilang': len(vehicles_missing),
                        'Jenis Kendaraan yang Hilang': ', '.join(vehicles_missing)
                    })
            
            if missing_summary:
                df_missing_summary = pd.DataFrame(missing_summary)
                
                # Display the table with better formatting
                st.dataframe(
                    df_missing_summary,
                    column_config={
                        "Checkpoint": st.column_config.TextColumn(
                            "📍 Checkpoint",
                            width="medium"
                        ),
                        "Tanggal": st.column_config.TextColumn(
                            "📅 Tanggal",
                            width="small"
                        ),
                        "Jumlah Jenis Hilang": st.column_config.NumberColumn(
                            "🔢 Jenis Hilang",
                            width="small"
                        ),
                        "Jenis Kendaraan yang Hilang": st.column_config.TextColumn(
                            "🚗 Jenis Kendaraan yang Hilang",
                            width="large"
                        )
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Summary stats per checkpoint
                st.subheader("📊 Ringkasan per Checkpoint")
                
                checkpoint_stats = []
                for checkpoint in sorted(missing_data['Source'].unique()):
                    checkpoint_missing = missing_data[missing_data['Source'] == checkpoint]
                    total_missing = len(checkpoint_missing)
                    unique_dates = checkpoint_missing['Tanggal'].nunique()
                    unique_vehicles = checkpoint_missing['Jenis Kendaraan'].nunique()
                    
                    checkpoint_stats.append({
                        'Checkpoint': checkpoint,
                        'Total Data Hilang': total_missing,
                        'Tanggal Bermasalah': unique_dates,
                        'Jenis Kendaraan Terdampak': unique_vehicles,
                        'Tingkat Masalah': 'Tinggi' if total_missing > 50 else 'Sedang' if total_missing > 20 else 'Rendah'
                    })
                
                df_checkpoint_stats = pd.DataFrame(checkpoint_stats)
                
                # Display checkpoint summary with color coding
                st.dataframe(
                    df_checkpoint_stats,
                    column_config={
                        "Checkpoint": st.column_config.TextColumn("📍 Checkpoint"),
                        "Total Data Hilang": st.column_config.NumberColumn("🔢 Total Hilang"),
                        "Tanggal Bermasalah": st.column_config.NumberColumn("📅 Total Hari"),
                        "Jenis Kendaraan Terdampak": st.column_config.NumberColumn("🚗 Jenis"),
                        "Tingkat Masalah": st.column_config.TextColumn("🚦 Level")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Download missing data analysis
                output_missing = io.BytesIO()
                with pd.ExcelWriter(output_missing, engine='openpyxl') as writer:
                    missing_data.to_excel(writer, index=False, sheet_name="data_hilang_detail")
                    if 'df_missing_summary' in locals():
                        df_missing_summary.to_excel(writer, index=False, sheet_name="ringkasan_per_checkpoint")
                
                st.download_button(
                    "📥 Download Analisis Data Hilang", 
                    data=output_missing.getvalue(), 
                    file_name="analisis_data_hilang.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # Final results
    st.header("📋 Hasil Estimasi Final")
    
    # Preview results
    with st.expander("👁️ Preview Hasil Estimasi (20 baris pertama)", expanded=True):
        st.dataframe(df_final.head(20), use_container_width=True)
    
    # # === VISUALISASI DASHBOARD ===
    # st.header("📊 Dashboard Visualisasi")
    
    # # Prepare data for visualization
    # df_viz = df_final.copy()
    # df_viz["Tanggal"] = pd.to_datetime(df_viz["Tanggal"], dayfirst=True, errors='coerce')
    # df_viz["Hari"] = df_viz["Tanggal"].dt.day_name()
    
    # # Mapping keterangan
    # keterangan_map = {
    #     "diponegoro": "Keluar Batu",
    #     "imam bonjol": "Batu", 
    #     "a yani": "Batu",
    #     "gajah mada": "Batu",
    #     "sudirman": "Keluar Batu",
    #     "brantas": "Masuk Batu",
    #     "patimura": "Masuk Batu", 
    #     "trunojoyo": "Masuk Batu",
    #     "arumdalu": "Masuk Batu",
    #     "mojorejo": "Masuk Batu"
    # }
    # df_viz["Keterangan"] = df_viz["Source"].map(keterangan_map)
    
    # # Get jam columns from final data
    # jam_cols_viz = [col for col in df_viz.columns if col.endswith(":00:00")]
    
    # # Create tabs for different views
    # tab1, tab2 = st.tabs(["📅 Rekap Harian", "📆 Rekap Bulanan"])
    
    # # TAB 1: Rekap Harian
    # with tab1:
    #     st.subheader("📅 Rekap Harian")
        
    #     col1, col2 = st.columns(2)
    #     with col1:
    #         tanggal_terpilih = st.date_input("Pilih Tanggal", df_viz["Tanggal"].min())
    #     with col2:
    #         source_terpilih = st.selectbox("Pilih Checkpoint", sorted(df_viz["Source"].unique()))
        
    #     df_filtered = df_viz[(df_viz["Tanggal"] == pd.to_datetime(tanggal_terpilih)) & (df_viz["Source"] == source_terpilih)]
        
    #     if df_filtered.empty:
    #         st.warning("⚠️ Data tidak ditemukan untuk pilihan tersebut.")
    #     else:
    #         st.write(f"**Rekap {source_terpilih} - {tanggal_terpilih.strftime('%A, %d %B %Y')}**")
            
    #         # Melt data untuk visualisasi
    #         df_melted = df_filtered.melt(
    #             id_vars=["Tanggal", "Source", "Jenis Kendaraan"], 
    #             value_vars=jam_cols_viz,
    #             var_name="Jam", 
    #             value_name="Jumlah"
    #         )
            
    #         # Total per jenis kendaraan
    #         total_per_kendaraan = df_melted.groupby("Jenis Kendaraan")["Jumlah"].sum().reset_index()
    #         total_per_kendaraan["Persen"] = (total_per_kendaraan["Jumlah"] / total_per_kendaraan["Jumlah"].sum() * 100).round(2)
    #         total_per_kendaraan = total_per_kendaraan.sort_values(by="Jumlah", ascending=False)
            
    #         # Top 3 jenis kendaraan
    #         st.write("**🏆 Top 3 Jenis Kendaraan:**")
    #         for idx, row in total_per_kendaraan.head(3).iterrows():
    #             st.write(f"• **{row['Jenis Kendaraan']}**: {row['Jumlah']} kendaraan ({row['Persen']}%)")
            
    #         col1, col2 = st.columns(2)
            
    #         with col1:
    #             st.write("**📄 Detail per Jenis Kendaraan**")
    #             st.dataframe(total_per_kendaraan, use_container_width=True)
            
    #         with col2:
    #             st.write("**📊 Diagram Pie Jenis Kendaraan**")
    #             if len(total_per_kendaraan) > 0:
    #                 import matplotlib.pyplot as plt
    #                 fig, ax = plt.subplots(figsize=(8, 6))
    #                 ax.pie(total_per_kendaraan["Jumlah"], 
    #                       labels=total_per_kendaraan["Jenis Kendaraan"],
    #                       autopct='%1.1f%%', 
    #                       startangle=90)
    #                 ax.set_title(f"Distribusi Jenis Kendaraan - {source_terpilih}")
    #                 st.pyplot(fig)
            
    #         # Pola waktu
    #         st.write("**📈 Pola Waktu per Jenis Kendaraan**")
    #         kendaraan_pilih = st.selectbox("Pilih Jenis Kendaraan untuk Analisis Waktu", 
    #                                      total_per_kendaraan["Jenis Kendaraan"].tolist())
            
    #         if kendaraan_pilih:
    #             df_jam = df_melted[df_melted["Jenis Kendaraan"] == kendaraan_pilih]
                
    #             # Buat bar chart pola waktu
    #             fig, ax = plt.subplots(figsize=(12, 5))
    #             jam_order = [f"{i:02d}:00:00" for i in range(24)]
    #             df_jam_sorted = df_jam.set_index('Jam').reindex(jam_order).fillna(0).reset_index()
                
    #             ax.bar(range(len(df_jam_sorted)), df_jam_sorted['Jumlah'])
    #             ax.set_xticks(range(0, len(jam_order), 2))
    #             ax.set_xticklabels([jam_order[i][:5] for i in range(0, len(jam_order), 2)], rotation=45)
    #             ax.set_title(f"Distribusi Waktu - {kendaraan_pilih}")
    #             ax.set_xlabel("Jam")
    #             ax.set_ylabel("Jumlah Kendaraan")
    #             st.pyplot(fig)
            
    #         # Total masuk/keluar Batu
    #         st.write("**🚪 Total Kendaraan Masuk/Keluar Batu**")
    #         df_tanggal = df_viz[df_viz["Tanggal"] == pd.to_datetime(tanggal_terpilih)]
            
    #         if not df_tanggal.empty:
    #             df_melted_all = df_tanggal.melt(
    #                 id_vars=["Keterangan"], 
    #                 value_vars=jam_cols_viz, 
    #                 value_name="Jumlah"
    #             )
    #             total_by_keterangan = df_melted_all.groupby("Keterangan")["Jumlah"].sum().reset_index()
                
    #             for _, row in total_by_keterangan.iterrows():
    #                 st.write(f"• **{row['Keterangan']}**: {int(row['Jumlah']):,} kendaraan")
    
    # # TAB 2: Rekap Bulanan  
    # with tab2:
    #     st.subheader("📆 Rekap Bulanan")
        
    #     # Filter bulan
    #     available_months = df_viz["Tanggal"].dt.strftime("%B %Y").unique()
    #     selected_month = st.selectbox("Pilih Bulan", sorted(available_months))
        
    #     month_filter = df_viz["Tanggal"].dt.strftime("%B %Y") == selected_month
    #     df_bulanan = df_viz[month_filter]
        
    #     if df_bulanan.empty:
    #         st.warning("⚠️ Tidak ada data untuk bulan yang dipilih.")
    #     else:
    #         # Pilih lokasi
    #         lokasi_terpilih = st.selectbox("Pilih Checkpoint", sorted(df_bulanan["Source"].unique()))
            
    #         # Melt data bulanan
    #         df_melted_bulan = df_bulanan[df_bulanan["Source"] == lokasi_terpilih].melt(
    #             id_vars=["Source", "Jenis Kendaraan"], 
    #             value_vars=jam_cols_viz,
    #             var_name="Jam", 
    #             value_name="Jumlah"
    #         )
            
    #         # Group by jenis kendaraan
    #         grouped = df_melted_bulan.groupby(["Source", "Jenis Kendaraan"])["Jumlah"].sum().reset_index()
    #         grouped["Persen"] = (grouped["Jumlah"] / grouped["Jumlah"].sum() * 100).round(2)
            
    #         # Total kendaraan bulan
    #         total_kendaraan_bulan = grouped["Jumlah"].sum()
    #         st.metric("🚗 Total Kendaraan Bulan Ini", f"{int(total_kendaraan_bulan):,} kendaraan")
            
    #         col1, col2 = st.columns([1.2, 1])
            
    #         with col1:
    #             st.write("**📄 Detail per Jenis Kendaraan (Bulanan)**")
    #             st.dataframe(grouped, use_container_width=True)
            
    #         with col2:
    #             st.write(f"**📊 Diagram Bulanan - {lokasi_terpilih}**")
    #             if len(grouped) > 0:
    #                 fig, ax = plt.subplots(figsize=(8, 6))
    #                 ax.pie(grouped["Jumlah"], 
    #                       labels=grouped["Jenis Kendaraan"],
    #                       autopct='%1.1f%%', 
    #                       startangle=90)
    #                 ax.set_title(f"Distribusi Bulanan - {lokasi_terpilih}")
    #                 st.pyplot(fig)
    
    # Download final results
    col1, col2 = st.columns(2)
    
    with col1:
        # Main results
        output_final = io.BytesIO()
        with pd.ExcelWriter(output_final, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False, sheet_name="estimasi_final")
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
            if len(missing_data) > 0:
                missing_data.to_excel(writer, index=False, sheet_name="data_hilang")
        
        st.download_button(
            "🎉 Download Hasil Estimasi Lengkap", 
            data=output_final.getvalue(), 
            file_name="estimasi_volume_lalu_lintas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    
    with col2:
        # Proportions only
        output_proporsi = io.BytesIO()
        with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
            df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
        
        st.download_button(
            "📊 Download Proporsi Saja", 
            data=output_proporsi.getvalue(), 
            file_name="proporsi_mingguan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif uploaded_bulanan and 'df_proporsi' not in locals():
    st.warning("⚠️ Harap upload data mingguan terlebih dahulu! Data mingguan diperlukan untuk menghitung proporsi sebelum memproses data bulanan.")