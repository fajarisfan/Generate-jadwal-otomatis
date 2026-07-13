"""
Logika generate jadwal jaga SIRS - RSUD Kota Cilegon
- Staf "PS Tetap"  -> pola 5 hari kerja (PS) lalu 2 hari libur (L), mengikuti kalender (Senin-Jumat kerja).
- Staf "Rotasi"    -> gantian Pagi(1)/Siang(2)/Malam(2) per hari, adil. Setelah Malam wajib libur 2 hari.
                     Usahakan setiap staf mendapat 5 hari kerja dan 2 hari libur dalam seminggu.
"""
import calendar
from datetime import date

SHIFT_LEGEND = {
    "PS": "Pagi Siang (5 hari kerja)",
    "P": "Pagi",
    "S": "Siang",
    "M": "Malam",
    "C": "Cuti",
    "L": "Lepas Malam / Libur",
}

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
    return date(year, month, day).weekday() in [5, 6]

def generate_ps_tetap(names, year, month, days_in_month, cuti_by_day):
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
    need = need or {"P": 1, "S": 2, "M": 2}
    counts = {n: {"P": 0, "S": 0, "M": 0, "L": 0} for n in names}
    schedule = {n: [""] * days_in_month for n in names}
    last_shift = {n: None for n in names}      # shift kemarin
    last_malam_date = {n: -10 for n in names}  # tanggal terakhir malam

    for day in range(1, days_in_month + 1):
        idx = day - 1
        cuti_today = {n for n in names if day in cuti_by_day.get(n, set())}
        
        # Tentukan forced rest (2 hari setelah malam)
        forced_rest = set()
        for n in names:
            if n in cuti_today:
                continue
            if day - last_malam_date[n] in (1, 2):
                forced_rest.add(n)
        
        # Staf yang tersedia untuk shift
        available = [n for n in names if n not in cuti_today and n not in forced_rest]
        
        # Assign cuti dan forced rest
        for n in cuti_today:
            schedule[n][idx] = "C"
        for n in forced_rest:
            schedule[n][idx] = "L"
            counts[n]["L"] += 1
            last_shift[n] = "L"
        
        # Untuk setiap shift, pilih staf dengan kriteria adil dan hindari urutan tidak wajar
        assigned_today = set()
        for shift in ("P", "S", "M"):
            for _ in range(need.get(shift, 0)):
                candidates = [n for n in available if n not in assigned_today]
                if not candidates:
                    break
                # Skor: (total_shift, count_shift_ini, penalty_sama_dengan_kemarin)
                candidates.sort(key=lambda x: (
                    counts[x]["P"] + counts[x]["S"] + counts[x]["M"],  # total kerja paling sedikit
                    counts[x][shift],                                  # shift ini paling jarang
                    0 if last_shift[x] != shift else 1                # hindari shift sama
                ))
                chosen = candidates[0]
                schedule[chosen][idx] = shift
                counts[chosen][shift] += 1
                assigned_today.add(chosen)
                last_shift[chosen] = shift
                if shift == "M":
                    last_malam_date[chosen] = day
        
        # Sisanya libur
        for n in available:
            if n not in assigned_today:
                schedule[n][idx] = "L"
                counts[n]["L"] += 1
                last_shift[n] = "L"
    
    return schedule, counts

def build_full_schedule(year, month, staff_ps_tetap, staff_rotasi, cuti_by_day, need=None):
    days_in_month = calendar.monthrange(year, month)[1]
    result = {}
    result.update(generate_ps_tetap(staff_ps_tetap, year, month, days_in_month, cuti_by_day))
    rotasi_sched, rotasi_counts = generate_rotasi(staff_rotasi, days_in_month, cuti_by_day, need)
    result.update(rotasi_sched)
    return result, days_in_month, rotasi_counts
