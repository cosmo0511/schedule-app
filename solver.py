"""
시간표 자동 배정 솔버 (OR-Tools CP-SAT)
config + participants 를 받아 배정 결과를 돌려준다.

조건:
  - 인원 균등 배치 (총 근무 격차 최소화)
  - 빈칸 허용 (정원 못 채우면 비움, 장소 우선순위로 빈칸 순서 결정)
  - 장소별 운영시간 (운영 안 하는 시간대엔 배정 X)
  - 연속 근무: 한 장소에 들어가면 min_run 슬롯 이상 연속 (토막 금지)
  - 다른 장소로 이동 가능하되 거기서도 min_run 이상 연속
  - 하루 총 근무 max_day 슬롯 이하
"""
from ortools.sat.python import cp_model


def solve(config, participants, time_limit=30):
    """
    필수 장소(required)는 먼저 hard 로 시도하고, 그 때문에 불가능하면
    soft(높은 페널티)로 다시 풀어 가능한 만큼 충족 + 못한 사람을 알려준다.
    """
    has_required = any(p.get("required") for p in config["places"])
    res = _solve(config, participants, time_limit, required_hard=True)
    if has_required and not res["feasible"]:
        res = _solve(config, participants, time_limit, required_hard=False)
        res["required_relaxed"] = True
    return res


def _solve(config, participants, time_limit=30, required_hard=True):
    days = config["days"]                 # ["월","화",...]
    times = config["times"]               # 슬롯(시간대) 리스트
    places = config["places"]             # [{"name","cap","priority","rows":[...], "required":bool}]
    min_run = config["min_run_slots"]     # 최소 연속 슬롯 수
    max_day = config["max_day_slots"]     # 하루 최대 슬롯 수

    nT = len(times)
    ndays = len(days)
    nslots = nT * ndays
    P = range(len(places))

    def row_of(s):
        return s % nT

    people = [p["name"] for p in participants]
    avail = {p["name"]: set(p["slots"]) for p in participants}

    m = cp_model.CpModel()

    x = {}
    for i in people:
        for s in range(nslots):
            for p in P:
                ok = (s in avail[i]) and (row_of(s) in places[p]["rows"])
                v = m.NewBoolVar(f"x_{i}_{s}_{p}")
                if not ok:
                    m.Add(v == 0)
                x[i, s, p] = v

    # 한 슬롯에 한 사람은 한 장소
    for i in people:
        for s in range(nslots):
            m.Add(sum(x[i, s, p] for p in P) <= 1)

    # 장소 정원 + 빈칸(우선순위 가중)
    cover_pen = 0
    for s in range(nslots):
        for p in P:
            if row_of(s) not in places[p]["rows"]:
                continue
            cap = places[p]["cap"]
            under = m.NewIntVar(0, cap, f"u_{s}_{p}")
            m.Add(sum(x[i, s, p] for i in people) + under == cap)
            cover_pen += places[p]["priority"] * under

    # 하루 총 <= max_day
    total = {}
    for i in people:
        day_tots = []
        for d in range(ndays):
            ds = [s for s in range(nslots) if s // nT == d]
            dt = m.NewIntVar(0, max_day, f"dt_{i}_{d}")
            m.Add(dt == sum(x[i, s, p] for s in ds for p in P))
            day_tots.append(dt)
        total[i] = m.NewIntVar(0, nslots, f"t_{i}")
        m.Add(total[i] == sum(day_tots))

    # 장소별 최소 연속 근무 (하루 경계서 리셋)
    starts = []
    for i in people:
        for p in P:
            for s in range(nslots):
                r = row_of(s)
                has_prev = r > 0
                prev = x[i, s - 1, p] if has_prev else 0
                st = m.NewBoolVar(f"st_{i}_{s}_{p}")
                m.Add(st >= x[i, s, p] - prev)
                m.Add(st <= x[i, s, p])
                if has_prev:
                    m.Add(st <= 1 - x[i, s - 1, p])
                room = True
                for k in range(1, min_run):
                    if r + k <= nT - 1:
                        m.Add(x[i, s + k, p] >= st)
                    else:
                        room = False
                if not room:
                    m.Add(st == 0)   # 남은 운영시간 부족 -> 시작 금지
                starts.append(st)

    # 하루 안에서는 끊김 없이 한 덩어리로 근무 (중간 공백 금지; 장소 이동은 OK)
    for i in people:
        for d in range(ndays):
            dslots = [s for s in range(nslots) if s // nT == d]
            day_starts = []
            for idx, s in enumerate(dslots):
                dw = sum(x[i, s, p] for p in P)       # 그 슬롯 근무 여부(0/1)
                prev = sum(x[i, dslots[idx - 1], p] for p in P) if idx > 0 else 0
                ds = m.NewBoolVar(f"dstart_{i}_{s}")
                m.Add(ds >= dw - prev)
                m.Add(ds <= dw)
                m.Add(ds <= 1 - prev)
                day_starts.append(ds)
            m.Add(sum(day_starts) <= 1)   # 하루에 근무 시작은 최대 1번 = 한 덩어리

    # 필수 장소: 사람마다 그 장소에서 최소 1회(=연속 min_run) 근무
    miss_pen = 0
    visit = {}
    for i in people:
        for p in P:
            if not places[p].get("required"):
                continue
            worked_p = sum(x[i, s, p] for s in range(nslots))
            vis = m.NewBoolVar(f"vis_{i}_{p}")
            m.Add(worked_p >= 1).OnlyEnforceIf(vis)
            m.Add(worked_p == 0).OnlyEnforceIf(vis.Not())
            visit[i, p] = vis
            if required_hard:
                m.Add(vis == 1)
            else:
                miss_pen += (1 - vis)

    # 균등
    lmax = m.NewIntVar(0, nslots, "lmax")
    lmin = m.NewIntVar(0, nslots, "lmin")
    for i in people:
        m.Add(lmax >= total[i])
        m.Add(lmin <= total[i])

    W = config.get("weights", {})
    m.Minimize(W.get("required", 5000) * miss_pen
               + W.get("cover", 1000) * cover_pen
               + W.get("balance", 30) * (lmax - lmin)
               + W.get("frag", 8) * sum(starts))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(m)

    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assign = {}
    loads = {}
    unmet_required = []
    if feasible:
        for s in range(nslots):
            for p in P:
                assign[f"{s}_{p}"] = [i for i in people if solver.Value(x[i, s, p]) == 1]
        loads = {i: int(solver.Value(total[i])) for i in people}
        # 필수 장소 미충족자 집계
        for i in people:
            for p in P:
                if places[p].get("required"):
                    if sum(solver.Value(x[i, s, p]) for s in range(nslots)) == 0:
                        unmet_required.append({"name": i, "place": places[p]["name"]})

    return {
        "status": solver.StatusName(status),
        "feasible": feasible,
        "assign": assign,
        "loads": loads,
        "unmet_required": unmet_required,
    }
