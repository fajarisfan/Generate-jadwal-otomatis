import calendar
from datetime import date

import pandas as pd
import streamlit as st

from scheduler import build_full_schedule, SHIFT_LEGEND, SHIFT_COLORS
from pdf_export import export_jadwal_pdf, BULAN_ID

st.set_page_config(page_title="Generator Jadwal Jaga SIRS", page_icon="🗓️", layout="wide")

PIN = st.secrets.get("PIN", "301199")

DEFAULT_STAFF = [
    {"nama": "ISTIQOMAH, S.Kom", "tipe": "PS Tetap"},
    {"nama": "Ahmad Haerudin", "tipe": "Rotasi"},
    {"nama": "Isfan Fajar Anugrah, S.Kom", "tipe": "Rotasi"},
    {"nama": "Ferdyansyah Zaelani", "tipe": "Rotasi"},
    {"nama": "Teguh Adi Pradana, A.Md", "tipe": "Rotasi"},
    {"nama": "Syihabudin Amien, S.Kom", "tipe": "Rotasi"},
    {"nama": "M. Hisyam Rizky F, S.Kom", "tipe": "PS Tetap"},
    {"nama": "Jaka Gilang R, A.Md", "tipe": "Rotasi"},
    {"nama": "Reynold Marcelino, S.Kom", "tipe": "PS Tetap"},
]

COLOR_MAP = SHIFT_COLORS


def check_pin():
    if st.session_state.get("authed"):
        return True
    st.title("🗓️ Generator Jadwal Jaga SIRS")
    pin = st.text_input("Masukkan PIN", type="password")
    if st.button("Masuk"):
        if pin == PIN:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("PIN salah.")
    return False


def style_cell(val):
    return f"background-color: {COLOR_MAP.get(val, '#FFFFFF')}"


def main():
    if not check_pin():
        return

    st.title("🗓️ Generator Jadwal Jaga - Unit SIRS RSUD Kota Cilegon")
    st.caption("Isi data staf, tentukan cuti (kalau ada), lalu klik Generate. Jadwal otomatis dibagi adil.")

    col1, col2 = st.columns(2)
    today = date.today()
    with col1:
        bulan = st.selectbox("Bulan", list(range(1, 13)), index=today.month - 1, format_func=lambda m: BULAN_ID[m])
    with col2:
        tahun = st.number_input("Tahun", min_value=2024, max_value=2100, value=today.year, step=1)

    days_in_month = calendar.monthrange(int(tahun), bulan)[1]

    st.subheader("1. Data Staf")
    st.caption("Tipe **PS Tetap** = kerja Pagi-Siang non-shift terus (kayak Kepala Unit, Rey, Hisyam). Tipe **Rotasi** = gantian Pagi/Siang/Malam.")
    if "staff_df" not in st.session_state:
        st.session_state["staff_df"] = pd.DataFrame(DEFAULT_STAFF)

    staff_df = st.data_editor(
        st.session_state["staff_df"],
        num_rows="dynamic",
        column_config={
            "tipe": st.column_config.SelectboxColumn("tipe", options=["PS Tetap", "Rotasi"]),
        },
        use_container_width=True,
        key="staff_editor",
    )
    st.session_state["staff_df"] = staff_df

    st.subheader("2. Cuti (opsional)")
    st.caption("Tambah baris kalau ada staf yang cuti di tanggal tertentu bulan ini.")
    if "cuti_df" not in st.session_state:
        st.session_state["cuti_df"] = pd.DataFrame(columns=["nama", "tanggal_mulai", "tanggal_selesai"])

    nama_options = staff_df["nama"].dropna().tolist()
    cuti_df = st.data_editor(
        st.session_state["cuti_df"],
        num_rows="dynamic",
        column_config={
            "nama": st.column_config.SelectboxColumn("nama", options=nama_options),
            "tanggal_mulai": st.column_config.NumberColumn("tgl mulai", min_value=1, max_value=31, step=1),
            "tanggal_selesai": st.column_config.NumberColumn("tgl selesai", min_value=1, max_value=31, step=1),
        },
        use_container_width=True,
        key="cuti_editor",
    )
    st.session_state["cuti_df"] = cuti_df

    # --- FITUR BARU: PILIH STAF ROTASI YANG NON-SHIFT ---
    st.subheader("2b. Staf Rotasi yang Non-Shift Bulan Ini")
    st.caption("Pilih staf Rotasi yang TIDAK ikut shift (misal libur dinas atau giliran non-shift). Mereka akan dijadwalkan seperti PS Tetap (masuk Senin–Jumat, libur akhir pekan).")
    rotasi_staff = staff_df[staff_df["tipe"] == "Rotasi"]["nama"].tolist()
    if "non_shift_rotasi" not in st.session_state:
        st.session_state["non_shift_rotasi"] = []
    non_shift_rotasi = st.multiselect(
        "Staf Rotasi yang menjadi non-shift",
        options=rotasi_staff,
        default=st.session_state["non_shift_rotasi"],
    )
    st.session_state["non_shift_rotasi"] = non_shift_rotasi
    # --------------------------------------------------

    st.subheader("3. Kebutuhan Petugas per Shift")
    c1, c2, c3 = st.columns(3)
    with c1:
        n_pagi = st.number_input("Pagi", min_value=1, max_value=5, value=1)
    with c2:
        n_siang = st.number_input("Siang", min_value=1, max_value=5, value=2)
    with c3:
        n_malam = st.number_input("Malam", min_value=1, max_value=5, value=2)

    if st.button("🔀 Generate Jadwal", type="primary"):
        cuti_by_day = {}
        for _, r in cuti_df.iterrows():
            if pd.isna(r.get("nama")) or pd.isna(r.get("tanggal_mulai")) or pd.isna(r.get("tanggal_selesai")):
                continue
            days = set(range(int(r["tanggal_mulai"]), int(r["tanggal_selesai"]) + 1))
            cuti_by_day.setdefault(r["nama"], set()).update(days)

        staff_ps_tetap = staff_df[staff_df["tipe"] == "PS Tetap"]["nama"].tolist()
        staff_rotasi = staff_df[staff_df["tipe"] == "Rotasi"]["nama"].tolist()
        non_shift = st.session_state.get("non_shift_rotasi", [])

        # Gabungkan non-shift ke PS Tetap untuk bulan ini
        ps_tetap_bulan = staff_ps_tetap + non_shift
        rotasi_bulan = [n for n in staff_rotasi if n not in non_shift]

        # Validasi kecukupan jumlah staf shift
        need_total = n_pagi + n_siang + n_malam
        if len(rotasi_bulan) < need_total:
            st.error(f"Staf Rotasi tersisa {len(rotasi_bulan)} orang, tetapi kebutuhan per hari {need_total} orang. Kurangi yang non-shift atau tambah kebutuhan.")
            st.stop()

        need = {"P": n_pagi, "S": n_siang, "M": n_malam}
        schedule, dim, counts = build_full_schedule(
            int(tahun), bulan,
            ps_tetap_bulan,
            rotasi_bulan,
            cuti_by_day,
            need=need
        )
        staff_order = staff_df["nama"].tolist()
        st.session_state["schedule"] = schedule
        st.session_state["staff_order"] = staff_order
        st.session_state["days_in_month"] = dim
        st.session_state["counts"] = counts
        st.session_state["gen_year"] = int(tahun)
        st.session_state["gen_month"] = bulan

    if "schedule" in st.session_state:
        st.subheader("Hasil Jadwal")
        schedule = st.session_state["schedule"]
        staff_order = st.session_state["staff_order"]
        dim = st.session_state["days_in_month"]

        display_df = pd.DataFrame(
            {str(d): [schedule[n][d - 1] for n in staff_order] for d in range(1, dim + 1)},
            index=staff_order,
        )
        st.dataframe(display_df.style.applymap(style_cell), use_container_width=True)

        with st.expander("Cek keadilan pembagian shift (Rotasi)"):
            counts = st.session_state["counts"]
            if counts:
                cdf = pd.DataFrame(counts).T
                st.dataframe(cdf, use_container_width=True)

        pdf_buf = export_jadwal_pdf(
            st.session_state["gen_year"], st.session_state["gen_month"],
            staff_order, schedule, dim,
        )
        st.download_button(
            "⬇️ Download PDF (siap print)",
            data=pdf_buf,
            file_name=f"JADWAL_SHIFT_SIMRS_{BULAN_ID[st.session_state['gen_month']]}_{st.session_state['gen_year']}.pdf",
            mime="application/pdf",
        )

    st.divider()
    with st.expander("Keterangan kode shift"):
        for code, desc in SHIFT_LEGEND.items():
            st.write(f"**{code}** : {desc}")


if __name__ == "__main__":
    main()
