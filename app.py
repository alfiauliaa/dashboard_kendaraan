import streamlit as st
import pandas as pd
import io
import re
import itertools
from datetime import datetime

# run: python -m streamlit run app.py

st.title("Analisis Volume Lalu Lintas Mingguan")

# === Step 1: Upload 7 File Excel (Masing-masing 1 Hari) ===
uploaded_files = st.file_uploader(
    "Upload 7 File Excel (1 File = 1 Hari)",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files and len(uploaded_files) == 7:
    st.success("7 file berhasil diupload!")

    nama_checkpoint = [
        "diponegoro", "imam bonjol", "a yani", "gajah mada", "sudirman",
        "brantas", "patimura", "trunojoyo", "arumdalu", "mojorejo"
    ]

    df_mingguan_list = []

    for uploaded_file in uploaded_files:
        # Deteksi tanggal dari nama file, misal: "tanggal 23 juli.xlsx"
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
            st.error(f"Format nama file tidak sesuai: {nama_file}")
            continue

        xls = pd.read_excel(uploaded_file, sheet_name=None)

        # Nama sheet diasumsikan berformat "1. 23 juli", dst
        mapping = {f"{i+1}. {tanggal} {bulan_str}": nama_checkpoint[i] for i in range(10)}
        df_list = []

        for sheet_name, df in xls.items():
            if sheet_name in mapping:
                df["Source"] = mapping[sheet_name]
                df_list.append(df)
            else:
                st.warning(f"Sheet '{sheet_name}' dilewati karena format tidak dikenali.")
                continue

        if not df_list:
            st.error(f"Tidak ada sheet yang cocok untuk file {nama_file}")
            continue

        df_final = pd.concat(df_list, ignore_index=True)

        # Buang baris semua jam = 0
        jam_cols = [col for col in df_final.columns if ":" in str(col)]
        df_final = df_final.loc[~(df_final[jam_cols] == 0).all(axis=1)].copy()

        df_final["Tanggal"] = tanggal_str
        df_mingguan_list.append(df_final)

    # Gabung semua data mingguan
    df_mingguan = pd.concat(df_mingguan_list, ignore_index=True)

    # === Step 2: Mapping dan Grouping ===
    jenis_map = {
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
    df_mingguan["Jenis Kendaraan"] = df_mingguan["Jenis Kendaraan"].replace(jenis_map)

    keterangan_map = {
        "diponegoro": "Keluar Batu",
        "imam bonjol": "Batu",
        "a yani": "Batu",
        "gajah mada": "Batu",
        "sudirman": "Keluar Batu",
        "brantas": "Masuk Batu",
        "patimura": "Masuk Batu",
        "trunojoyo": "Masuk Batu",
        "arumdalu": "Masuk Batu",
        "mojorejo": "Masuk Batu"
    }
    df_mingguan["Keterangan"] = df_mingguan["Source"].map(keterangan_map)

    jam_cols = [col for col in df_mingguan.columns if ":" in str(col)]
    kolom_awal = ["Source", "Jenis Kendaraan", "Tanggal", "Keterangan"]
    df_grouped = df_mingguan.groupby(kolom_awal, as_index=False)[jam_cols].sum()
    
    # === Step 3: Hitung Proporsi sesuai logika processing ===
    # Tambahkan kolom 'Hari' dan 'Total'
    df_grouped["Tanggal"] = pd.to_datetime(df_grouped["Tanggal"], format='%d-%m-%Y')
    df_grouped["Hari"] = df_grouped["Tanggal"].dt.day_name()
    df_grouped["Total"] = df_grouped[jam_cols].sum(axis=1)

    # Hitung proporsi sesuai logika processing
    grouped_proporsi = df_grouped.groupby(["Hari", "Source", "Jenis Kendaraan"])["Total"].sum().reset_index()
    total_per_jenis_per_hari = (
        grouped_proporsi.groupby(["Hari", "Jenis Kendaraan"])["Total"]
        .sum()
        .reset_index()
        .rename(columns={"Total": "TotalJenis"})
    )
    
    df_proporsi = grouped_proporsi.merge(total_per_jenis_per_hari, on=["Hari", "Jenis Kendaraan"])
    df_proporsi["Proporsi"] = df_proporsi["Total"] / df_proporsi["TotalJenis"]
    df_proporsi["Proporsi (%)"] = (df_proporsi["Proporsi"] * 100).round(2)

    # === Output: Proporsi Jenis Kendaraan Mingguan ===
    st.subheader("Proporsi Jenis Kendaraan per Checkpoint (Mingguan)")
    st.dataframe(df_proporsi)

    # Simpan ke Excel
    output_proporsi = io.BytesIO()
    with pd.ExcelWriter(output_proporsi, engine='openpyxl') as writer:
        df_proporsi.to_excel(writer, index=False, sheet_name="proporsi_mingguan")
    st.download_button("Download Proporsi Mingguan", data=output_proporsi.getvalue(), file_name="proporsi_mingguan.xlsx")

    # === Output dan Preview ===
    st.subheader("Data Mingguan Gabungan")
    st.dataframe(df_mingguan.head())

    st.subheader("Data Mingguan yang Sudah Dikelompokkan")
    st.dataframe(df_grouped.head())

    # Simpan untuk download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_grouped.to_excel(writer, index=False, sheet_name="data_mingguan")
    st.download_button("Download Dataset Mingguan", data=output.getvalue(), file_name="dataset_mingguan.xlsx")

else:
    st.warning("Harap upload tepat 7 file Excel (masing-masing 1 hari).")
    
st.markdown("---")
st.title("Estimasi Volume Lalu Lintas Bulanan Berdasarkan Proporsi Mingguan")

# Upload File Bulanan (Data Volume Lalu Lintas Bulanan)
uploaded_bulanan = st.file_uploader("Upload File Bulanan: Data Volume Lalu Lintas (.xlsx)", type=["xlsx"])

if uploaded_bulanan and 'df_proporsi' in locals():
    st.success(f"File bulanan berhasil diupload: {uploaded_bulanan.name}")

    # === Load File Bulanan sesuai logika processing ===
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

    # Proses setiap sheet (tanggal 1-30) sesuai logika processing
    for sheet_name, df_raw in xls.items():
        try:
            sheet_num = int(sheet_name)
        except:
            continue

        if sheet_num < 1 or sheet_num > 31:
            continue

        st.write(f"Memproses sheet: {sheet_num}")

        # Cari baris yang mengandung "Jenis Kendaraan"
        jenis_rows = df_raw[df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False)]
        if jenis_rows.empty:
            st.warning(f"Sheet {sheet_num}: Tidak ditemukan 'Jenis Kendaraan'")
            continue
            
        start_idx = jenis_rows.index[0] + 1
        header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)

        # Handle duplicate columns
        if header_row.duplicated().any():
            st.write(f"➜ Duplikat header di sheet {sheet_num} ➜ auto rename")
            header_row = dedup_columns(header_row)

        df_jenis = df_raw.iloc[start_idx:].copy()
        df_jenis.columns = header_row

        # Buang baris arah/keterangan yang mengandung "Arah", "Keterangan", atau ":"
        mask_arah = df_jenis.apply(
            lambda row: row.astype(str).str.contains(r"Arah|Keterangan|:", case=False, na=False).any(),
            axis=1
        )
        df_jenis = df_jenis[~mask_arah]

        # Buang baris kosong dan total
        df_jenis = df_jenis[df_jenis["Jenis Kendaraan"].notna()]
        df_jenis = df_jenis[~df_jenis["Jenis Kendaraan"].astype(str).str.lower().str.contains("total")]

        # Tambah kolom tanggal sesuai format processing
        df_jenis["Tanggal"] = f"{sheet_num}-06-2025"

        list_df.append(df_jenis)

    if not list_df:
        st.error("Tidak ada data yang berhasil diproses dari file bulanan.")
        st.stop()

    st.write("➜ Semua sheet OK ➜ Menggabungkan ...")
    df_bulanan = pd.concat(list_df, ignore_index=True)

    # === Cleaning sesuai logika processing ===
    # PERSIS seperti di kode processing
    jam_list = [f"{str(i).zfill(2)}:00:00" for i in range(24)]
    columns = list(df_bulanan.columns)
    
    st.write("Kolom sebelum rename:", columns)
    st.write("Total kolom:", len(columns))
    
    # Sesuai kode processing: columns[1:25] = jam_list
    # Ini artinya kolom 1 sampai 24 (24 kolom) diganti dengan jam_list
    if len(columns) >= 25:
        columns[1:25] = jam_list
        df_bulanan.columns = columns
        
        # Cek apakah ada kolom 'Total'
        groupby_cols = jam_list.copy()
        if 'Total' in df_bulanan.columns:
            groupby_cols.append('Total')
            
    else:
        st.error(f"Jumlah kolom tidak mencukupi: {len(columns)}. Dibutuhkan minimal 25 kolom.")
        st.write("Kolom yang tersedia:", columns)
        st.stop()

    # Mapping jenis kendaraan sesuai processing
    jenis_map = {
        "Truk": "Truck",
        "Light Truck": "Truck",
        "Bus": "Bus",
        "Pick up Truck": "Pick-up",
        "Sedan": "Roda 4",
        "Minivan": "Roda 4",
        "SUV/MPV": "Roda 4",
        "Roda 3": "Tossa",
        "Roda 2": "Sepeda motor",
        "Pedestrian": "Pejalan kaki",
        "Unknown": "Unknown"
    }
    df_bulanan['Jenis Kendaraan'] = df_bulanan['Jenis Kendaraan'].map(jenis_map)

    st.write("Kolom setelah rename:", df_bulanan.columns.tolist())
    st.write("Kolom untuk groupby:", groupby_cols)
    
    # Grouping sesuai processing (per tanggal dan jenis kendaraan)
    # Pastikan kolom numeric sebelum groupby
    for col in jam_list:
        if col in df_bulanan.columns:
            df_bulanan[col] = pd.to_numeric(df_bulanan[col], errors='coerce').fillna(0)
    
    if 'Total' in df_bulanan.columns:
        df_bulanan['Total'] = pd.to_numeric(df_bulanan['Total'], errors='coerce').fillna(0)
    
    df_bulanan = df_bulanan.groupby(['Tanggal', 'Jenis Kendaraan'], as_index=False)[groupby_cols].sum()

    # Sort sesuai processing
    df_bulanan = df_bulanan.sort_values(by=['Tanggal', 'Jenis Kendaraan']).reset_index(drop=True)

    # === Siapkan untuk estimasi sesuai logika processing ===
    # Tambahkan kolom Hari
    df_bulanan["Tanggal"] = pd.to_datetime(df_bulanan["Tanggal"], format='%d-%m-%Y')
    df_bulanan["Hari"] = df_bulanan["Tanggal"].dt.day_name()

    # === Ubah ke Long Format ===
    df_jenis_long = df_bulanan.melt(
        id_vars=["Tanggal", "Jenis Kendaraan", "Hari"],
        value_vars=jam_list,  # Gunakan jam_list karena sudah dipastikan tersedia
        var_name="Jam",
        value_name="Jumlah"
    )
    
    # Pastikan kolom Jumlah numeric
    df_jenis_long["Jumlah"] = pd.to_numeric(df_jenis_long["Jumlah"], errors='coerce').fillna(0)

    # === Gabungkan dengan Proporsi sesuai processing ===
    df_join = df_jenis_long.merge(df_proporsi[["Hari", "Source", "Jenis Kendaraan", "Proporsi"]], 
                                  on=["Hari", "Jenis Kendaraan"], how="left")

    # Hitung Estimasi Jumlah per Jam Berdasarkan Proporsi
    df_join["Jumlah_Estimasi"] = df_join["Jumlah"] * df_join["Proporsi"]

    # === Pivot Kembali ke Format Wide ===
    df_pivot = df_join.pivot_table(
        index=["Tanggal", "Jenis Kendaraan", "Source"],
        columns="Jam",
        values="Jumlah_Estimasi",
        aggfunc="sum"
    ).reset_index()

    # Bulatkan Nilai Estimasi dan Isi NaN
    df_pivot.iloc[:, 3:] = df_pivot.iloc[:, 3:].fillna(0).astype(int)

    # === Sorting dan Pembersihan Data sesuai processing ===
    df_pivot["Tanggal"] = pd.to_datetime(df_pivot["Tanggal"], errors="coerce")
    df_sorted = df_pivot.sort_values(by=["Tanggal", "Source"])
    df_sorted["Tanggal"] = df_sorted["Tanggal"].dt.strftime("%d-%m-%Y")

    # Hapus baris dengan jenis kendaraan 'unknown'
    df_final = df_sorted[df_sorted["Jenis Kendaraan"].str.lower() != "unknown"]

    # === [FITUR BARU] PENGECEKAN DATA YANG HILANG ===
    st.markdown("---")
    st.subheader("🔍 Analisis Data yang Hilang/Kosong")
    
    # Buat kombinasi lengkap (Cartesian product)
    all_tanggal = df_final["Tanggal"].unique()
    all_source = df_final["Source"].unique()
    all_jenis = df_final["Jenis Kendaraan"].unique()
    
    # Cartesian product untuk mendapatkan semua kombinasi yang seharusnya ada
    full_combinations = pd.DataFrame(
        list(itertools.product(all_tanggal, all_source, all_jenis)),
        columns=["Tanggal", "Source", "Jenis Kendaraan"]
    )
    
    # Merge dengan dataset hasil estimasi untuk mencari yang hilang
    merged_check = full_combinations.merge(
        df_final[["Tanggal", "Source", "Jenis Kendaraan"]],
        on=["Tanggal", "Source", "Jenis Kendaraan"],
        how="left",
        indicator=True
    )
    
    # Filter data yang hilang
    missing_data = merged_check[merged_check["_merge"] == "left_only"].drop(columns=["_merge"])
    
    if len(missing_data) > 0:
        st.error(f"⚠️ Ditemukan {len(missing_data)} kombinasi data yang hilang!")
        
        # Tampilkan ringkasan utama
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Checkpoint Bermasalah", missing_data['Source'].nunique(), 
                     delta=f"dari {len(all_source)} checkpoint")
        with col2:
            st.metric("Total Tanggal Bermasalah", missing_data['Tanggal'].nunique(),
                     delta=f"dari {len(all_tanggal)} tanggal")
        with col3:
            completeness = ((len(full_combinations) - len(missing_data)) / len(full_combinations) * 100)
            st.metric("Kelengkapan Data", f"{completeness:.1f}%", 
                     delta=f"-{100-completeness:.1f}%", delta_color="inverse")
        
        # === ANALISIS PER CHECKPOINT (SIMPLIFIED TABLE) ===
        st.subheader("📍 Analisis Detail per Checkpoint")
        
        # Buat ringkasan per checkpoint dalam bentuk tabel
        checkpoint_summary = []
        problem_sources = sorted(missing_data['Source'].unique())
        
        for source in problem_sources:
            source_missing = missing_data[missing_data['Source'] == source]
            total_expected_for_source = len(all_tanggal) * len(all_jenis)
            source_completeness = ((total_expected_for_source - len(source_missing)) / total_expected_for_source * 100)
            
            checkpoint_summary.append({
                'Checkpoint': source,
                'Data Hilang': len(source_missing),
                'Tanggal Bermasalah': source_missing['Tanggal'].nunique(),
                'Jenis Kendaraan Hilang': source_missing['Jenis Kendaraan'].nunique(),
                'Kelengkapan (%)': round(source_completeness, 1),
                'Status': '❌ Bermasalah' if source_completeness < 90 else '⚠️ Perlu Perhatian' if source_completeness < 100 else '✅ Lengkap'
            })
        
        df_checkpoint_summary = pd.DataFrame(checkpoint_summary)
        
        # Tampilkan tabel ringkasan checkpoint
        st.write("**📊 Ringkasan Status per Checkpoint:**")
        st.dataframe(
            df_checkpoint_summary,
            column_config={
                "Checkpoint": st.column_config.TextColumn("📍 Checkpoint"),
                "Data Hilang": st.column_config.NumberColumn("🔢 Data Hilang"),
                "Tanggal Bermasalah": st.column_config.NumberColumn("📅 Tanggal Bermasalah"),
                "Jenis Kendaraan Hilang": st.column_config.NumberColumn("🚗 Jenis Hilang"),
                "Kelengkapan (%)": st.column_config.NumberColumn("📈 Kelengkapan (%)", format="%.1f"),
                "Status": st.column_config.TextColumn("🚦 Status")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # === DETAIL DATA HILANG PER CHECKPOINT (TABEL LANGSUNG) ===
        st.write("**📋 Detail Data yang Hilang per Checkpoint:**")
        
        # Buat tabel detail untuk semua checkpoint sekaligus
        all_detail_table = []
        for source in problem_sources:
            source_missing = missing_data[missing_data['Source'] == source]
            
            for tanggal in sorted(source_missing['Tanggal'].unique()):
                tanggal_missing = source_missing[source_missing['Tanggal'] == tanggal]
                jenis_hilang = ', '.join(sorted(tanggal_missing['Jenis Kendaraan'].unique()))
                
                all_detail_table.append({
                    'Checkpoint': source,
                    'Tanggal': tanggal,
                    'Jumlah Jenis Hilang': len(tanggal_missing),
                    'Jenis Kendaraan yang Hilang': jenis_hilang
                })
        
        df_all_detail = pd.DataFrame(all_detail_table)
        
        # Tampilkan tabel detail lengkap
        st.dataframe(
            df_all_detail,
            column_config={
                "Checkpoint": st.column_config.TextColumn("📍 Checkpoint"),
                "Tanggal": st.column_config.TextColumn("📅 Tanggal"),
                "Jumlah Jenis Hilang": st.column_config.NumberColumn("🔢 Jumlah Hilang"),
                "Jenis Kendaraan yang Hilang": st.column_config.TextColumn("🚗 Jenis Kendaraan yang Hilang")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # === RINGKASAN GLOBAL ===
        st.subheader("📊 Ringkasan Global")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🚩 Checkpoint Paling Bermasalah:**")
            source_problems = missing_data['Source'].value_counts()
            for source, count in source_problems.head(5).items():
                percentage = (count / len(missing_data)) * 100
                st.write(f"📍 **{source}**: {count} data hilang ({percentage:.1f}%)")
        
        with col2:
            st.write("**📅 Tanggal Paling Bermasalah:**")
            date_problems = missing_data['Tanggal'].value_counts()
            for date, count in date_problems.head(5).items():
                percentage = (count / len(missing_data)) * 100
                st.write(f"🗓️ **{date}**: {count} data hilang ({percentage:.1f}%)")
        
        # Jenis kendaraan yang paling sering hilang
        st.write("**🚗 Jenis Kendaraan yang Paling Sering Hilang:**")
        vehicle_problems = missing_data['Jenis Kendaraan'].value_counts()
        cols = st.columns(min(3, len(vehicle_problems)))
        for idx, (vehicle, count) in enumerate(vehicle_problems.items()):
            with cols[idx % 3]:
                percentage = (count / len(missing_data)) * 100
                st.metric(vehicle, f"{count} kali", delta=f"{percentage:.1f}%")
        
        # === REKOMENDASI AKSI ===
        st.subheader("💡 Rekomendasi Tindakan")
        
        # Analisis pola untuk memberikan rekomendasi
        if missing_data['Source'].nunique() == 1:
            problematic_source = missing_data['Source'].iloc[0]
            st.warning(f"🎯 **Fokus pada checkpoint '{problematic_source}'** - semua data hilang berasal dari sini")
        elif missing_data['Tanggal'].nunique() <= 3:
            problematic_dates = ', '.join(missing_data['Tanggal'].unique())
            st.warning(f"🎯 **Periksa data untuk tanggal: {problematic_dates}** - kemungkinan masalah pada file sumber")
        else:
            st.info("🔍 **Masalah tersebar** - periksa konsistensi format data di semua file Excel")
        
        # Langkah-langkah perbaikan
        st.write("**📋 Langkah Perbaikan yang Disarankan:**")
        st.write("1. 📂 Periksa file Excel sumber untuk checkpoint yang bermasalah")
        st.write("2. 🔍 Pastikan nama sheet sesuai format yang diharapkan")
        st.write("3. ✅ Verifikasi data jenis kendaraan tidak kosong atau bernilai 0 semua")
        st.write("4. 🔄 Re-upload file setelah diperbaiki")
        
        # Download data yang hilang
        output_missing = io.BytesIO()
        with pd.ExcelWriter(output_missing, engine='openpyxl') as writer:
            missing_data.to_excel(writer, index=False, sheet_name="semua_data_hilang")
            df_checkpoint_summary.to_excel(writer, index=False, sheet_name="ringkasan_checkpoint")
            
            # Sheet per checkpoint
            for source in problem_sources:
                source_data = missing_data[missing_data['Source'] == source]
                sheet_name = f"hilang_{source}"[:31]  # Excel sheet name limit
                source_data.to_excel(writer, index=False, sheet_name=sheet_name)
        
        st.download_button(
            "📥 Download Analisis Data Hilang (Detail per Checkpoint)", 
            data=output_missing.getvalue(), 
            file_name="analisis_data_hilang_detail.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    else:
        st.success("✅ **PERFECT!** Tidak ada data yang hilang!")
        st.balloons()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Kelengkapan Data", "100%", delta="✅ Sempurna")
        with col2:
            st.metric("Total Kombinasi", len(full_combinations))
        with col3:
            st.metric("Data Tersedia", len(df_final))

    # === TAMPILKAN HASIL AKHIR ===
    st.subheader("📋 Estimasi Volume Lalu Lintas Bulanan per Checkpoint")
    st.dataframe(df_final.head(20))

    # Simpan Excel
    output_est = io.BytesIO()
    with pd.ExcelWriter(output_est, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="rekap_estimasi")
        if len(missing_data) > 0:
            missing_data.to_excel(writer, index=False, sheet_name="data_hilang")
    st.download_button(
        "📥 Download Estimasi Bulanan (+ Data Hilang)", 
        data=output_est.getvalue(), 
        file_name="rekap_estimasi_bulanan_lengkap.xlsx"
    )

    # Tampilkan summary
    st.subheader("📈 Summary Data")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Baris Hasil Estimasi", len(df_final))
        st.metric("Checkpoint Tersedia", df_final['Source'].nunique() if len(df_final) > 0 else 0)
        st.metric("Jenis Kendaraan", df_final['Jenis Kendaraan'].nunique() if len(df_final) > 0 else 0)
    
    with col2:
        if len(df_final) > 0:
            st.metric("Rentang Tanggal", f"{df_final['Tanggal'].min()} - {df_final['Tanggal'].max()}")
        st.metric("Data yang Hilang", len(missing_data))
        completeness = ((len(full_combinations) - len(missing_data)) / len(full_combinations) * 100) if len(full_combinations) > 0 else 100
        st.metric("Kelengkapan Data (%)", f"{completeness:.1f}%")
    
    # Debug info (bisa di-collapse)
    with st.expander("🔧 Debug Info", expanded=False):
        st.write("**Data Bulanan setelah processing:**")
        st.dataframe(df_bulanan.head())
        st.write("**Data Proporsi:**")
        st.dataframe(df_proporsi.head())
        st.write("**Data setelah merge:**")
        st.dataframe(df_join.head())

elif uploaded_bulanan and 'df_proporsi' not in locals():
    st.warning("Harap upload data mingguan terlebih dahulu untuk mendapatkan proporsi!")
    
else:
    st.info("Silakan upload file bulanan setelah data mingguan selesai diproses.")