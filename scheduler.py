"""
Logika generate jadwal jaga SIRS - RSUD Kota Cilegon
- Staf "PS Tetap"  -> pola 5 hari kerja (PS) lalu 2 hari libur (L), mengikuti kalender (Senin-Jumat kerja).
- Staf "Rotasi"    -> gantian Pagi(1org)/Siang(2org)/Malam(2org) per hari, adil berdasar hitungan
                      paling sedikit kebagian shift itu. Setelah Malam wajib libur (rest) besoknya.
"""
import calendar
from datetime import date
from collections import defaultdict

SHIFT_LEGEND = {
    "PS": "Pagi Siang (5 hari kerja)",
    "P": "Pagi",
    "S": "Siang",
    "M": "Malam",
    "C": "Cuti",
    "L": "Lepas Malam / Libur",
}

# satu sumber warna dipakai bareng oleh app.py (preview di layar) & pdf_export.py (PDF)
SHIFT_COLORS = {
    "PS": "#FFF3B0",
    "P": "#C7F2A4",
    "S": "#A4D8F2",
    "M": "#E7A4F2",
    "C": "#F2A4A4",
    "L": "#DDDDDD",
    "": "#FFFFFF",
}


def is_weekend(day, month, year):
    """Return True jika hari Sabtu atau Minggu."""
    return date(year, month, day).weekday() in [5, 6]


def generate_ps_tetap(names, year, month, days_in_month, cuti_by_day):
    """
    5 hari kerja (PS) lalu 2 hari libur (L), mengikuti kalender aktual.
    Cuti manual akan override menjadi 'C'.
    """
    schedule = {}
    for name in names:
        seq = []
        for day in range(1, days_in_month + 1):
            if day in cuti_by_day.get(name, set()):
                seq.append("C")
            elif is_weekend(day, month, year):
                seq.append("L")
            else:
                seq.append("PS")
        schedule[name] = seq
    return schedule


def generate_rotasi(names, days_in_month, cuti_by_day, need=None):
    """
    Rotasi adil: tiap hari butuh Pagi=1, Siang=2, Malam=2 (default).
    Sisa orang di pool -> Libur. Yang habis Malam WAJIB libur besoknya.
    Pemilihan orang per shift pakai orang yang PALING JARANG kebagian shift itu (dan total shift).
    """
    need = need or {"P": 1, "S": 2, "M": 2}
    counts = {n: {"P": 0, "S": 0, "M": 0, "L": 0} for n in names}
    schedule = {n: [""] * days_in_month for n in names}
    last_malam = set()  # staf yang jaga Malam hari sebelumnya

    for day in range(1, days_in_month + 1):
        idx = day - 1
        cuti_today = {n for n in names if day in cuti_by_day.get(n, set())}
        forced_rest = {n for n in last_malam if n not in cuti_today}
        available = [n for n in names if n not in cuti_today and n not in forced_rest]

        # Assign cuti dan forced rest
        for n in cuti_today:
            schedule[n][idx] = "C"
        for n in forced_rest:
            schedule[n][idx] = "L"
            counts[n]["L"] += 1

        assigned_today = set()
        for shift in ("P", "S", "M"):
            for _ in range(need.get(shift, 0)):
                candidates = [n for n in available if n not in assigned_today]
                if not candidates:
                    break
                # Prioritas: paling sedikit mendapat shift ini, lalu total shift
                candidates.sort(
                    key=lambda x: (counts[x][shift], counts[x]["P"] + counts[x]["S"] + counts[x]["M"])
                )
                chosen = candidates[0]
                schedule[chosen][idx] = shift
                counts[chosen][shift] += 1
                assigned_today.add(chosen)

        # Sisanya libur
        for n in available:
            if n not in assigned_today:
                schedule[n][idx] = "L"
                counts[n]["L"] += 1

        # Update last_malam untuk hari berikutnya
        last_malam = {n for n in names if schedule[n][idx] == "M"}

    return schedule, counts


def build_full_schedule(year, month, staff_ps_tetap, staff_rotasi, cuti_by_day, need=None):
    days_in_month = calendar.monthrange(year, month)[1]
    result = {}
    # Jadwalkan staf PS Tetap (termasuk non-shift sementara)
    result.update(generate_ps_tetap(staff_ps_tetap, year, month, days_in_month, cuti_by_day))
    # Jadwalkan staf Rotasi
    rotasi_sched, rotasi_counts = generate_rotasi(staff_rotasi, days_in_month, cuti_by_day, need)
    result.update(rotasi_sched)
    return result, days_in_month, rotasi_counts
