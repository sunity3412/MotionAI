// 공급자 링크 페이지 문구 단일 출처 (Phase 38 — UI-SPEC §Copywriting 글자 단위 정본).
//
// 규율은 authCopy.ts 와 같다: 화면 파일(38-10/38-11 Expo 라우트 · 38-12 단일 HTML)에는
// 한국어 리터럴을 두지 않고 이 객체만 읽는다. 문구가 두 곳에 있으면 갈린다(메모리
// llm-tips: 문장 결함은 소비처 표부터) — belle 이 한 곳만 보게 한다.
//
//   · Figma 문자열은 그대로(CONTEXT D-22) — 출처 노드는 UI-SPEC 표의 `[1:xxx]` 열.
//   · `guide.*` 는 docs/supplier-guide.md 와 글자 단위로 같다 — supplierCopy.test.ts 가
//     md 를 읽어 대조한다. 한쪽을 고치면 다른 쪽도 같이.
//   · `row.fail.<code>` 8개(no_human 제외)는 `title + '. ' + body` 가 analysis.ts
//     REGISTRATION_ERROR_MESSAGE(= models.py = contract.md §5)와 같다 — 같은 테스트가 잠근다.
//     no_human 만 D-09 예외(기존 ERROR_MESSAGE.no_human 재사용, 여기 문구는 Figma 1:479).
//   · UI-SPEC §Decisions "ui-checker flags (2026-09-26)" 표의 적용값이 §Copywriting 원문보다
//     우선한다 — 해당 키에 `// ui-checker flag #n` 을 달았다.
//   · `{score}` `{joints}` `{name}` `{email}` `{n}` `{durationSec}` `{sizeMB}` `{pct}`
//     `{athlete}` `{level}` `{file}` `{meta}` 는 치환 자리 — 소비처가 String.replace 만 한다(HTML/JSX 로 해석하지 않는다, T-38-03-2).
//   · 숫자 상수(재현성 문턱 SELF_SCORE_OK_MIN 등)는 여기 두지 않는다 — lib/supplierRules.ts.
//   · 실증은 무료라 돈에 관한 문구가 없다(D-13). 기술 용어(RTMW·DTW·conf) 없음. 이모지 없음.
//   · 2026-09-30 38-DESIGN.md(Figma 282:506)가 표시 문구 일부를 바꿨다 — 이 파일이 여전히 단일 출처.
//     재량 판단 2건: (a) form.uploading.summaryTitle/summaryMeta/pct · row.self.scoreText 는
//     38-DESIGN 키 요약에 없지만 A-5·A-3c 화면 파일에 ` · `·'점'·'%' 리터럴을 두지 않으려고 추가.
//     (b) form.sec1.guideLink 는 키 요약에서 빠졌으나 A-4 본문이 '자세한 가이드' 를 명시해 따른다.
//   · 2026-09-30 38-DESIGN-v2(quick-260930-lfw)가 A-2 를 메일 초대판으로 바꾸고 홈 코드 카드·빌드
//     라벨을 지웠다 — noAccess 는 v2 문구, home.codeRow · bigCode 는 새 키, 옛 ID·코드 카드 키는 삭제.
//   · 2026-09-30 quick-260930-w9l — belle 폰 확인 뒤 수정(필수 표시·동의 2·학습 계약 안내·5초~2분·
//     1GB·소리 서버 제거·선언 3 삭제·선수 이름 고정·초급). form.sec3 · sec2.combo · sec5.silent/
//     training/trainingNote/withdraw/tagOptional · row.done.info.split/hold/stand 는 지웠다.

export const supplierCopy = {
  common: {
    guideLink: '촬영 가이드',
    back: '뒤로',
    retry: '다시 시도',
    copied: '복사됐어요', // 38-DESIGN-v2 A-3 강사 코드 줄 복사 토스트
    copyFallback: '길게 눌러 복사해 주세요',
    signOut: '다른 계정으로 로그인',
    cancel: '올리기 취소', // ui-checker flag #2 — A-5 진행 패널의 링크가 업로드 중단임을 말한다
    close: '닫기',
    toList: '목록으로',
    seeAll: '전체보기',
    offline: '연결이 안 돼요. 인터넷을 확인한 뒤 다시 시도해주세요.',
  },

  // A-1 로그인 전 (Figma 1:960 + 1:977)
  login: {
    title: '시작해 볼까요?',
    body: '기준 동작을 올리는 강사·선수를 위한 페이지예요. 앱과 같은 Google 계정으로 시작해 주세요.',
    chip: '강사·선수 전용', // 38-DESIGN A-1
    google: 'Google로 시작하기',
    busy: '로그인 중...',
    sameAccountHint: '앱에서 쓰는 Google 계정과 같으면 하나의 ID로 연결돼요.',
    popupBlocked: '로그인 창이 열리지 않았어요. 브라우저의 팝업 차단을 풀고 다시 시도해주세요.',
    failed: '로그인에 실패했어요. 잠시 후 다시 시도해주세요.',
  },

  // 38-DESIGN-v2 A-2 초대받은 분만 (Figma 283:543 v2) — 로그인했는데 403 not_invited.
  // 만료·없음·취소·메일 미인증을 나누지 않는 화면 하나(리서치 권고). 내 ID·ID 복사·등록 확인하기는 없다.
  noAccess: {
    title: '초대받은 분만 쓸 수 있어요',
    body: '공급자 페이지는 Sunity가 초대한 강사·선수만 쓸 수 있어요. 초대 메일을 받은 Google 계정으로 로그인해 주세요.',
    accountLabel: '지금 로그인한 계정',
    helpTitle: '초대가 필요하거나 계정이 헷갈리면',
    helpBody: '아래로 알려 주세요. 운영팀이 확인해 드려요.',
    kakaoTitle: '카카오톡 채널로 문의',
    kakaoUrl: 'http://pf.kakao.com/_CyNxkn',
    mailTitle: '메일로 문의',
    mailSub: 'cs@sunity.ai',
    mailUrl: 'mailto:cs@sunity.ai',
    checking: '확인하는 중...',
  },

  // A-3 메인 (Figma 1:717 · 1:743 · 1:646)
  home: {
    title: '공급자 페이지',
    identity: '{name} · {email}',
    motionsTitle: '내 동작',
    motionsSub: '올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요.',
    count: '{n}개', // 38-DESIGN A-3 내 동작 카드 머리 오른쪽
    upload: '동작 올리기', // 38-DESIGN A-3 — '>' 대신 쉐브론 아이콘(ui-checker flag #4 대체)
    emptyStep: 'STEP 1',
    emptyTitle: '첫 동작을 올려보세요',
    emptyBody: '올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. 올리기 전에 촬영 전 체크 3가지를 확인해 주세요.',
    // 안내 알약 2줄(Figma 1:399 문법 재사용 — Decisions 21)
    podDown: ['분석 서버가 꺼져 있어요.', '켜지면 올린 동작을 이어서 처리해요.'],
    listError: '목록을 불러오지 못했어요.',
    // 38-DESIGN-v2 A-3 — 시트 맨 위 강사 코드 한 줄(코드가 있을 때만). 옛 '내 코드' 카드는 지웠다.
    codeRow: { label: '내 강사 코드', copy: '복사', big: '크게 보기' },
  },

  // 38-DESIGN-v2 크게 보기 (Figma 299:666) — 흰 전체 화면 모달, 투명도로만 열고 닫는다.
  bigCode: {
    title: '{name} 강사님의 코드',
    titleNoName: '내 강사 코드',
    how: 'Sunity 앱 → 마이 → 강사 코드에\n이 코드를 넣어 주세요',
  },

  // A-3 행 · A-3b 실패 상세 · A-3c 완료 상세. 부제 = `{레벨} · {상태어}`(38-DESIGN A-3, 레벨 라벨은
  // form.sec2.level.options), 날짜 `YYYY.MM.DD`.
  row: {
    status: {
      // quick-261001-thx(belle 2026-10-01 "아주 심플하게") — 승인 전 상태(registering · queued · processing ·
      // review)는 공급자에게 한 문구로만 보인다. 실패·만료·승인 뒤 문구는 따로.
      checking: '확인 중 · 끝나면 수강생에게 보여요',
      newlyAdded: '새로 추가됨',
      self: '재현성 {score}점',
      selfLow: '재현성 {score}점 · 다시 찍어 주세요',
      failed: '등록 안 됨 · 눌러서 이유 보기',
      expired: '업로드가 끝나지 않았어요 · 다시 올리기', // 리뷰 R4
    },
    // 만료 패널(리뷰 R4) — 코드 칩·TIP 없이 제목·본문 + 다시 올리기
    expired: {
      title: '업로드가 끝나지 않았어요',
      body: '영상이 끝까지 올라가지 않아 등록을 시작하지 못했어요. 같은 정보로 다시 올려주세요.',
    },
    done: {
      title: '등록됐어요',
      sub: '{name} · {athlete} 선수', // 38-DESIGN A-3c
      // A-3c 정보 표 라벨(동작 이름 · 선수 · 레벨 · 등록일). 스플릿·유지·서 있는 시작 행은
      // w9l 에서 지웠다(폼이 더는 묻지 않는다).
      info: {
        name: '동작 이름',
        athlete: '선수',
        level: '레벨',
        registeredAt: '등록일',
      },
    },
    // 자기 재현성 카드(D-10, 38-DESIGN A-3c). 옛 한 줄(ok)을 제목 + `{score}점` + 본문으로
    // 나눴다. okBody 가 리뷰 R11 취지(높은 점수 = 정확도 증명이 아니라 추출·저장·재분석이
    // 일관됐다는 진단)를 잇고, note 가 그 아래 항상 붙는다(D-11). 점수는 카드 오른쪽
    // scoreText 한 자리에만 — 본문(okBody·lowBody)엔 숫자를 다시 쓰지 않는다.
    self: {
      title: '자기 영상 재분석',
      scoreText: '{score}점',
      pending: '본인 재현성 확인 중',
      queued: '본인 재현성 확인 대기 중 · 분석 서버가 켜지면 이어서 해요',
      okBody: '관절 읽기와 저장이 일관돼요.',
      note: '동작 정확도는 시험 영상으로 따로 봐요.',
      lowBody: '점수가 낮아요. 관절을 잘못 읽었을 수 있으니 다시 찍어 주세요.',
      failed: '본인 재현성을 확인하지 못했어요. 운영팀에 알려주세요.',
    },
    reupload: '다시 올리기',
    tipHead: '촬영 팁', // 느낌표 없음(문구 규칙, 261001-thx). Figma 1:482 원문은 '촬영 TIP!'
    // TIP 카드 줄은 Figma 1:482 문법대로 `· ` 를 문구 안에 가진다(loading.tsx 와 같다).
    tip: [
      '· 기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)',
      '· 밝은 실내, 역광 없이, 한 사람만',
      '· 길이는 5초~2분',
    ],
    // 등록 실패 문구(D-09 + 리뷰 R9). no_human 만 Figma 1:479 원문(계약 문구와 다른 의도된
    // 예외). 나머지 8개는 title + '. ' + body = REGISTRATION_ERROR_MESSAGE[code].
    // low_confidence 의 {joints} 는 부위명을 ' · ' 로 이은 문자열로 치환한다(supplierRules.failCopy).
    // rejected(quick-261001-thx) 의 {reason} 은 운영자가 적은 반려 사유 — 사유가 없으면 그 문장을 뺀다.
    // multiple_people · no_standing_start · low_confidence 는 2026-10-01 부터 서버가 더 내지 않는다
    // (진단으로 내림) — 그 전 실패 doc 을 보여 주려고 남긴다.
    fail: {
      no_human: {
        title: '영상 안에 사람이 보이지 않아요',
        body: '전신이 화면에 들어오게 촬영해주세요.',
      },
      multiple_people: {
        title: '영상에 여러 사람이 나와요',
        body: '한 사람만 나오게 다시 촬영해 주세요.',
      },
      no_standing_start: {
        title: '서 있는 자세로 시작하지 않았어요',
        body: '서 있는 자세에서 시작해 주세요. 폴 옆에 서서 1초쯤 있다가 동작을 시작하면 돼요.',
      },
      low_confidence: {
        title: '일부 관절을 못 읽었어요',
        body: '잘 안 보인 부위: {joints}. 밝은 곳에서, 옷과 배경이 구분되게 다시 촬영해 주세요.',
      },
      too_short: {
        title: '영상이 너무 짧아요',
        body: '기준 동작은 5초 이상이어야 해요. 동작 전체가 담기게 다시 올려주세요.',
      },
      too_long: {
        title: '영상이 너무 길어요',
        body: '기준 동작은 2분 이내로 올려주세요.',
      },
      too_large: {
        title: '용량이 너무 커요',
        body: '1GB 이하 영상으로 다시 올려주세요.',
      },
      server_error: {
        title: '등록 중 문제가 생겼어요',
        body: '잠시 후 다시 올려주세요. 계속 그러면 운영팀에 알려주세요.',
      },
      rejected: {
        title: '운영팀 확인에서 등록되지 않았어요',
        body: '이유: {reason}. 고쳐서 다시 올려 주세요.',
      },
    },
  },

  // A-4 올리기 폼 STEP 01 / 02 (Figma 1:960 골격) · A-5 업로드 진행 → 결과
  form: {
    step1: { label: 'STEP 01 / 02', title: '동작 정보' },
    step2: { label: 'STEP 02 / 02', title: '동의' },
    next: '다음',
    submit: '올리기',
    remaining: '필수 항목 {n}개가 남았어요',
    // 필수 칸 라벨 옆 표시(w9l 항목 2) — CheckboxRow 의 [필수] 태그와 같은 모양(brand 700).
    requiredTag: '필수',
    // ① 촬영 전 체크 (TIP 카드 문법 + 확인 체크 1개)
    sec1: {
      title: '촬영 전 체크',
      items: [
        '· 세로로, 삼각대나 거치대에 고정해서 찍었어요. 손으로 들고 찍지 않았어요.',
        '· 폴 전체(천장~바닥)와 몸 전체가 동작 내내 화면 안에 있어요. 카메라는 약 4~5m 떨어져 있어요.',
        '· 한 사람만 나오고, 밝은 실내예요. 창을 등지지 않았어요.',
      ],
      confirm: '위 3가지를 확인했어요',
      guideLink: '자세한 가이드', // 38-DESIGN A-4 ① 체크 행 오른쪽 링크
      error: '촬영 전 체크를 확인해주세요.',
    },
    // ② 동작 정보
    sec2: {
      title: '동작 정보',
      name: {
        label: '동작 이름',
        placeholder: '동작을 고르세요',
        newOption: '새 동작 (직접 입력)',
        newPlaceholder: '동작 이름을 입력하세요',
        // 리뷰 R7 — 이름은 보관만, 채점 변화 약속 없음(D-07 범위 = 보관까지).
        helper:
          '동작 이름은 등록 정보로 보관해요. 지금은 정은지 선수 기준 영상과 같은 기본 비교 방식으로 채점해요. 동작별 채점 규칙은 다음 단계에서 더해요.',
        error: '동작 이름을 고르거나 입력해주세요.',
      },
      // w9l 항목 10 — 입력 칸이 아니라 읽기 전용(초대 때 이름 = probe displayName). 없으면 missing.
      athlete: {
        label: '선수 이름',
        helper:
          '초대할 때 확인한 실명이에요. 앱의 기준 동작 목록에 이 이름으로 보여요. 바꾸려면 운영팀에 알려주세요.',
        missing: '선수 이름이 아직 등록되지 않았어요. 운영팀에 알려주시면 등록해 드려요.',
      },
      level: {
        label: '레벨',
        // 앱 picker 탭(reference.tsx TABS)과 같은 라벨 — SkillLevel 키 그대로.
        // w9l 항목 1 — basic 표시 '초급'(belle 09-30). 키 'basic' 불변.
        options: { basic: '초급', intermediate: '중급', advanced: '고급' },
        helper: '앱에서 이 레벨 탭에 보여요.',
        error: '레벨을 골라 주세요.',
      },
    },
    // ④ 영상 파일 (Figma 1:407 카드 + 1:399 알약 자리)
    sec4: {
      title: '영상 파일',
      card: { title: '앨범에서 선택', sub: '저장된 영상(mp4, mov)' },
      pill: [
        '기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)',
        '5초~2분 · 1GB 이하 · 소리는 자동으로 지워요',
      ],
      repick: '다른 파일 선택',
      meta: '{durationSec}초 · {sizeMB}MB',
      previewHint: '미리보기에서 폴 전체와 몸 전체가 보이는지 확인해 주세요.',
      err: { required: '영상을 선택해주세요.' },
    },
    // ⑤ 동의 (STEP 02, Figma 1:1064 골격). w9l 항목 4·5·11(belle 09-30): '[필수] ○○ 동의 · 보기 >'
    // 두 줄 + 필수 안내 한 줄 + 학습 안내 한 줄. 학습은 체크박스가 아니라 공급자 계약이 근거다.
    // 긴 설명(무엇을 허락하는지·철회)은 '보기' → 가이드 s5 로 옮겼다.
    sec5: {
      all: '전체 동의',
      tagRequired: '[필수]',
      portrait: '초상·성명 사용 동의',
      usage: '영상 이용 동의',
      view: '보기',
      allHint: '필수 2개', // 38-DESIGN A-4 STEP 02 전체 동의 상자 오른쪽
      requiredNote: '필수 항목에 동의하지 않으면 등록할 수 없어요.',
      trainingNotice:
        '올린 영상은 공급자 계약에 따라 Sunity AI 학습에도 쓰여요. 학습용 영상과 데이터는 외부에 공개하거나 넘기지 않아요.',
      error: '필수 동의 2가지에 체크해주세요.',
    },
    sessionExpired: '로그인이 만료됐어요. 다시 로그인해주세요.',
    presignFail: '요청을 보내지 못했어요. 잠시 후 다시 시도해 주세요.',
    // A-5 진행 패널(38-DESIGN A-5). 옛 progress 한 줄을 progressLabel + pct 두 조각으로.
    uploading: {
      title: '올리는 중',
      progressLabel: '올리는 중',
      pct: '{pct}%',
      keepOpen: '화면을 닫지 마세요. 다 올라가면 목록으로 돌아가요.',
      summaryTitle: '{name} · {level}',
      summaryMeta: '{file} · {meta}',
    },
    uploaded: { toast: '동작을 올렸어요. 운영팀 확인이 끝나면 앱에 보여요.' },
    uploadFail: {
      title: '올리지 못했어요',
      body: '인터넷 연결이 끊겼거나 올리는 시간이 너무 오래 걸렸어요. 다시 올려 주세요.',
      retry: '다시 올리기',
      home: '처음으로',
    },
  },

  // 검증 다이얼로그 (A-4 ④, Figma 1:499 형식: 제목 + 2줄 + 닫기 / 다른 파일 선택).
  // format 은 Figma 확정 문구(pickerFailure.ts 와 같은 원문, 한 글자도 바꾸지 않는다). tooLarge 는
  // 제목만 같고 본문이 1GB 다 — 공급자 기준 등록만 1GB(belle 09-30, w9l 항목 7), 수강생은 100MB.
  dialog: {
    format: {
      title: '지원할 수 없는 파일이에요',
      lines: ['mp4, mov형식의 영상만', '업로드 가능해요.'],
    },
    tooLarge: {
      title: '용량이 너무 커요',
      lines: ['1GB 이하 영상만 올릴 수 있어요.', '영상을 잘라서 다시 시도해 주세요.'],
    },
    tooShort: {
      title: '영상이 너무 짧아요',
      lines: ['기준 동작은 5초 이상이어야 해요.', '동작 전체가 담긴 영상을 다시 선택해주세요.'],
    },
    tooLong: {
      title: '영상이 너무 길어요',
      lines: ['기준 동작은 2분 이내로 올릴 수 있어요.', '동작이 담긴 부분만 잘라서 다시 선택해주세요.'],
    },
    unreadable: {
      title: '영상을 처리하지 못했어요',
      lines: ['영상은 선택했지만 읽는 중에 문제가 생겼어요.', '다른 영상으로 다시 시도해주세요.'],
    },
  },

  // A-6 상세 가이드 = docs/supplier-guide.md 정본(D-18 7항목). 화면과 md 가 글자 단위로 같다.
  guide: {
    title: '촬영과 등록 가이드',
    sub: '정은지 선수 기준 영상과 같은 조건으로 찍으면 돼요.',
    s1: {
      h: '어떻게 찍나요',
      items: [
        '폰을 세로로 세워요.',
        '삼각대나 거치대에 고정해요. 손으로 들고 찍으면 흔들려서 관절을 잘못 읽어요.',
        '카메라 높이는 허리와 가슴 사이예요. 폴이 화면에서 똑바로 서 있게 맞춰요.',
        '폴 전체(천장부터 바닥까지)와 몸 전체가 동작 내내 화면 안에 있어야 해요. 보통 4~5m 떨어지면 돼요.',
        '밝은 실내에서 찍어요. 창을 등지면 몸이 검게 나와서 관절을 못 읽어요.',
        '화면에는 한 사람만 나오게 해요. 뒤로 지나가는 사람도 없어야 해요.',
        '시작 방향은 정해져 있지 않아요. 동작이 가장 잘 보이는 방향으로 찍되, 한 영상 안에서는 카메라를 움직이지 않아요.',
      ],
      caption: '이 정도 거리와 높이면 돼요 — 정은지 선수 기준 영상 프레임',
    },
    // w9l 항목 6·8 — 5초~2분 하나(콤보도 같은 한도), 소리는 서버가 지운다, 1GB.
    s2: {
      h: '길이와 시작',
      items: [
        '길이는 5초~2분이에요. 동작 하나도, 여러 동작을 이은 콤보도 올릴 수 있어요.',
        '가능하면 폴 옆에 서서 1초쯤 있다가 시작해 주세요. 서 있는 순간이 발 높이를 재는 기준이 돼요.',
        '소리는 신경 쓰지 않아도 돼요. 등록할 때 영상의 소리를 지워서 저장해요.',
        '영상 파일은 1GB까지 올릴 수 있어요.',
      ],
    },
    // 리뷰 R7 — 이름은 보관만, 채점 변화 약속 없음. w9l 항목 9·10 — 선언 3 삭제, 선수 이름 고정.
    s3: {
      h: '올릴 때 무엇을 적나요',
      items: [
        '동작 이름: 목록에 있는 동작을 고르거나 새 이름을 적어요. 이름은 등록 정보로 보관해요. 지금은 기본 비교 방식으로 채점하고, 동작별 채점 규칙은 다음 단계에서 더해요.',
        '레벨: 초급·중급·고급 중에서 골라요. 앱에서 이 레벨 탭에 보여요.',
        '선수 이름: 초대할 때 확인한 실명으로 정해져 있어요. 바꾸려면 운영팀에 알려주세요.',
      ],
    },
    // quick-261001-thx(belle 2026-10-01) — 등록 = 자동 읽기 + 운영팀 확인. 막는 것은 사람을 못 찾을 때뿐이라
    // 옛 '등록이 안 되는 4가지' 를 '잘 찍는 팁' 으로 바꿨다. 재현성 점수 설명 두 줄은 지웠다.
    s4: {
      h: '올리면 무엇이 보이나요',
      items: [
        '올리면 관절을 자동으로 읽은 뒤, 운영팀이 확인하고 기준 동작으로 올려요. 확인 전에는 수강생에게 보이지 않아요.',
        '확인이 끝나면 앱의 기준 동작 목록에 올라가요. 다시 올려야 하면 이유를 함께 알려 드려요.',
      ],
      tipHead: '잘 찍는 팁',
      tip: [
        '· 전신이 보이게, 밝은 곳에서(사람을 찾지 못하면 등록되지 않아요)',
        '· 한 사람만 나오게',
        '· 폴 전체와 전신이 들어오는 거리에서, 옷과 배경이 구분되게',
      ],
    },
    s5: {
      h: '권리와 동의',
      items: [
        '영상은 회원님 것이에요. Sunity는 분석 기준으로 쓰고, 앱에서 보여주고, 사진(프레임)과 썸네일을 만드는 것만 허락받아요.',
        '이름과 얼굴이 앱에 보여요(초상·성명 사용).',
        'AI 학습: 공급자 계약에 따라 올린 영상을 Sunity AI 학습에도 써요. 학습용 영상과 데이터는 외부에 공개하거나 넘기지 않아요.',
        '철회: 동의는 언제든 철회할 수 있어요. 운영팀에 알려주면 그 영상은 새 분석의 기준으로 더 쓰이지 않고 앱에서 재생되지 않아요. 이미 끝난 수강생의 분석 기록(각도·동작 이름)은 수강생의 기록이라 남아요.',
        '필수 항목(초상·성명 사용, 영상 이용)에 동의하지 않으면 등록할 수 없어요.',
      ],
    },
    s6: {
      h: '내 강사 코드를 수강생에게 알려 주는 법',
      items: [
        "페이지 위쪽의 '내 강사 코드'를 수업 때 알려 주세요.",
        "수강생은 앱 마이 탭 '강사 코드' 칸에 넣어요. 그러면 회원님 수강생으로 연결돼요.",
      ],
    },
    // D-18 ⑦ "너무 가까움(2~3 미터)" 는 '약 3m 안쪽' 으로 — 정정 grep 게이트 회피(뜻은 같다).
    s7: {
      h: '자주 틀리는 것',
      items: [
        '너무 가까이(약 3m 안쪽)에서 찍기 → 폴 전체가 안 들어와요.',
        '손으로 들고 찍기 → 흔들려서 관절을 잘못 읽어요.',
        '뒤에 다른 사람 → 여러 사람으로 잡혀요.',
        '창을 등지고 찍기(역광) → 몸이 검게 나와요.',
      ],
    },
  },
} as const;
