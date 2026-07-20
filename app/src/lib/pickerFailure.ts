// 영상 선택·업로드 실패 → 사용자 행동 안내 매핑 (quick-260720-hn8).
//
// belle 요구: "분석조차 안 되면 안 되니까 해결방안을 알려줘야지 고객들에게."
// 목적은 에러를 예쁘게 보여주는 게 아니라 **사용자가 다음에 뭘 하면 되는지 알게 하는 것**.
// 그래서 각 실패는 title(무슨 일인지) + lines(원인 1줄 + 행동 1줄) + 오른쪽 버튼
// (즉시 실행 가능한 행동) 으로 구성한다.
//
// 문구 출처 — Figma node 1:499 `Group 53` 확정본:
//   · 용량 초과 / 형식 미지원 2종은 **디자인 확정 문구라 한 글자도 바꾸지 않는다.**
//     'mp4, mov형식의' 의 붙임(공백 없음)도 원문 그대로다.
//   · 나머지(권한 거부·picker 실패·처리 실패)는 Figma 에 없어 같은 양식으로 확장했다
//     (원인 1줄 + 행동 1줄, '~요' 종결).
//
// 기술 용어 노출 금지 — iCloud 오프로드 / representation mode 같은 내부 개념은
// "사진 앱에서 영상을 열어 다운로드한 뒤 다시 선택해주세요" 같은 행동 지시로 번역한다.
//
// react / react-native / expo import 0 — 순수 데이터 매핑이라 `node --test` 로 바로
// 검증된다 (신규 npm 의존성 0 제약).

export type PickFailureKind =
  | 'permissionCamera'
  | 'permissionLibrary'
  | 'format'
  | 'tooLarge'
  | 'libraryOpen'
  | 'cameraOpen'
  | 'processFailed';

// 오른쪽(주) 버튼의 동작. 왼쪽은 항상 [닫기] 로 고정이라 별도 표현하지 않는다.
//   openSettings — 설정 앱 열기 (권한 거부)
//   repick       — 알림창 닫고 앨범 picker 재오픈 (앨범 기인 실패)
//   dismiss      — 닫기만 (재오픈이 부적절한 카메라 기인 실패)
export type PickFailureAction = 'openSettings' | 'repick' | 'dismiss';

export interface PickFailure {
  kind: PickFailureKind;
  title: string;
  // 본문. Figma 확정본이 2줄 구성이라 배열로 유지한다 (줄바꿈 위치가 디자인의 일부).
  lines: string[];
  primaryLabel: string;
  primaryAction: PickFailureAction;
  // picker 가 던진 원본 오류 문자열. iCloud 오프로드는 아직 **가설**이라(에어드랍
  // 로컬 파일 성공 / 앨범 원본 실패라는 정황 증거뿐) 실패가 재현될 때 원인을
  // 확정·기각할 증거가 화면에 남아야 한다. 가공하지 않고 그대로 싣는다.
  // Figma 양식에 없는 진단 전용 요소 — 본문 아래 작은 회색 텍스트로 눈에 띄지 않게 둔다.
  detail?: string;
}

type PickFailureCopy = Omit<PickFailure, 'kind' | 'detail'>;

const REPICK_LABEL = '다른 파일 선택';

function copyFor(kind: PickFailureKind): PickFailureCopy {
  switch (kind) {
    // ── Figma 확정 문구 (변경 금지) ──────────────────────────────────────
    case 'tooLarge':
      return {
        title: '용량이 너무 커요',
        lines: [
          '100MB 이하 영상만 업로드 할 수 있어요.',
          '영상을 잘라서 다시 시도해주세요.',
        ],
        primaryLabel: REPICK_LABEL,
        primaryAction: 'repick',
      };
    case 'format':
      return {
        title: '지원할 수 없는 파일이에요',
        lines: ['mp4, mov형식의 영상만', '업로드 가능해요.'],
        primaryLabel: REPICK_LABEL,
        primaryAction: 'repick',
      };
    // ── Figma 미수록 — 같은 양식으로 확장 ────────────────────────────────
    case 'libraryOpen':
      return {
        title: '영상을 가져오지 못했어요',
        lines: [
          '이 영상은 기기에 저장되어 있지 않을 수 있어요.',
          '사진 앱에서 영상을 열어 다운로드한 뒤 다시 선택해주세요.',
        ],
        primaryLabel: REPICK_LABEL,
        primaryAction: 'repick',
      };
    case 'permissionLibrary':
      return {
        title: '사진 접근 권한이 필요해요',
        lines: [
          '앨범에서 영상을 가져오려면 사진 접근 권한이 필요해요.',
          '설정에서 사진 접근을 허용한 뒤 다시 시도해주세요.',
        ],
        primaryLabel: '설정 열기',
        primaryAction: 'openSettings',
      };
    case 'permissionCamera':
      return {
        title: '카메라 접근 권한이 필요해요',
        lines: [
          '앱에서 바로 촬영하려면 카메라 권한이 필요해요.',
          '설정에서 카메라를 켠 뒤 다시 시도해주세요.',
        ],
        primaryLabel: '설정 열기',
        primaryAction: 'openSettings',
      };
    case 'cameraOpen':
      return {
        title: '카메라를 열지 못했어요',
        lines: [
          '다른 앱이 카메라를 쓰고 있으면 열리지 않을 수 있어요.',
          '해당 앱을 종료한 뒤 다시 시도해주세요.',
        ],
        // 카메라 기인 실패라 앨범 재오픈은 부적절 — 닫기만.
        primaryLabel: '확인',
        primaryAction: 'dismiss',
      };
    case 'processFailed':
      return {
        title: '영상을 처리하지 못했어요',
        lines: [
          '영상은 선택했지만 읽는 중에 문제가 생겼어요.',
          '다른 영상으로 다시 시도해주세요.',
        ],
        primaryLabel: REPICK_LABEL,
        primaryAction: 'repick',
      };
    default: {
      // 컴파일 타임 exhaustiveness 게이트 — PickFailureKind 에 값을 추가하고
      // 매핑을 빠뜨리면 `npm run typecheck` 가 깨진다 (안내 없는 실패 = 회귀).
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

export function describePickFailure(
  kind: PickFailureKind,
  detail?: string,
): PickFailure {
  const copy = copyFor(kind);
  if (detail === undefined) return { kind, ...copy };
  return { kind, ...copy, detail };
}
