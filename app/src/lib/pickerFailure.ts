// 영상 선택·업로드 실패 → 사용자 행동 안내 매핑 (quick-260720-hn8).
//
// belle 요구: "분석조차 안 되면 안 되니까 해결방안을 알려줘야지 고객들에게."
// 목적은 에러를 예쁘게 보여주는 게 아니라 **사용자가 다음에 뭘 하면 되는지 알게 하는 것**.
// 그래서 각 실패는 title(무슨 일인지) + cause(왜 그런지) + steps(무엇을 하면 되는지) +
// action(즉시 실행 가능한 버튼) 4요소를 반드시 갖는다.
//
// 기술 용어 노출 금지 — iCloud 오프로드 / representation mode 같은 내부 개념은
// "사진 앱에서 영상을 한 번 열어 다운로드가 끝난 뒤 다시 선택해주세요" 같은 행동
// 지시로 번역한다 (폴스포츠 수강생이 읽고 실제로 행동할 수 있어야 함).
//
// react / react-native / expo import 0 — 순수 데이터 매핑이라 테스트 하니스 없이
// `node --test` 로 바로 검증된다 (신규 npm 의존성 0 제약).

export type PickFailureKind =
  | 'permissionCamera'
  | 'permissionLibrary'
  | 'format'
  | 'tooLarge'
  | 'libraryOpen'
  | 'cameraOpen'
  | 'processFailed';

export type PickFailureAction =
  | { kind: 'openSettings'; label: string }
  | { kind: 'dismiss'; label: string };

export interface PickFailure {
  kind: PickFailureKind;
  title: string;
  cause: string;
  steps: string[];
  action: PickFailureAction;
  // picker 가 던진 원본 오류 문자열. iCloud 오프로드는 아직 **가설**이라(에어드랍
  // 로컬 파일 성공 / 앨범 원본 실패라는 정황 증거뿐) 실패가 재현될 때 원인을
  // 확정·기각할 증거가 화면에 남아야 한다. 가공하지 않고 그대로 싣는다.
  detail?: string;
}

type PickFailureCopy = Omit<PickFailure, 'kind' | 'detail'>;

function copyFor(kind: PickFailureKind): PickFailureCopy {
  switch (kind) {
    case 'permissionLibrary':
      return {
        title: '사진 접근 권한이 꺼져 있어요',
        cause:
          '앨범에 저장된 영상을 가져오려면 사진 접근 권한이 필요해요. 지금은 권한이 꺼져 있어 영상을 읽을 수 없어요.',
        steps: [
          '아래 [설정 열기] 를 눌러 설정 앱으로 이동해 주세요.',
          'Sunity 를 찾아 [사진] 항목을 눌러주세요.',
          "[모든 사진] 을 선택해 접근을 허용해 주세요.",
          '앱으로 돌아와 [앨범에서 선택] 을 다시 눌러주세요.',
        ],
        action: { kind: 'openSettings', label: '설정 열기' },
      };
    case 'permissionCamera':
      return {
        title: '카메라 권한이 꺼져 있어요',
        cause:
          '앱에서 바로 촬영하려면 카메라 권한이 필요해요. 지금은 권한이 꺼져 있어 카메라를 열 수 없어요.',
        steps: [
          '아래 [설정 열기] 를 눌러 설정 앱으로 이동해 주세요.',
          'Sunity 를 찾아 [카메라] 를 켜주세요.',
          '앱으로 돌아와 [즉석 촬영] 을 다시 눌러주세요.',
        ],
        action: { kind: 'openSettings', label: '설정 열기' },
      };
    case 'format':
      return {
        title: '지원하지 않는 형식이에요',
        cause:
          '지금은 mp4, mov 형식의 영상만 분석할 수 있어요. 선택한 영상은 다른 형식이라 읽을 수 없어요.',
        steps: [
          'mp4 또는 mov 형식의 다른 영상을 골라주세요.',
          '앱에서 직접 촬영하면 항상 분석 가능한 형식으로 저장돼요.',
        ],
        action: { kind: 'dismiss', label: '다른 영상 선택' },
      };
    case 'tooLarge':
      return {
        title: '영상 용량이 너무 커요',
        cause:
          '100MB 이하 영상만 분석할 수 있어요. 선택한 영상은 100MB 를 넘어서 업로드할 수 없어요.',
        steps: [
          '동작이 담긴 부분만 짧게 잘라서 다시 올려주세요.',
          '앱에서 직접 촬영하면 분석에 맞는 길이로 저장돼요.',
        ],
        action: { kind: 'dismiss', label: '다른 영상 선택' },
      };
    case 'libraryOpen':
      return {
        title: '영상을 가져오지 못했어요',
        cause:
          '앨범에 보이는 영상이라도 실제 파일이 기기에 없을 수 있어요. 저장 공간을 아끼려고 원본이 클라우드에 올라가 있으면 목록에는 보여도 바로 가져오지 못해요.',
        steps: [
          '사진 앱에서 그 영상을 열어 끝까지 재생한 뒤, 다운로드가 끝나면 다시 선택해 주세요.',
          'Wi-Fi 에 연결된 상태에서 다시 시도해 주세요.',
          "설정 앱 > 사진 에서 [iPhone 저장 공간 최적화] 대신 [원본 다운로드 및 보관] 을 선택해 주세요.",
          '계속 안 되면 앱에서 직접 촬영해 주세요. 촬영본은 항상 기기에 저장돼요.',
        ],
        action: { kind: 'openSettings', label: '설정 열기' },
      };
    case 'cameraOpen':
      return {
        title: '카메라를 열지 못했어요',
        cause:
          '권한은 있지만 카메라를 실행하는 단계에서 실패했어요. 다른 앱이 카메라를 쓰고 있으면 이런 일이 생길 수 있어요.',
        steps: [
          '카메라를 쓰고 있는 다른 앱(영상통화 등)이 있는지 확인하고 종료해 주세요.',
          '앱을 완전히 껐다가 다시 켠 뒤 시도해 주세요.',
          '급하면 앨범에서 저장된 영상을 선택해 주세요.',
        ],
        action: { kind: 'dismiss', label: '확인' },
      };
    case 'processFailed':
      return {
        title: '선택한 영상을 처리하지 못했어요',
        cause:
          '영상은 정상적으로 골랐지만, 앱이 그 영상을 읽는 단계에서 실패했어요. 앨범을 여는 문제와는 다른 단계예요.',
        steps: [
          '같은 영상 대신 다른 영상으로 다시 시도해 주세요.',
          '앱에서 직접 촬영한 영상은 이 문제가 거의 없어요.',
        ],
        action: { kind: 'dismiss', label: '다른 영상 선택' },
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
