import pandas as pd
from io import BytesIO

jam_list = [f"{str(i).zfill(2)}:00:00" for i in range(24)]

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

def process_uploaded_file(uploaded_file):
    # sheet names (1–30)
    xl = pd.ExcelFile(uploaded_file)
    sheet_names = xl.sheet_names
    df_jenis_list = []
    df_cp_list = []

    for sheet in sheet_names:
        df_raw = xl.parse(sheet, header=None)

        # === Per Jenis Kendaraan ===
        if df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False).any():
            start_idx = df_raw[df_raw[0].astype(str).str.contains("Jenis Kendaraan", case=False, na=False)].index[0] + 1
            header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)
            if header_row.duplicated().any():
                header_row = dedup_columns(header_row)

            df_jenis = df_raw.iloc[start_idx:].copy()
            df_jenis.columns = header_row

            # hapus baris arah/jam
            mask = df_jenis.apply(lambda row: row.astype(str).str.contains(r"Arah|Keterangan|:", case=False, na=False).any(), axis=1)
            df_jenis = df_jenis[~mask]
            df_jenis = df_jenis[df_jenis["Jenis Kendaraan"].notna()]
            df_jenis = df_jenis[~df_jenis["Jenis Kendaraan"].astype(str).str.lower().str.contains("total")]

            df_jenis["Tanggal"] = f"{sheet}-06-2025"
            df_jenis_list.append(df_jenis)

        # === Per Checkpoint ===
        if df_raw[0].astype(str).str.contains("Checkpoint", case=False, na=False).any():
            start_idx = df_raw[df_raw[0].astype(str).str.contains("Checkpoint", case=False, na=False)].index[0] + 1
            header_row = df_raw.iloc[start_idx - 1].fillna("NA").astype(str)
            if header_row.duplicated().any():
                header_row = dedup_columns(header_row)

            df_cp = df_raw.iloc[start_idx:].copy()
            df_cp.columns = header_row

            # stop di 2 baris kosong
            stop_idx = None
            kosong_count = 0
            for i, row in df_cp.iterrows():
                if row.isnull().all():
                    kosong_count += 1
                    if kosong_count == 2:
                        stop_idx = i - 1
                        break
                else:
                    kosong_count = 0

            if stop_idx is not None:
                df_cp = df_cp.loc[:stop_idx]

            mask = df_cp.apply(lambda row: row.astype(str).str.contains(r"Jenis Kendaraan|Arah|Keterangan|:", case=False, na=False).any(), axis=1)
            df_cp = df_cp[~mask]
            df_cp = df_cp[df_cp["Checkpoint"].notna()]
            df_cp = df_cp[~df_cp["Checkpoint"].astype(str).str.lower().str.contains("total")]

            df_cp["Tanggal"] = f"{sheet}-06-2025"
            df_cp_list.append(df_cp)

    # Gabungkan dan bersihkan
    df_jenis_all = pd.concat(df_jenis_list, ignore_index=True)
    df_cp_all = pd.concat(df_cp_list, ignore_index=True)

    # Bersihkan kolom jam
    df_jenis_all.columns = ["Jenis Kendaraan"] + jam_list + ["Total", "Tanggal"]
    jenis_map = {
        "Truk": "Truck", "Light Truck": "Truck", "Bus": "Bus", "Pick up Truck": "Pick-up",
        "Sedan": "Roda 4", "Minivan": "Roda 4", "SUV/MPV": "Roda 4", "Roda 3": "Tossa",
        "Roda 2": "Sepeda motor", "Pedestrian": "Pejalan kaki", "Unknown": "Unknown"
    }
    df_jenis_all["Jenis Kendaraan"] = df_jenis_all["Jenis Kendaraan"].map(jenis_map)
    df_jenis_all = df_jenis_all.groupby(['Tanggal', 'Jenis Kendaraan'], as_index=False)[jam_list + ['Total']].sum()

    # Bersihkan checkpoint
    df_cp_all.columns = ["Checkpoint"] + jam_list + ["Total", "Tanggal"]
    checkpoint_map = {
        "Jl P.Sudirman - Trunojoyo Timur": "sudirman",
        "Jl. Imam Bonjol Batos Barat": "imam bonjol",
        "Jl Gajah Mada": "gajah mada",
        "Simpang Mojorejo": "mojorejo",
        "Jl. Diponegoro Batos": "diponegoro",
        "Jl. Patimura": "patimura",
        "Jl. Brantas": "brantas",
        "Jl A. Yani depan BCA": "a yani",
        "Simpang Arumdalu": "arumdalu",
        "Jl. Trunojoyo - P. Sudirman Barat": "trunojoyo"
    }
    df_cp_all["Source"] = df_cp_all["Checkpoint"].map(checkpoint_map)
    df_cp_all.drop(columns=["Checkpoint"], inplace=True)

    return df_jenis_all, df_cp_all


def estimate_hourly_volume(df_jenis_all, uploaded_seminggu_file):
    df_seminggu = pd.read_excel(uploaded_seminggu_file)
    df_seminggu["Tanggal"] = pd.to_datetime(df_seminggu["Tanggal"], dayfirst=True)
    df_seminggu["Hari"] = df_seminggu["Tanggal"].dt.day_name()
    df_seminggu["Total"] = df_seminggu[jam_list].sum(axis=1)

    grouped = df_seminggu.groupby(["Hari", "Source", "Jenis Kendaraan"])["Total"].sum().reset_index()
    total_per_jenis_per_hari = (
        grouped.groupby(["Hari", "Jenis Kendaraan"])["Total"]
        .sum()
        .reset_index()
        .rename(columns={"Total": "TotalJenis"})
    )
    df_proporsi = grouped.merge(total_per_jenis_per_hari, on=["Hari", "Jenis Kendaraan"])
    df_proporsi["Proporsi"] = df_proporsi["Total"] / df_proporsi["TotalJenis"]

    # Long format
    df_jenis_all["Tanggal"] = pd.to_datetime(df_jenis_all["Tanggal"], dayfirst=True)
    df_jenis_all["Hari"] = df_jenis_all["Tanggal"].dt.day_name()
    df_long = df_jenis_all.melt(id_vars=["Tanggal", "Jenis Kendaraan", "Hari"], value_vars=jam_list,
                                 var_name="Jam", value_name="Jumlah")

    df_join = df_long.merge(df_proporsi, on=["Hari", "Jenis Kendaraan"], how="left")
    df_join["Jumlah_Estimasi"] = df_join["Jumlah"] * df_join["Proporsi"]

    df_pivot = df_join.pivot_table(index=["Tanggal", "Jenis Kendaraan", "Source"],
                                   columns="Jam", values="Jumlah_Estimasi", aggfunc="sum").reset_index()
    df_pivot.iloc[:, 3:] = df_pivot.iloc[:, 3:].fillna(0).astype(int)
    df_pivot["Tanggal"] = df_pivot["Tanggal"].dt.strftime("%d-%m-%Y")
    return df_pivot
