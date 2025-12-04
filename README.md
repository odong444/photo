# 📸 사진 관리 시스템

프로젝트별 사진 업로드/다운로드 관리 웹 애플리케이션

## 기능

### 일반 사용자
- 프로젝트 선택 후 사진 업로드
- 업로더 이름 입력으로 구분
- 다중 파일 업로드 지원
- 모바일 친화적 UI

### 관리자
- 프로젝트 생성/수정/삭제
- 업로더별 사진 확인
- 개별/전체 ZIP 다운로드
- 다운로드 상태 표시

---

## 로컬 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일 수정

# 4. 실행
python app.py
```

---

## AWS S3 설정

### 1. S3 버킷 생성

1. AWS 콘솔 → S3 → 버킷 만들기
2. 버킷 이름 입력 (예: `my-photo-manager`)
3. 리전: `ap-northeast-2` (서울)
4. **퍼블릭 액세스 차단** 설정 유지 (보안)
5. 버킷 생성

### 2. IAM 사용자 생성

1. AWS 콘솔 → IAM → 사용자 → 사용자 생성
2. 사용자 이름 입력
3. 권한 → **직접 정책 연결**
4. 정책 생성:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR-BUCKET-NAME",
                "arn:aws:s3:::YOUR-BUCKET-NAME/*"
            ]
        }
    ]
}
```

5. 액세스 키 생성 → Access Key와 Secret Key 저장

### 3. CORS 설정 (버킷)

S3 버킷 → 권한 → CORS 구성:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

---

## 배포 (Render.com)

### 1. GitHub에 코드 푸시

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/photo-manager.git
git push -u origin main
```

### 2. Render.com 설정

1. https://render.com 가입
2. New → Web Service
3. GitHub 연결 → 레포 선택
4. 설정:
   - **Name**: photo-manager
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

5. Environment Variables 추가:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=ap-northeast-2
   S3_BUCKET_NAME=your-bucket
   SECRET_KEY=랜덤문자열
   ADMIN_PASSWORD=관리자비밀번호
   ```

6. Create Web Service

---

## 환경변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 | AKIA... |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키 | ... |
| `AWS_REGION` | AWS 리전 | ap-northeast-2 |
| `S3_BUCKET_NAME` | S3 버킷 이름 | my-photo-bucket |
| `SECRET_KEY` | Flask 시크릿 키 | 랜덤 문자열 |
| `ADMIN_PASSWORD` | 관리자 비밀번호 | admin1234 |
| `DATABASE_URL` | DB URL (선택) | sqlite:///photo.db |

---

## 사용법

### 일반 사용자
1. 메인 페이지에서 프로젝트 선택
2. 이름 입력 + 사진 선택
3. 업로드 버튼 클릭

### 관리자
1. `/admin/login` 접속
2. 비밀번호 입력
3. 프로젝트 관리 / 사진 다운로드

---

## 파일 구조

```
photo_manager/
├── app.py              # 메인 Flask 앱
├── config.py           # 설정
├── models.py           # DB 모델
├── requirements.txt    # 의존성
├── .env.example        # 환경변수 예시
├── templates/          # HTML 템플릿
│   ├── base.html
│   ├── index.html
│   ├── upload.html
│   ├── upload_complete.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   ├── admin_project_form.html
│   └── admin_project_detail.html
└── README.md
```

---

## 예상 비용 (AWS)

10GB 저장 기준:
- S3 저장: ~$0.23/월
- 데이터 전송: ~$0.45/월 (5GB 다운로드)
- **총: ~$1/월 미만**

---

## 라이선스

MIT License
