# 서니티 AWS 운영 · 배포 · 확장 관리 가이드

이 문서는 서니티 플랫폼 운영 서버와 향후 Motion AI 앱 인프라까지 함께 관리하기 위한 AWS/DevOps 인수인계용 가이드다.  
다른 LLM, 개발자, 운영 담당자에게 전달할 수 있도록 현재 운영 구조, 배포 방식, 주의사항, 확장 방향을 정리한다.

---

## 1. 목적

이 문서의 목적은 다음과 같다.

- 서니티 플랫폼 운영 서버 접속 및 배포 절차 표준화
- 로컬 작업과 서버 작업 구분
- AWS EC2, SSM, IAM, PM2, nginx, GitHub Deploy Key 관리 기준 정리
- 추후 Motion AI 앱을 같은 AWS 계정 또는 분리된 AWS 인프라로 확장할 때 참고할 운영 기준 마련
- 반복 배포 시 불필요한 시행착오 방지

---

## 2. 현재 운영 서버 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | Sunity Funding Platform |
| 운영 도메인 | https://sunity.ai |
| AWS 리전 | ap-northeast-2, 서울 |
| EC2 인스턴스 ID | i-0de9190eb75eec460 |
| 퍼블릭 IP | 15.165.246.207 |
| 내부 IP | 172.31.27.113 |
| OS | Ubuntu 22.04 LTS |
| EC2 타입 | t3.medium |
| 웹 포트 | 80 / 443 |
| 프론트 포트 | 3000 |
| 백엔드 포트 | 12100 |

현재 구조는 다음과 같다.

```text
사용자 브라우저
   ↓
https://sunity.ai
   ↓
nginx 80/443
   ↓
Next.js Frontend : localhost:3000
   ↓
Spring Boot Backend : localhost:12100
```

---

## 3. 접속 방식

### 3.1 로컬 Mac 기준 SSH 접속

메인 SSH 키:

```bash
~/Dev/sunity.pem
```

서버 접속:

```bash
cd ~/Dev
ssh -i sunity.pem ubuntu@ec2-15-165-246-207.ap-northeast-2.compute.amazonaws.com
```

개발사 백업 키:

```bash
~/Dev/sunity11.pem
```

백업 키 접속:

```bash
cd ~/Dev
ssh -i sunity11.pem ubuntu@ec2-15-165-246-207.ap-northeast-2.compute.amazonaws.com
```

### 3.2 접속 후 기본 확인

서버에 접속되면 프롬프트가 아래처럼 바뀐다.

```bash
ubuntu@ip-172-31-27-113:~$
```

기본 확인:

```bash
pwd
whoami
hostname
```

---

## 4. 보안 및 키 관리 주의사항

### 4.1 절대 공유 금지

아래 파일의 내용은 절대 채팅, GitHub, Notion, 문서에 붙여넣지 않는다.

```text
sunity.pem
sunity11.pem
*.pem
개인키 전체 내용
-----BEGIN OPENSSH PRIVATE KEY-----
```

### 4.2 GitHub 업로드 금지

`.gitignore`에는 반드시 아래 패턴을 유지한다.

```gitignore
*.pem
```

### 4.3 공개키와 개인키 구분

| 파일 | 설명 | 공유 가능 여부 |
|---|---|---|
| `sunity.pem` | 개인키 | 공유 금지 |
| `sunity.pub` | 공개키 | 필요 시 공유 가능 |
| `sunity11.pem` | 개발사 백업 개인키 | 공유 금지 |

---

## 5. AWS SSM Session Manager

EC2에는 SSM 접속을 위해 IAM Role이 연결되어 있다.

| 항목 | 내용 |
|---|---|
| IAM Role | SunityEC2SSMRole |
| 주요 정책 | AmazonSSMManagedInstanceCore |
| 용도 | PEM 없이 AWS 콘솔에서 서버 접속 가능하게 함 |

AWS 콘솔에서 접속 경로:

```text
EC2
→ 인스턴스 선택
→ 연결
→ SSM Session Manager
→ 연결
```

SSM으로 접속하면 기본 사용자가 `ssm-user`일 수 있다.  
운영 작업은 `ubuntu`로 전환 후 진행한다.

```bash
sudo -iu ubuntu
```

---

## 6. 서버 주요 경로

프론트 운영 루트:

```bash
/app/web/sunity-web
```

현재 배포 구조:

```text
/app/web/sunity-web
├── deploy.sh
├── ecosystem.config.js
├── releases/
└── current -> releases/타임스탬프
```

각 경로 역할:

| 경로 | 설명 |
|---|---|
| `/app/web/sunity-web` | 프론트 운영 루트 |
| `/app/web/sunity-web/deploy.sh` | 배포 스크립트 |
| `/app/web/sunity-web/ecosystem.config.js` | PM2 실행 설정 |
| `/app/web/sunity-web/releases` | 릴리즈별 빌드 결과 저장 |
| `/app/web/sunity-web/current` | 현재 운영 중인 release 링크 |

---

## 7. PM2 운영 구조

프론트는 root 계정의 PM2에서 실행된다.  
따라서 일반 `pm2`가 아니라 `sudo pm2`를 사용해야 한다.

PM2 상태 확인:

```bash
sudo pm2 status
```

현재 앱 이름:

```text
sunity-web
```

PM2 설정 파일:

```bash
/app/web/sunity-web/ecosystem.config.js
```

설정 핵심:

```js
module.exports = {
  apps: [
    {
      name: "sunity-web",
      cwd: "/app/web/sunity-web/current",
      script: "yarn",
      args: "start -p 3000",
      exec_mode: "cluster",
      instances: 2,
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
    },
  ],
};
```

PM2 로그 확인:

```bash
sudo pm2 logs sunity-web --lines 100
```

---

## 8. GitHub 연결 구조

GitHub 저장소:

```text
sunity3412/sunity-funding
```

서버에는 GitHub Deploy Key가 등록되어 있다.

서버 SSH config Host:

```text
github-sunity-funding
```

GitHub 연결 테스트:

```bash
ssh -T github-sunity-funding
```

정상 메시지 예시:

```text
Hi sunity3412/sunity-funding! You've successfully authenticated, but GitHub does not provide shell access.
```

remote 확인:

```bash
cd /app/web/sunity-web
git remote -v
```

정상 형태:

```text
origin github-sunity-funding:sunity3412/sunity-funding.git (fetch)
origin github-sunity-funding:sunity3412/sunity-funding.git (push)
```

최신 커밋 확인:

```bash
git fetch origin main
git log --oneline origin/main -3
```

---

## 9. 저장소 구조

GitHub는 모노레포 구조다.

```text
sunity-funding
├── docs
├── sunity-admin
├── sunity-server
└── sunity-web
```

프론트 배포 시에는 `origin/main` 전체가 아니라 `origin/main:sunity-web`만 추출해야 한다.

핵심 명령:

```bash
git archive origin/main:sunity-web | tar -x -C "$NEW_RELEASE"
```

---

## 10. 일반 배포 루틴

### 10.1 로컬 Mac에서 작업

로컬 프로젝트 경로:

```bash
cd ~/Dev/Sunityfunding
```

수정 후 확인:

```bash
git status
git diff
```

커밋 및 푸시:

```bash
git add .
git commit -m "fix: 수정 내용"
git push origin main
```

### 10.2 서버 접속

```bash
cd ~/Dev
ssh -i sunity.pem ubuntu@ec2-15-165-246-207.ap-northeast-2.compute.amazonaws.com
```

### 10.3 서버에서 배포

```bash
cd /app/web/sunity-web
./deploy.sh
```

### 10.4 배포 후 확인

```bash
sudo pm2 status
curl -I http://localhost:3000
curl -I https://sunity.ai
```

정상 응답 예시:

```text
HTTP/1.1 200 OK
```

브라우저 확인:

```text
https://sunity.ai
```

강력 새로고침:

```text
Cmd + Shift + R
```

---

## 11. deploy.sh 역할

현재 `deploy.sh`는 다음 작업을 자동화한다.

```text
1. git fetch origin main
2. 새 releases/타임스탬프 폴더 생성
3. origin/main:sunity-web만 추출
4. .env 파일 복사
5. yarn install --frozen-lockfile
6. yarn build
7. current 링크 교체
8. sudo pm2 reload sunity-web
9. sudo pm2 save
10. 오래된 release 정리
```

수동으로 매번 오늘처럼 할 필요 없이, 다음부터는 보통 아래만 실행하면 된다.

```bash
cd /app/web/sunity-web
./deploy.sh
```

---

## 12. 장애 대응 및 롤백

### 12.1 배포 실패 시

빌드 실패가 발생하면 `current` 링크가 교체되기 전이므로 운영 반영이 되지 않는다.  
이 경우 기존 사이트는 유지된다.

확인:

```bash
ls -la /app/web/sunity-web/current
sudo pm2 status
```

### 12.2 운영 반영 후 문제 발생 시

이전 release 목록 확인:

```bash
ls -1dt /app/web/sunity-web/releases/*
```

이전 release로 롤백:

```bash
cd /app/web/sunity-web
sudo ln -sfn /app/web/sunity-web/releases/이전타임스탬프 /app/web/sunity-web/current
sudo pm2 reload sunity-web --update-env
sudo pm2 save
```

상태 확인:

```bash
sudo pm2 status
curl -I https://sunity.ai
```

---

## 13. 운영 주의사항

### 13.1 로컬 작업과 서버 작업 구분

항상 아래처럼 구분한다.

```text
[로컬 Mac에서]
- 코드 수정
- git add / commit / push

[서버 EC2에서]
- git fetch
- ./deploy.sh
- pm2 상태 확인

[AWS 콘솔에서]
- EC2, IAM, SSM, 보안그룹 확인

[GitHub에서]
- Deploy Key, 저장소, 커밋 확인
```

### 13.2 PM2는 sudo 사용

프론트는 root PM2에서 실행 중이다.

```bash
sudo pm2 status
```

일반 `pm2 status`는 ubuntu 계정 PM2라서 비어 있을 수 있다.

### 13.3 서버 재부팅 주의

서버 접속 시 아래 메시지가 보일 수 있다.

```text
*** System restart required ***
```

무작정 재부팅하지 않는다.  
운영 중 재부팅은 사전 점검 후 진행한다.

### 13.4 assets 누락 주의

프론트 빌드에서 이미지, SVG, 컴포넌트가 누락되면 아래 형태로 실패할 수 있다.

```text
Module not found: Can't resolve '@/assets/icons/...'
Module not found: Can't resolve '@/components/...'
```

이 경우 로컬 Git에서 누락 파일이 추적되고 있는지 확인한다.

```bash
git status
git ls-files | grep "src/assets/icons"
```

`.gitignore` 때문에 assets가 무시되는 경우 강제 추가가 필요할 수 있다.

```bash
git add -f -- sunity-web/src/assets/icons/*.svg
git add -f -- sunity-web/src/components/필요컴포넌트.tsx
```

---

## 14. 권한 문제 대응

서버에서 아래 에러가 발생할 수 있다.

```text
error: insufficient permission for adding an object to repository database .git/objects
fatal: failed to write object
```

이 경우 `.git` 내부 권한 문제일 가능성이 높다.

해결:

```bash
cd /app/web/sunity-web
sudo chown -R ubuntu:ubuntu .git
git fetch origin main
```

release 폴더 생성 권한 문제:

```text
mkdir: cannot create directory ... Permission denied
```

해결:

```bash
sudo mkdir -p "$NEW_RELEASE"
sudo chown -R ubuntu:ubuntu "$NEW_RELEASE"
```

---

## 15. nginx 확인

nginx 상태 확인:

```bash
sudo systemctl status nginx --no-pager
```

포트 확인:

```bash
sudo ss -lntp | grep -E ':80|:443|:3000|:12100'
```

예상 구조:

```text
80/443 → nginx
3000 → next-server
12100 → java spring boot
```

nginx 설정 확인:

```bash
sudo nginx -t
ls -la /etc/nginx/sites-enabled
sudo cat /etc/nginx/sites-enabled/*
```

---

## 16. Motion AI 확장 방향

향후 Motion AI 앱을 추가할 때는 기존 플랫폼과 무작정 같은 서버에 올리기보다, 역할을 분리하는 방향을 우선 검토한다.

### 16.1 추천 구조

```text
sunity.ai
├── 기존 플랫폼
│   ├── EC2: Next.js + Spring Boot
│   ├── RDS 또는 DB
│   └── S3/이미지 리소스
│
└── Motion AI
    ├── 별도 API 서버
    ├── 영상 업로드 저장소 S3
    ├── 분석 작업 큐
    ├── AI 모델 API 또는 GPU 서버
    └── 결과 리포트 저장소
```

### 16.2 Motion AI에서 고려할 AWS 리소스

| 기능 | 후보 |
|---|---|
| 영상 업로드 | S3 |
| 영상 분석 요청 | API Gateway 또는 EC2/Nest/Spring API |
| 비동기 작업 | SQS |
| AI 분석 처리 | 외부 AI API, EC2 GPU, ECS, Lambda 일부 |
| 결과 저장 | RDS, S3 |
| 이미지/영상 배포 | CloudFront |
| 인증 | 기존 플랫폼 계정 연동 또는 Cognito 검토 |
| 로그 | CloudWatch |
| 비밀키 관리 | Parameter Store 또는 Secrets Manager |

### 16.3 분리 기준

Motion AI는 영상 업로드, 분석, AI 처리 비용이 크므로 기존 플랫폼과 서버를 분리하는 것이 좋다.

분리 추천 기준:

```text
1. 영상 업로드 용량이 크다
2. AI 분석 시간이 길다
3. 요청이 몰리면 기존 플랫폼에 영향이 간다
4. GPU 또는 외부 AI API 비용 관리가 필요하다
5. 사용자별 분석 결과 보안 관리가 필요하다
```

---

## 17. 비용 관리 방향

현재 플랫폼 운영 비용 외에 Motion AI를 추가하면 비용 증가 요인이 생긴다.

주의할 비용 항목:

```text
EC2 인스턴스 비용
RDS 비용
S3 저장 비용
CloudFront 트래픽 비용
AI API 비용
GPU 서버 비용
로그 저장 비용
백업 스냅샷 비용
```

운영 원칙:

```text
1. 영상 원본 저장 기간 제한
2. 분석 결과만 장기 보관
3. S3 lifecycle 정책 적용
4. CloudWatch 로그 보관 기간 설정
5. GPU 서버는 상시 구동보다 작업형 구조 검토
6. 비용 알림 설정 필수
```

---

## 18. 보안 관리 방향

### 18.1 AWS 계정 보안

- MFA는 서니티 측 인증기로 관리한다.
- 루트 계정 사용은 최소화한다.
- 운영자별 IAM User 또는 IAM Identity Center 사용을 검토한다.
- 장기 액세스 키는 최소화한다.

### 18.2 서버 보안

- SSH 22번은 필요한 IP만 허용한다.
- 가능하면 SSM Session Manager 중심 운영으로 전환한다.
- PEM 키는 로컬 안전한 위치에 보관한다.
- 퇴사자/외부 개발사 키는 정기적으로 정리한다.

### 18.3 애플리케이션 보안

- `.env` 파일은 GitHub에 올리지 않는다.
- API Key, DB Password, OAuth Secret은 코드에 하드코딩하지 않는다.
- 추후 Parameter Store 또는 Secrets Manager로 이전 검토한다.

---

## 19. 다음에 해야 할 정리 작업

우선순위 높은 순서:

```text
1. deploy.sh가 실제 다음 배포에서도 정상 작동하는지 소규모 수정 때 확인
2. GitHub에 필요한 assets가 모두 추적되는지 확인
3. 운영 서버의 current/release 구조 문서화
4. 백업 키 sunity11.pem 안전 보관
5. SSM Session Manager 접속 유지 확인
6. AWS 비용 알림 설정
7. Motion AI 별도 인프라 설계 초안 작성
8. 서버 재부팅 필요 메시지에 대한 점검 일정 수립
```

---

## 20. 다른 LLM에게 전달할 운영 지침

이 문서를 전달받은 LLM은 다음 원칙을 지켜야 한다.

```text
1. 사용자에게 로컬 작업과 서버 작업을 반드시 구분해서 안내한다.
2. pem 파일 내용을 요구하지 않는다.
3. 운영 서버에서 명령 실행 전 영향 범위를 설명한다.
4. deploy.sh 실행 전 git push 여부를 확인한다.
5. PM2 명령은 sudo pm2 기준으로 안내한다.
6. 모노레포 구조이므로 sunity-web만 배포 대상으로 본다.
7. 장애 시 먼저 current 링크와 releases 폴더를 확인한다.
8. 불필요한 AWS 리소스 생성은 피한다.
9. Motion AI 확장 시 기존 플랫폼 서버에 무리하게 얹지 않는다.
10. 사용자가 초보 운영자임을 전제로 단계별로 짧게 안내한다.
```

---

## 21. 빠른 명령어 모음

### 서버 접속

```bash
cd ~/Dev
ssh -i sunity.pem ubuntu@ec2-15-165-246-207.ap-northeast-2.compute.amazonaws.com
```

### 서버 배포

```bash
cd /app/web/sunity-web
./deploy.sh
```

### PM2 상태

```bash
sudo pm2 status
```

### 프론트 확인

```bash
curl -I http://localhost:3000
curl -I https://sunity.ai
```

### GitHub 최신 커밋 확인

```bash
cd /app/web/sunity-web
git fetch origin main
git log --oneline origin/main -3
```

### 포트 확인

```bash
sudo ss -lntp | grep -E ':80|:443|:3000|:12100'
```

---

## 22. 최종 운영 루틴 요약

```text
[로컬 Mac]
1. 코드 수정
2. git status
3. git add .
4. git commit -m "..."
5. git push origin main

[서버 EC2]
6. ssh -i sunity.pem ubuntu@ec2-...
7. cd /app/web/sunity-web
8. ./deploy.sh
9. sudo pm2 status
10. curl -I https://sunity.ai

[브라우저]
11. https://sunity.ai 접속
12. Cmd + Shift + R
13. 수정 반영 확인
```

이 문서를 기준으로, 향후 서니티 플랫폼과 Motion AI 인프라를 함께 관리한다.
