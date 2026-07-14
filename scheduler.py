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

# --- aturan rotasi shift ----------------------------------------------------
TIER = {"P": 0, "S": 1, "M": 2}
REST_AFTER_MALAM = 2   # jumlah hari libur wajib setelah dapat shift Malam
MAX_STREAK = 5          # maksimal hari kerja berturut-turut sebelum wajib libur


MAX_SAME_TIER_STREAK = 2  # maks hari beruntun di tier yang SAMA sebelum wajib naik/libur


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


def _shift_allowed(tier, shift, same_tier_streak=0):
    """
    Progresi shift dalam satu rangkaian kerja (streak) cuma boleh NAIK
    (P -> S -> M) dan naiknya maksimal 1 tingkat per hari, gak boleh turun,
    gak boleh loncat (misal P langsung ke M).

    tier None artinya staf baru mau mulai streak baru -> wajib mulai dari Pagi.

    same_tier_streak: sudah berapa hari beruntun staf ini ada di tier yang
    sama. Kalau sudah MAX_SAME_TIER_STREAK hari, gak boleh "nyangkut" di
    tier itu lagi (harus naik tier atau kena libur) -> ini yang mencegah
    ada orang yang keseringan Pagi-terus atau Siang-terus.
    """
    want = TIER[shift]
    if tier is None:
        return want == TIER["P"]
    if not (tier <= want <= tier + 1):
        return False
    if want == tier and same_tier_streak >= MAX_SAME_TIER_STREAK:
        return False
    return True


def _default_state(names):
    return {
        n: {"tier": None, "streak": 0, "rest_left": 0, "same_tier_streak": 0}
        for n in names
    }


def generate_rotasi(names, days_in_month, cuti_by_day, need=None, carry_state=None):
    """
    Aturan yang dipakai:
    - Setiap rangkaian kerja (streak) dimulai dari Pagi (P), boleh naik ke
      Siang (S) lalu Malam (M), tapi TIDAK BOLEH turun tier
      (misal dari S balik lagi ke P) dan tidak boleh loncat tier.
    - Sesudah dapat Malam, staf WAJIB libur REST_AFTER_MALAM (default 2) hari.
    - Satu streak kerja maksimal MAX_STREAK (default 5) hari, sesudahnya
      wajib libur (streak reset, mulai dari Pagi lagi kalau kerja lagi).
    - Kalau staf available tapi gak kebagian shift hari itu (kelebihan orang),
      dia dianggap libur biasa -> streak-nya reset.
    - Pemilihan siapa yang dapat shift tetap pakai prinsip fairness lama:
      diprioritaskan yang total kerjanya paling sedikit, lalu yang paling
      jarang dapat shift itu -> jadi P dan S gak numpuk ke orang yang sama.
    - carry_state (opsional): dict {nama: {"tier","streak","rest_left"}}
      buat nyambungin dari akhir bulan sebelumnya. Bisa didapat dari
      end_state hasil generate_rotasi()/build_full_schedule() bulan lalu,
      atau dari extract_carry_state() kalau bulan lalu jadwalnya bukan
      hasil generate (misal masih manual/dari PDF).
    """
    need = need or {"P": 1, "S": 2, "M": 2}
    counts = {n: {"P": 0, "S": 0, "M": 0, "L": 0} for n in names}
    schedule = {n: [""] * days_in_month for n in names}

    state = _default_state(names)
    if carry_state:
        for n in names:
            if n in carry_state:
                state[n].update(carry_state[n])

    for day in range(1, days_in_month + 1):
        idx = day - 1
        cuti_today = {n for n in names if day in cuti_by_day.get(n, set())}

        # staf yang masih dalam masa libur wajib pasca-Malam
        forced_rest = {
            n for n in names
            if n not in cuti_today and state[n]["rest_left"] > 0
        }

        available = [n for n in names if n not in cuti_today and n not in forced_rest]

        for n in cuti_today:
            schedule[n][idx] = "C"
            state[n]["streak"] = 0
            state[n]["tier"] = None
            state[n]["same_tier_streak"] = 0

        for n in forced_rest:
            schedule[n][idx] = "L"
            counts[n]["L"] += 1
            state[n]["rest_left"] -= 1
            if state[n]["rest_left"] == 0:
                state[n]["streak"] = 0
                state[n]["tier"] = None
                state[n]["same_tier_streak"] = 0

        assigned_today = set()
        for shift in ("P", "S", "M"):
            for _ in range(need.get(shift, 0)):
                candidates = [
                    n for n in available
                    if n not in assigned_today
                    and state[n]["streak"] < MAX_STREAK
                    and _shift_allowed(state[n]["tier"], shift, state[n]["same_tier_streak"])
                ]
                if not candidates:
                    break
                candidates.sort(key=lambda x: (
                    counts[x]["P"] + counts[x]["S"] + counts[x]["M"],  # total kerja paling sedikit
                    counts[x][shift],                                   # shift ini paling jarang
                ))
                chosen = candidates[0]
                schedule[chosen][idx] = shift
                counts[chosen][shift] += 1
                assigned_today.add(chosen)
                new_tier = TIER[shift]
                if state[chosen]["tier"] == new_tier:
                    state[chosen]["same_tier_streak"] += 1
                else:
                    state[chosen]["same_tier_streak"] = 1
                state[chosen]["tier"] = new_tier
                state[chosen]["streak"] += 1
                if shift == "M":
                    state[chosen]["rest_left"] = REST_AFTER_MALAM

        # sisanya (available tapi gak kebagian shift) -> libur, streak reset
        for n in available:
            if n not in assigned_today:
                schedule[n][idx] = "L"
                counts[n]["L"] += 1
                state[n]["streak"] = 0
                state[n]["tier"] = None
                state[n]["same_tier_streak"] = 0

    end_state = {n: dict(state[n]) for n in names}
    return schedule, counts, end_state


def extract_carry_state(schedule, names, rest_after_malam=REST_AFTER_MALAM, max_streak=MAX_STREAK):
    """
    Bangun carry_state dari jadwal HASIL AKHIR suatu bulan (misal Juli, walau
    itu jadwal manual dari PDF, bukan hasil generate_rotasi()), supaya bulan
    berikutnya (Agustus) tetap nyambung aturan progresinya.

    schedule: dict {nama: [shift_per_hari...]} untuk bulan yang sudah lewat.
    """
    state = {}
    for n in names:
        seq = schedule.get(n, [])
        tier = None
        streak = 0
        rest_left = 0

        # cek dulu: apakah akhir bulan masih dalam masa libur wajib pasca-Malam
        days_since_malam = None
        for j in range(len(seq) - 1, -1, -1):
            if seq[j] == "M":
                days_since_malam = len(seq) - 1 - j
                break
            if seq[j] not in ("L", "-", "", "C"):
                break

        if days_since_malam is not None and days_since_malam < rest_after_malam:
            rest_left = rest_after_malam - days_since_malam
        else:
            # cari streak kerja beruntun di ekor bulan; tier yang dipakai
            # HARUS dari hari paling akhir (paling baru), bukan yang paling
            # rendah di sepanjang streak-nya.
            i = len(seq) - 1
            while i >= 0 and seq[i] in ("P", "S", "M") and streak < max_streak:
                streak += 1
                i -= 1
            if streak > 0:
                tier = TIER[seq[-1]]

        # hitung berapa hari beruntun di tier yang SAMA di ekor bulan
        # (dipakai buat aturan maks MAX_SAME_TIER_STREAK hari nyangkut di tier sama)
        same_tier_streak = 0
        if tier is not None:
            k = len(seq) - 1
            while k >= 0 and seq[k] in ("P", "S", "M") and TIER[seq[k]] == tier:
                same_tier_streak += 1
                k -= 1

        state[n] = {
            "tier": tier,
            "streak": streak,
            "rest_left": rest_left,
            "same_tier_streak": same_tier_streak,
        }
    return state


def build_full_schedule(year, month, staff_ps_tetap, staff_rotasi, cuti_by_day, need=None, carry_state=None):
    """
    carry_state (opsional): state rotasi dari akhir bulan sebelumnya, supaya
    jadwal nyambung antar bulan (mis. akhir Juli -> awal Agustus).
    Sekarang function ini juga return end_state, buat langsung dipakai
    sebagai carry_state generate bulan berikutnya.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    result = {}
    result.update(generate_ps_tetap(staff_ps_tetap, year, month, days_in_month, cuti_by_day))
    rotasi_sched, rotasi_counts, end_state = generate_rotasi(
        staff_rotasi, days_in_month, cuti_by_day, need, carry_state
    )
    result.update(rotasi_sched)
    return result, days_in_month, rotasi_counts, end_state
