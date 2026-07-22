import calendar
from datetime import date, datetime

SHIFT_LEGEND = {
    "PS": "Pagi Siang (5 hari kerja)",
    "P": "Pagi",
    "S": "Siang",
    "M": "Malam",
    "C": "Cuti",
    "-": "Lepas Malam",
    "L": "Libur",
}

SHIFT_COLORS = {
    "PS": "#FFF3B0",
    "P": "#C7F2A4",
    "S": "#A4D8F2",
    "M": "#E7A4F2",
    "C": "#F2A4A4",
    "-": "#DDDDDD",
    "L": "#DDDDDD",
    "": "#FFFFFF",
}

# Daftar libur nasional resmi di Indonesia tahun 2026 (SKB 3 Menteri)
LIBUR_NASIONAL_2026 = {
    "01-01": "Tahun Baru Masehi",
    "16-01": "Isra Mikraj Nabi Muhammad S.A.W.",
    "17-02": "Tahun Baru Imlek 2577 Kongzili",
    "19-03": "Hari Suci Nyepi (Tahun Baru Saka 1948)",
    "21-03": "Hari Raya Idulfitri 1447 H",
    "22-03": "Hari Raya Idulfitri 1447 H",
    "03-04": "Wafat Yesus Kristus",
    "05-04": "Hari Raya Paskah",
    "01-05": "Hari Buruh Internasional",
    "14-05": "Kenaikan Yesus Kristus",
    "27-05": "Hari Raya Iduladha 1447 H",
    "31-05": "Hari Raya Waisak 2570 BE",
    "01-06": "Hari Lahir Pancasila",
    "16-06": "Tahun Baru Islam 1448 H",
    "17-08": "Hari Kemerdekaan Republik Indonesia",
    "25-08": "Maulid Nabi Muhammad S.A.W.",
    "25-12": "Hari Raya Natal",
}

LIBUR_NASIONAL = {
    2026: LIBUR_NASIONAL_2026,
}

def is_weekend(day, month, year):
    return date(year, month, day).weekday() in [5, 6]

def is_holiday(day, month, year):
    if is_weekend(day, month, year):
        return True
    key = f"{day:02d}-{month:02d}"
    libur_nasional = LIBUR_NASIONAL.get(year, {})
    if key in libur_nasional:
        return True
    return False

def get_holiday_name(day, month, year):
    if is_weekend(day, month, year):
        return "Hari Minggu"
    key = f"{day:02d}-{month:02d}"
    libur_nasional = LIBUR_NASIONAL.get(year, {})
    return libur_nasional.get(key, "")

def generate_ps_tetap(names, year, month, days_in_month, cuti_by_day):
    schedule = {}
    for name in names:
        seq = []
        for day in range(1, days_in_month + 1):
            if day in cuti_by_day.get(name, set()):
                seq.append("C")
            elif is_holiday(day, month, year):
                seq.append("L")  # PS Tetap libur di hari Minggu/tanggal merah
            else:
                seq.append("PS")
        schedule[name] = seq
    return schedule

def generate_rotasi(names, days_in_month, cuti_by_day, need=None, last_month_shift=None):
    need = need or {"P": 1, "S": 2, "M": 2}
    counts = {n: {"P": 0, "S": 0, "M": 0, "L": 0} for n in names}
    schedule = {n: [""] * days_in_month for n in names}
    last_shift = {n: last_month_shift.get(n, None) if last_month_shift else None for n in names}
    last_malam_date = {n: -10 for n in names}

    for day in range(1, days_in_month + 1):
        idx = day - 1
        cuti_today = {n for n in names if day in cuti_by_day.get(n, set())}
        forced_rest = set()
        for n in names:
            if n in cuti_today:
                continue
            # Hari setelah Malam = Lepas Malam ("-")
            if day - last_malam_date[n] == 1:
                forced_rest.add(n)
        
        available = [n for n in names if n not in cuti_today and n not in forced_rest]

        for n in cuti_today:
            schedule[n][idx] = "C"
            last_shift[n] = "C"
        for n in forced_rest:
            schedule[n][idx] = "-"  # Lepas Malam
            counts[n]["L"] += 1
            last_shift[n] = "-"

        assigned_today = set()
        
        for shift in ("P", "S", "M"):
            for _ in range(need.get(shift, 0)):
                candidates = [n for n in available if n not in assigned_today]
                if not candidates:
                    break
                
                def score(n):
                    prev = last_shift[n]
                    total_kerja = counts[n]["P"] + counts[n]["S"] + counts[n]["M"]
                    specific = counts[n][shift]
                    penalty = 0
                    
                    if prev == shift:
                        penalty += 100
                    if prev == "S" and shift == "P":
                        penalty += 50
                    if prev == "-" and shift == "P":
                        penalty += 50
                    if prev == "-" and shift == "S":
                        penalty += 30
                    if prev == "P" and shift == "M":
                        penalty += 20
                    
                    return (total_kerja, specific, penalty)
                
                candidates.sort(key=score)
                chosen = candidates[0]
                schedule[chosen][idx] = shift
                counts[chosen][shift] += 1
                assigned_today.add(chosen)
                last_shift[chosen] = shift
                if shift == "M":
                    last_malam_date[chosen] = day

        # Sisanya libur - pakai "L"
        for n in available:
            if n not in assigned_today:
                schedule[n][idx] = "L"
                counts[n]["L"] += 1
                last_shift[n] = "L"

    return schedule, counts, last_shift

def build_full_schedule(year, month, staff_ps_tetap, staff_rotasi, cuti_by_day, need=None, last_month_shift=None):
    days_in_month = calendar.monthrange(year, month)[1]
    result = {}
    result.update(generate_ps_tetap(staff_ps_tetap, year, month, days_in_month, cuti_by_day))
    rotasi_sched, rotasi_counts, last_shift = generate_rotasi(
        staff_rotasi, days_in_month, cuti_by_day, need, last_month_shift
    )
    result.update(rotasi_sched)
    return result, days_in_month, rotasi_counts, last_shift
