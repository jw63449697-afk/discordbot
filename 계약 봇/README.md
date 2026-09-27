# Discord 계약 관리 봇

게임 개발팀 계약자를 관리하는 간단한 Discord 봇입니다. `discord.py` 슬래시 명령어 세 개와 SQLite만 사용합니다.

## 준비 사항

- Python 3.10 이상
- Discord 애플리케이션 및 봇 토큰
- 봇을 초대할 서버의 관리자 권한

## 설치 및 실행

1. 이 폴더에서 가상 환경을 만들고 활성화합니다.

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. 필요한 패키지를 설치합니다.
   ```bash
   python -m pip install -r requirements.txt
   ```

3. `.env.example`을 복사해 `.env` 파일을 만들고 `BOT_TOKEN`에 봇 토큰을 입력합니다.

   **Windows PowerShell**
   ```powershell
   Copy-Item .env.example .env
   ```

   **macOS / Linux**
   ```bash
   cp .env.example .env
   ```

4. Discord Developer Portal의 **Bot > Privileged Gateway Intents** 설정에서 특별한 인텐트를 켤 필요는 없습니다. **OAuth2 > URL Generator**에서 `bot`과 `applications.commands` 스코프를 선택해 생성한 URL로 봇을 서버에 초대하고, 봇에 `View Channels`, `Send Messages`, `Embed Links` 권한을 부여합니다.

5. 봇을 실행합니다.
   ```bash
   python bot.py
   ```

실행할 때 SQLite 데이터베이스 `contracts.db`가 자동 생성되고, 슬래시 명령어 세 개가 자동 동기화됩니다. 전역 명령어 동기화는 Discord 반영까지 시간이 걸릴 수 있습니다.

## 명령어

- `/계약추가 사용자 날짜`: 관리자 전용. 날짜는 `YYYY-MM-DD` 형식이어야 합니다.
- `/계약취소 사용자`: 관리자 전용. 기존 계약 기록은 보존되고 상태만 `CANCELLED`로 바뀝니다.
- `/계약목록`: 모든 서버 멤버가 사용 가능. 현재 `ACTIVE` 계약만 시작일과 이름 기준으로 정렬해 표시합니다.

관리자 명령어는 Discord 명령어 권한 설정과 실행 시 권한 검사를 모두 적용합니다. 계약 추가/취소가 실행된 실제 시각은 UTC ISO 8601 형식으로 DB에 저장됩니다. 취소 응답의 계약 종료일은 명령어를 실행한 서버 로컬 날짜 기준입니다.

## 보안 및 데이터

- 봇 토큰은 `.env`에서 읽으며 `.env`와 `contracts.db`는 Git에서 제외됩니다.
- SQL은 모두 매개변수화해 실행합니다.
- 현재 계약 여부는 Discord 사용자 ID와 `ACTIVE` 상태로 확인하며, 취소된 기록은 삭제하지 않습니다.
- 이 프로젝트의 계약 테이블은 단일 팀/서버에서 사용할 공유 목록입니다.
