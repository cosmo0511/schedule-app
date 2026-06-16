import json
from fastapi.testclient import TestClient
import app as A
c=TestClient(A.app)

# 1) 홈/정적
assert c.get("/").status_code==200, "home fail"

# 2) 이벤트 생성 (정문 09-21, 후문/주차장 09-17)
ev=c.post("/api/events",json={
 "title":"테스트 근무","days":["월","화","수","목","금"],
 "day_start":"09:00","day_end":"21:00","slot_minutes":60,
 "min_run_hours":3,"max_day_hours":8,
 "places":[{"name":"정문","cap":2,"priority":3,"op_start":"09:00","op_end":"21:00"},
           {"name":"후문","cap":1,"priority":2,"op_start":"09:00","op_end":"17:00"},
           {"name":"주차장","cap":1,"priority":1,"op_start":"09:00","op_end":"17:00"}]}).json()
eid,tok=ev["event_id"],ev["admin_token"]
print("event:",eid)

# 3) 이벤트 조회 -> times 개수
cfg=c.get(f"/api/events/{eid}").json()["config"]
print("슬롯/일:",len(cfg["times"]),"  주차장 rows:",cfg["places"][2]["rows"])

# 4) 실제 CSV 12명 제출
avail=json.load(open("/sessions/vibrant-wonderful-mendel/mnt/outputs/_avail_csv.json"))
for name,slots in avail.items():
    r=c.post(f"/api/events/{eid}/participants",json={"name":name,"slots":slots})
    assert r.status_code==200
print("제출:",len(c.get(f"/api/events/{eid}/participants").json()),"명")

# 5) 토큰 틀리면 거부
assert c.post(f"/api/events/{eid}/solve?token=WRONG").status_code==403
print("토큰 검증 OK")

# 6) 배정 실행
res=c.post(f"/api/events/{eid}/solve?token={tok}").json()
print("status:",res["status"],"feasible:",res["feasible"])

# 7) 검증: 운영시간 빈칸, 연속 3시간, 하루<=8
nT=len(cfg["times"]); days=cfg["days"]; places=cfg["places"]
need=0;fill=0;blank=0
for s in range(nT*len(days)):
    for pi,p in enumerate(places):
        if (s%nT) in p["rows"]:
            need+=p["cap"]; n=len(res["assign"][f"{s}_{pi}"]); fill+=n
            if n<p["cap"]: blank+=p["cap"]-n
print(f"운영필요 {need} / 채움 {fill} / 빈자리 {blank}")
# 연속/하루 검증
bad_run=[]; bad_day=[]
for name in avail:
    for di in range(len(days)):
        daycnt=0
        for pi in range(len(places)):
            seq=[1 if name in res["assign"][f"{di*nT+ri}_{pi}"] else 0 for ri in range(nT)]
            run=0
            for v in seq+[0]:
                if v: run+=1; daycnt+=v
                else:
                    if 0<run<3: bad_run.append((name,di,pi,run))
                    run=0
        if daycnt>8: bad_day.append((name,di,daycnt))
print("3h미만 토막:",bad_run or "없음 ✓")
print("하루 8h초과:",bad_day or "없음 ✓")
print("loads:",res["loads"])
print("\n전체 흐름 정상 ✅")
