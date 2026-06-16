# 인터넷 배포 가이드 (Render 무료)

이 가이드대로 하면 **어디서나 접속되는 진짜 공유 링크**가 생겨요.
git/터미널 몰라도 괜찮아요 — 전부 웹 화면에서 클릭으로 해요.

대략 15분, 카드 없이 무료.

---

## 1단계 — GitHub에 코드 올리기

1. https://github.com 에서 회원가입(무료) / 로그인.
2. 오른쪽 위 **＋ → New repository** 클릭.
3. Repository name 에 `schedule-app` 입력 → **Public** 선택 → **Create repository**.
4. 다음 화면에서 **uploading an existing file** 링크 클릭.
5. `schedule_app` 폴더 **안에 있는 파일들**을 전부 드래그해서 올려요.
   - ⚠️ 폴더째 말고, 폴더 안의 내용물(`app.py`, `solver.py`, `requirements.txt`, `Procfile`, `render.yaml`, `runtime.txt`, `static` 폴더 등)을 올려야 해요.
   - `static` 폴더도 같이 올라가야 해요(드래그하면 폴더 구조 유지됨).
6. 맨 아래 **Commit changes** 클릭.

> `schedule.db` 파일은 올리지 마세요(자동 생성됨). `.gitignore`가 알아서 빼줘요.

## 2단계 — Render에 연결

1. https://render.com 에서 **GitHub 계정으로 가입**(무료, 카드 X).
2. 대시보드에서 **New + → Web Service**.
3. 방금 만든 `schedule-app` 저장소를 선택(**Connect**).
4. 설정값(보통 자동으로 채워짐):
   - **Language**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
5. **Create Web Service** 클릭 → 빌드가 몇 분 돌아가요(처음엔 OR-Tools 설치로 조금 걸림).
6. 완료되면 위에 `https://schedule-app-xxxx.onrender.com` 같은 **주소**가 떠요. 그게 너의 사이트예요!

이제 그 주소로 들어가면 1단계 설정 화면이 나오고, 거기서 만든 참가자/관리자 링크를 공유하면 끝.

---

## 무료 등급 주의 + 해결 (중요)

Render 무료는 **15분 동안 아무도 안 들어오면 잠들고**, 깰 때 제출 데이터가 초기화될 수 있어요.
며칠에 걸쳐 제출을 받는다면 아래 중 하나로 막아요.

### 방법 A — Keep-alive로 안 잠들게 (가장 쉬움, 무료)
1. https://uptimerobot.com 또는 https://cron-job.org 가입(무료).
2. 새 모니터 만들고 URL에 `https://너의주소.onrender.com/health` 입력.
3. 체크 주기를 **5~10분**으로 설정.
- 이러면 계속 깨어 있어서 제출 데이터가 유지돼요. (제출 다 받고 배정 끝나면 꺼도 됨)

### 방법 B — 영구 저장(Postgres) 연결 (권장, 데이터 안 날아감)
앱은 이미 Postgres를 지원해요. `DATABASE_URL` 환경변수만 넣으면 자동으로 그 DB에 영구 저장돼요(없으면 SQLite 사용).

1. Render 대시보드 → **New + → Postgres** → 이름 입력 → **Free** → **Create Database**.
2. 만들어진 DB 페이지에서 **Internal Database URL** 을 복사(`postgresql://...` 형태).
3. 아까 만든 **Web Service** → **Environment** 탭 → **Add Environment Variable**:
   - Key: `DATABASE_URL`
   - Value: 방금 복사한 URL 붙여넣기
4. **Save Changes** → 자동으로 재배포돼요. 이제 잠들었다 깨어도 제출 데이터가 유지돼요.

> 무료 Postgres는 생성 후 30일이면 만료되니, 한 번의 시간표 라운드(보통 1~2주)엔 충분해요. 만료되면 새로 만들어 URL만 교체하면 돼요.
> 방법 B를 쓰면 방법 A(keep-alive)는 안 해도 데이터는 안전해요. (다만 첫 접속이 1분 느린 건 keep-alive로 같이 막을 수 있어요.)

---

## 자주 묻는 것
- **빌드 실패(메모리)**: 무료 등급은 RAM 512MB라 가끔 빠듯해요. 다시 Deploy 누르면 대부분 해결.
- **첫 접속이 느려요**: 잠들었다 깨는 중이라 1분쯤 걸려요(방법 A로 예방).
- **주소 바꾸고 싶어요**: Render 서비스 Settings에서 이름 변경 가능.

막히는 단계가 있으면 화면 캡처해서 보여주면 같이 풀어줄게요.
