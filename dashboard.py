import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import os
from datetime import datetime

# python -m streamlit run app.py

st.set_page_config(page_title="Dashboard Lalu Lintas", layout="wide")

@st.cache_data
def load_all_data():
    """Load semua file Excel dengan pattern 'hasil rekap *.xlsx'"""
    
    # Cari semua file dengan pattern 'hasil rekap *.xlsx'
    file_pattern = "hasil rekap *.xlsx"
    excel_files = glob.glob(file_pattern)
    
    if not excel_files:
        st.error("❌ Tidak ditemukan file dengan format 'hasil rekap (bulan).xlsx'")
        return pd.DataFrame()
    
    all_dataframes = []
    
    for file_path in excel_files:
        try:
            # Extract nama bulan dari nama file
            bulan_dari_file = os.path.basename(file_path).replace("hasil rekap ", "").replace(".xlsx", "")
            
            df_temp = pd.read_excel(file_path)
            df_temp["File_Source"] = bulan_dari_file  # Tambah kolom untuk tracking
            all_dataframes.append(df_temp)
            
            st.sidebar.success(f"✅ Berhasil load: {file_path}")
            
        except Exception as e:
            st.sidebar.error(f"❌ Error loading {file_path}: {str(e)}")
    
    if not all_dataframes:
        return pd.DataFrame()
    
    # Gabungkan semua dataframe
    df_combined = pd.concat(all_dataframes, ignore_index=True)
    
    # Proses data seperti biasa
    df_combined["Tanggal"] = pd.to_datetime(df_combined["Tanggal"], dayfirst=True, errors='coerce')
    df_combined["Hari"] = df_combined["Tanggal"].dt.day_name()
    
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
    df_combined["Keterangan"] = df_combined["Source"].map(keterangan_map)
    
    return df_combined

# Load data
df = load_all_data()

if df.empty:
    st.stop()

jam_cols = [col for col in df.columns if col.endswith(":00:00")]

# Info file yang berhasil di-load
st.sidebar.markdown("### 📁 File Data Loaded:")
files_loaded = df["File_Source"].unique()
for file in sorted(files_loaded):
    st.sidebar.markdown(f"- hasil rekap {file}.xlsx")

# === NAVBAR ===
st.title("📊 Rekap & Analisis Kendaraan per Lokasi dan Jenis")
tab1, tab2 = st.tabs(["📅 Rekap Harian", "📆 Rekap Bulanan"])

# TAB 1: Rekap Harian
with tab1:
    st.header("📅 Rekap Harian")

    # Sekarang bisa pilih tanggal dari semua bulan yang ada
    min_date = df["Tanggal"].min()
    max_date = df["Tanggal"].max()
    
    tanggal_terpilih = st.date_input(
        "Pilih Tanggal", 
        value=max_date.date() if pd.notna(max_date) else datetime.now().date(),
        min_value=min_date.date() if pd.notna(min_date) else datetime(2023, 1, 1).date(),
        max_value=max_date.date() if pd.notna(max_date) else datetime.now().date()
    )
    
    source_terpilih = st.selectbox("Pilih Lokasi (Source)", sorted(df["Source"].unique()))

    df_filtered = df[(df["Tanggal"] == pd.to_datetime(tanggal_terpilih)) & (df["Source"] == source_terpilih)]

    if df_filtered.empty:
        st.warning("⚠️ Data tidak ditemukan untuk pilihan tersebut.")
        
        # Tampilkan tanggal yang tersedia untuk lokasi ini
        available_dates = df[df["Source"] == source_terpilih]["Tanggal"].dropna()
        if not available_dates.empty:
            st.info(f"📅 Tanggal tersedia untuk {source_terpilih}:")
            for date in sorted(available_dates.unique()):
                st.write(f"- {date.strftime('%d %B %Y')}")
    else:
        st.subheader(f"Rekap **{source_terpilih}** - {tanggal_terpilih.strftime('%A, %d %B %Y')}")
        
        df_melted = df_filtered.melt(
            id_vars=["Tanggal", "Source", "Jenis Kendaraan"], 
            value_vars=jam_cols,
            var_name="Jam", 
            value_name="Jumlah"
        )

        total_per_kendaraan = df_melted.groupby("Jenis Kendaraan")["Jumlah"].sum().reset_index()
        total_per_kendaraan["Persen"] = (total_per_kendaraan["Jumlah"] / total_per_kendaraan["Jumlah"].sum() * 100).round(2)
        total_per_kendaraan = total_per_kendaraan.sort_values(by="Jumlah", ascending=False)

        st.subheader("🚗 Jenis Kendaraan Terbanyak")
        for idx, row in total_per_kendaraan.head(3).iterrows():
            st.markdown(f"**{row['Jenis Kendaraan']}**: {row['Jumlah']} kendaraan ({row['Persen']}%)")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 Data Lengkap Jenis Kendaraan")
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
        st.subheader(f"📈 Pola Waktu Kendaraan")
        kendaraan_pilih = st.selectbox("Pilih Jenis Kendaraan", total_per_kendaraan["Jenis Kendaraan"])
        df_jam = df_melted[df_melted["Jenis Kendaraan"] == kendaraan_pilih]

        fig2, ax2 = plt.subplots(figsize=(12, 4))
        sns.barplot(data=df_jam, x="Jam", y="Jumlah", ax=ax2, palette="Set2")
        ax2.set_title(f"Distribusi Waktu - {kendaraan_pilih}")
        ax2.set_ylabel("Jumlah")
        ax2.set_xlabel("Jam")
        plt.xticks(rotation=45)
        st.pyplot(fig2)

        st.markdown("---")
        st.subheader("🚪 Total Kendaraan Masuk / Keluar Batu")

        df_tanggal = df[df["Tanggal"] == pd.to_datetime(tanggal_terpilih)]
        total_by_keterangan = (
            df_tanggal
            .melt(id_vars=["Keterangan"], value_vars=jam_cols, value_name="Jumlah")
            .groupby("Keterangan")["Jumlah"]
            .sum()
            .reset_index()
        )

        for _, row in total_by_keterangan.iterrows():
            st.markdown(f"**{row['Keterangan']}**: {row['Jumlah']} kendaraan")

# TAB 2: Rekap Bulanan
with tab2:
    st.header("📆 Rekap Bulanan")

    # Sekarang punya pilihan bulan dari semua file yang di-load
    available_months = sorted(df["Tanggal"].dt.strftime("%B %Y").dropna().unique())
    selected_month = st.selectbox("Pilih Bulan", available_months)
    
    month_filter = df["Tanggal"].dt.strftime("%B %Y") == selected_month
    df_bulanan = df[month_filter]

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

        lokasi_terpilih = st.selectbox("Pilih Lokasi", sorted(grouped["Source"].unique()))
        df_source = grouped[grouped["Source"] == lokasi_terpilih]

        df_source["Persen"] = (df_source["Jumlah"] / df_source["Jumlah"].sum() * 100).round(2)
        df_source = df_source.sort_values(by="Jumlah", ascending=False)
        
        total_kendaraan_bulan = df_source["Jumlah"].sum()
        st.subheader("🚗 Total Kendaraan Bulan Ini")
        st.metric(label="Total Kendaraan", value=f"{int(total_kendaraan_bulan):,} kendaraan")

        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.subheader("📄 Data Lengkap Jenis Kendaraan")
            st.dataframe(df_source, use_container_width=True)

        with col2:
            st.subheader(f"📊 Diagram Jenis Kendaraan Bulanan - {lokasi_terpilih}")
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

        st.markdown("---")
        st.subheader("📊 Perbandingan Total per Hari dalam Bulan")
        
        # Chart harian dalam bulan
        df_harian_bulan = (
            df_bulanan
            .melt(id_vars=["Tanggal", "Source"], value_vars=jam_cols, value_name="Jumlah")
            .groupby(["Tanggal", "Source"])["Jumlah"]
            .sum()
            .reset_index()
        )
        
        df_harian_lokasi = df_harian_bulan[df_harian_bulan["Source"] == lokasi_terpilih]
        
        if not df_harian_lokasi.empty:
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            df_harian_lokasi["Hari"] = df_harian_lokasi["Tanggal"].dt.strftime("%d")
            sns.lineplot(data=df_harian_lokasi, x="Hari", y="Jumlah", marker="o", ax=ax3)
            ax3.set_title(f"Pola Harian Bulan {selected_month} - {lokasi_terpilih}")
            ax3.set_ylabel("Total Kendaraan")
            ax3.set_xlabel("Tanggal")
            plt.xticks(rotation=45)
            st.pyplot(fig3)