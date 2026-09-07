// 부위 상세 시트 (승인 목업 7R ② 구조 — quick-260730-py1, 33-G S6/S7).
//
// 종전 구조는 **record 단위**였다 (부위에 감점 2건이면 시트가 2개 열렸다). 승인
// 목업 ② 는 **부위 단위**다: 칩 → 크롭 1쌍 → paircap(좌우 실영상 초) → onecap →
// 결함 블록 N개(다리 = "고칠 것 1"·"고칠 것 2") → facing.
// belle 확인 ② 반려의 "무릎 피는 거 하나 어디 갔냐"(4R#2)가 이 구조의 이유다.
//
// 조판·카피 조립은 `lib/deductionSheet.ts buildRegionSheetView` 가 소유한다 (순수
// 함수, node --test 로 고정). 호출은 caller(result.tsx)가 하고 이 컴포넌트는 그
// 결과(`RegionSheetView`)를 **렌더만** 한다 — 조판 분기 사본 0.
//
// 승인 CSS → 앱 토큰 매핑 (M-14 — 목업 px 는 데스크톱 스케일, 앱은 토큰 우선.
// 색 실측값은 theme/colors.ts 에 출처와 함께 박제 — 여기 hex 리터럴 0):
//   .fault-head (15/800 brand on brand-tint + 하단 보더) → boxLabel + brandTint
//   .headline (bodyLg 800) → typography.bodyLg
//   .why (bodySm ink-2) → bodySm + textMid
//   .basis (연회색 배경 + line 보더, b=진한 잉크) → softBg + border + bold 세그먼트
//   .cue (bodyMd 800 brand on brand-tint radius 12) → bodyMdBold brand + brandTint
//   .methodline (틸 박스) → caption 스케일 본문 + infoTeal 토큰 3종
//   .numnote (12.5 ink-3) → caption + textSecondary
//   .paircap (12/800 회색 space-between) → caption 700 + textMid
//   .onecap (caption ink-2 center) → caption + textMid + center
//   .facing (틸 박스, bodySm) → bodySm + infoTeal 토큰 3종
// 신규 폰트 크기 리터럴 0 (CLAUDE.md §4). 이모지 0. 라이트 전용.
//
// 유지되는 승인 원형(gate ⑤ belle Figma, M-13): bullets(용어줄·확인하기) ·
// coachConnect · aiNoteBox — 삭제 금지. (일러스트 표면은 belle 08-24 결정으로
// 전면 제거 — 시트는 실사진 비교·원인 문구·수치·미션 텍스트 경로만 남는다.)
// 대체된 것: 하단 "이 원인은 어떻게 측정됐나" 근거 박스 → 블록 맨 뒤 numnote
// (2R 수치 강등 — 수치의 승인 거처가 바뀐 것이지 수치가 사라진 게 아니다).
//
// 제거된 것 (M-1): 사진 속 베이크 초를 지칭하던 안내 라벨 2개(구 33-15 A-6 이관분).
// 초 표기의 정본은 승인 7R 의 paircap 텍스트다 — 두 곳에 같은 초를 쓰면 이중 표기가
// 되고, PNG 재생성(§C-4) 후에는 사진 속 표기 자체가 사라진다.

import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import { ANGLE_VS_REFERENCE_PREFIX } from '../lib/deductionLabels';
import {
  ADVISORY_CHIP_KO,
  objectJosaKo,
  type RegionSheetView,
} from '../lib/deductionSheet';
import { resolveZoomImageUrl } from '../lib/faultZoomUrls';
import { terminologyPlain, type TerminologyTerm } from '../lib/terminologyMap';
import { colors, radius, spacing, typography } from '../theme';
import type { FaultZoomComparison } from '../types/analysis';

interface Props {
  visible: boolean;
  onClose: () => void;
  /** 부위 단위 뷰모델 (lib/deductionSheet.buildRegionSheetView). null = 미렌더. */
  view: RegionSheetView | null;
  /** 시트 상단 크롭 (view.primaryRecordIndex 의 카드). */
  primaryZoom: FaultZoomComparison | null;
  /** 블록 안 크롭 — key = recordIndex (view.blocks[].blockRecordIndexForCrop). */
  blockZooms?: Record<number, FaultZoomComparison | null>;
  // Phase 27 D-06 — zoom 사후 도착 대기 중이면 true. 확대사진 자리에 로딩 placeholder.
  zoomPending?: boolean;
  // Phase 28 D-04 — DTW 기준 프레임 대응 실패 시 true. 전신 폴백 정직 캡션.
  refMatchFailed?: boolean;
  // quick-260802-tie — 기준(우측) 패널에 표시가 하나도 그려지지 않았을 때 true
  // (백엔드 `refMarked === false`). 크롭은 그대로 두고 한 줄만 덧붙인다.
  refUnmarked?: boolean;
  // quick-260903-upx — 학생(왼쪽) 패널에 표시가 하나도 안 그려진 카드 (userMarked===false).
  // 게이트가 카드를 지우는 대신 표시만 뺀 결과 — 사진은 그대로, 한 줄로 사실만 말한다.
  userUnmarked?: boolean;
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 true. 크롭은 유지하되 "예상 부위"
  // 배지를 얹어 확정 결함이 아니라 추정 부위임을 표시 (크롭·수치·비교 삭제 0).
  estimatedArea?: boolean;
  // 우측 비교 대상 라벨 — Mode1='정은지 선수', Mode3='지난 영상'. 크롭 위 halfLabel 용
  // (paircap 우측 라벨은 뷰모델이 소유 — rightPairLabel).
  rightLabel: string;
  // quick-260824-q6p — 7일 넘은 doc 의 확대 이미지 재발급 맵 (zoomCardKey →
  // fresh presigned URL). 부재/미등재 키 = 종전 저장 imageUrl 그대로 (하위호환,
  // fail-closed — 재발급 실패 시 현행 회색 폴백). doc item 은 변형하지 않고
  // 렌더 경계에서만 조회한다.
  freshZoomUrls?: Record<string, string>;
  // quick-260824-q6p — Image 로드 실패 시 나이 무관 재발급 트리거 (시계 오차·
  // 조기 만료 커버, 훅이 mount 당 1회 single-flight 소유).
  onZoomImageError?: () => void;
  // belle 09-07 — "영상에서 이 순간 크게 보기". 시트를 닫고 전체화면 비교 뷰어를
  // 그 순간에 멈춰 세우는 명령 (caller 가 순서를 소유한다 — iOS 중첩 Modal 함정).
  //
  // **미전달 = 버튼 자체를 렌더하지 않는다**(fail-closed). 합성 비교 영상 가지처럼
  // 뛰어갈 곳이 없는 화면에서 눌러도 아무 일 없는 버튼을 놓지 않기 위함이다.
  onOpenMoment?: (recordId: string) => void;
  // belle 09-07 — 위 버튼이 가리킬 순간의 조인 키(대표 record 의 recordId).
  // null = 이 항목엔 뛰어갈 순간이 없다 → 버튼을 **숨기지 않고 비활성**으로 그린다.
  // 순간이 없는 것은 예외가 아니라 설계다: 잰 순간을 신뢰 있게 정할 수 없는
  // criterion(split_angle 의 vision 주입분·reach·whole-score 폴백)과 legacy doc 은
  // atVideoSec 자체가 없다 (momentJump.ts 등재 조건 3). 없는 초를 지어내 뛰면
  // 사용자가 엉뚱한 데를 확대하고 "확대해 봤는데 아무것도 없다"가 된다.
  momentRecordId?: string | null;
}

// criterion → 심사 언어 용어(terminologyMap) 매핑. 미등록 criterion 은 null(용어줄 생략).
function criterionTerm(criterion: string): TerminologyTerm | null {
  if (criterion === 'split_angle') return 'split';
  if (criterion === 'body_relative_reach') return 'reach';
  if (criterion === 'leg_extension' || criterion === 'arm_extension' || criterion === 'line') {
    return 'line';
  }
  if (criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) return 'angle';
  return null;
}

// gate ⑤ 하단 고지 박스 카피 (belle Figma 원형).
const AI_DISCLAIMER =
  'AI가 추정한 가능성이에요. 강사 수업과 함께 확인하면 가장 정확한 피드백을 받을 수 있어요.';
// gate ⑤ 강사 연결 줄.
const COACH_CONNECT = '강사가 함께 보면 더 구체적인 피드백을 받을 수 있어요';
// 33-15 (D-16) — 대시 나열("확인하기 — …") 문장화.
const CHECK_BULLET = '거울을 보며 동작을 직접 재현해서 확인해 보세요';
// 승인 목업 ② 크롭 카드 칩 (renderDetail chip.brand / chip.gray).
const CHIP_TODAY_FIX = '오늘 고칠 것';
// 33-G S2 (quick-260730-szk) — 참고 칩 문형은 `lib/deductionSheet.ADVISORY_CHIP_KO`
// 단일 소스. 여기 local 사본이 있던 동안 시트·칩·마커 title 이 서로 갈릴 수 있었다.
// 시트 제목 접미 (부위 단위 재구성 — 승인본 ② 는 부위 시트다).
const SHEET_TITLE_SUFFIX = ' 부위 상세';
// quick-260802-tie — 기준(우측) 패널에 표시가 하나도 안 그려졌을 때의 한 줄.
// **단정 금지·사과 금지**: 오른쪽 영상이나 선수를 평가하지 않고, 우리가 그 프레임에서
// 관절 위치를 확인하지 못했다는 사실과 그래서 표시를 넣지 않았다는 처분만 말한다.
// 문형은 `refMatchNote`(같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요) 선례 —
// [이유] + [그래서 이렇게 했다] + `-요`. 카드·수치·비교는 그대로 둔다(정보 보존).
const REF_UNMARKED_NOTE = '오른쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요';
// quick-260903-upx — 학생 패널판. 승인 문장(REF_UNMARKED_NOTE)에서 "오른쪽"→"왼쪽"만 (신규 문형 0).
const USER_UNMARKED_NOTE = '왼쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요';
// IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 카피 (시트가
// 실제 라벨 소유). 확정 결함 아님 — advisoryOrange 톤(표시 전용).
const ESTIMATED_AREA_LABEL = '예상 부위';
// IN-01 — 저신뢰 시 관절을 단정하지 않는 시트 제목(정확한 관절 assert 금지).
const ESTIMATED_AREA_TITLE = '예상 부위 (참고)';
// belle 09-07 — 손가락 확대 진입 버튼 라벨. "이 순간"이 무엇인지(영상의 그 시점)와
// 무엇을 하게 되는지(크게 보기)를 한 줄에 담는다 — 제스처 설명은 전체화면 안의
// 1회 안내가 맡는다(여기서 "두 손가락으로" 까지 말하면 버튼이 설명문이 된다).
const MOMENT_BTN_LABEL = '영상에서 이 순간 크게 보기';

export function DeductionDetailSheet({
  visible,
  onClose,
  view,
  primaryZoom,
  blockZooms,
  zoomPending = false,
  refMatchFailed = false,
  refUnmarked = false,
  userUnmarked = false,
  estimatedArea = false,
  rightLabel,
  freshZoomUrls,
  onZoomImageError,
  onOpenMoment,
  momentRecordId,
}: Props) {
  const { width, height: winH } = useWindowDimensions();
  if (!view) return null;

  const sheetHeight = Math.round(winH * 0.78);
  // 합성 이미지 = [내 영상 | 기준] 정사각 2개 → 가로:세로 ≈ 2:1.
  const imgW = width - spacing.screenX * 2;
  const imgH = imgW / 2;

  // 심사 언어 용어줄 (terminologyMap 적용 — "이 지표가 무엇인지"). 부위 시트라
  // 기준 record = 상단 크롭을 낳은 블록의 criterion (뷰모델이 원 키를 나른다).
  const term = criterionTerm(view.primaryCriterion);
  const termText = term ? terminologyPlain(term) : null;

  const renderCrop = (zoom: FaultZoomComparison) => (
    <View style={[styles.imageWrap, { height: imgH }]}>
      {/* quick-260824-q6p — fresh 맵 우선, 저장 imageUrl 폴백 (7일 presigned 만료
          수리). onError = 재발급 트리거 (훅 single-flight — 무한 루프 차단).
          quick-260903-f2w — 조회 규칙은 resolveZoomImageUrl 단일 출처 (topFix
          카드 인라인과 공유, 사본 0). */}
      <Image
        source={{ uri: resolveZoomImageUrl(zoom, freshZoomUrls) }}
        onError={onZoomImageError}
        style={styles.image}
        resizeMode="contain"
        accessibilityLabel={`${view.title} 확대 비교 이미지`}
      />
      <View style={[styles.halfLabel, styles.halfLabelLeft]}>
        <Text style={styles.halfLabelText}>내 영상</Text>
      </View>
      <View style={[styles.halfLabel, styles.halfLabelRight]}>
        <Text style={styles.halfLabelText}>{rightLabel}</Text>
      </View>
    </View>
  );

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      {/* RN bottom sheet 정석: backdrop 빈 영역만 Pressable, sheet 는 pure View. */}
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTop} onPress={onClose} />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />
          <View style={styles.titleRow}>
            {/* IN-01 — 저신뢰 시 관절 단정 대신 "예상 부위" 제목 (S17 PASS 보존). */}
            <Text style={styles.title}>
              {estimatedArea
                ? ESTIMATED_AREA_TITLE
                : `${view.title}${SHEET_TITLE_SUFFIX}`}
            </Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="닫기"
              hitSlop={10}
              style={styles.closeBtn}
            >
              <Text style={styles.closeText}>✕</Text>
            </Pressable>
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {/* goalLine (quick-260802-mrg) — 이 항목이 무엇을 하려는 동작인지 한
                문장. 제목 아래·블록 위, `oneCap`(사진 설명)과 다른 자리다. 원인이
                묶인 항목에서 목표 문장을 **한 번만** 말하는 자리 — 블록마다 같은
                문장을 반복하지 않는다. 목표 절이 없으면 자리도 두지 않는다
                (fail-closed — 없는 문장을 만들지 않는다). */}
            {view.goalLine ? (
              <View style={styles.goalBox}>
                <Text style={styles.goalText}>{view.goalLine}</Text>
              </View>
            ) : null}

            {/* ── 크롭 카드 (승인본 card: chip → cropimg → paircap → onecap) ── */}
            {primaryZoom ? (
              <View style={styles.cropCard}>
                {/* IN-01 (M-21) — 역립 저신뢰에서는 "오늘 고칠 것" 확정 칩을 걸지
                    않는다. 바로 아래 "예상 부위" 배지와 서로 모순되고, IN-01 은
                    확정 단정 표면을 강등하는 결정이다 (S17 PASS 보존). 승인 목업 ②
                    에는 추정 케이스가 없어 이 분기의 정답은 승인본이 아니라
                    IN-01 원칙에서 나온다. */}
                {estimatedArea ? null : (
                  <View
                    style={[
                      styles.chip,
                      view.isAdvisoryOnly ? styles.chipGray : styles.chipBrand,
                    ]}
                  >
                    <Text
                      style={[
                        styles.chipText,
                        view.isAdvisoryOnly
                          ? styles.chipTextGray
                          : styles.chipTextBrand,
                      ]}
                    >
                      {view.isAdvisoryOnly ? ADVISORY_CHIP_KO : CHIP_TODAY_FIX}
                    </Text>
                  </View>
                )}
                {/* IN-01 — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 (확정 결함 아님,
                    advisoryOrange 톤). 크롭·수치·비교는 유지. */}
                {estimatedArea ? (
                  <View style={styles.estimatedBadge}>
                    <Text style={styles.estimatedBadgeText}>
                      {ESTIMATED_AREA_LABEL}
                    </Text>
                  </View>
                ) : null}
                {renderCrop(primaryZoom)}
                {/* paircap (6R) — 좌 '내 자세 · 실 N초' / 우 '기준 (정은지) · 실 N초'.
                    초는 백엔드 방출값만 (뷰모델 소유 — 앱 재계산 금지, F-3). */}
                {view.pairCapLeft || view.pairCapRight ? (
                  <View style={styles.pairCapRow}>
                    <Text style={styles.pairCapText}>{view.pairCapLeft}</Text>
                    <Text style={styles.pairCapText}>{view.pairCapRight}</Text>
                  </View>
                ) : null}
                {/* onecap — 무엇을 견주는 사진인지 1줄. 마킹 기하 단정 0 (M-6). */}
                {view.oneCap ? (
                  <Text style={styles.oneCap}>{view.oneCap}</Text>
                ) : null}
                {/* Phase 28 D-04 — DTW 대응 실패 시 ref 는 전신 폴백이라 정직 고지. */}
                {refMatchFailed ? (
                  <Text style={styles.refMatchNote}>
                    같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요
                  </Text>
                ) : null}
                {/* quick-260802-tie — 기준 패널에 표시가 하나도 안 그려진 카드.
                    비교 대상 쪽이 빈 채로 침묵하지 않는다. 사진은 그대로 둔다. */}
                {refUnmarked ? (
                  <Text style={styles.refMatchNote}>{REF_UNMARKED_NOTE}</Text>
                ) : null}
                {/* quick-260903-upx — 학생 패널 표시 생략(눈 불일치·좌표 부재). 사진은 그대로. */}
                {userUnmarked ? (
                  <Text style={styles.refMatchNote}>{USER_UNMARKED_NOTE}</Text>
                ) : null}
              </View>
            ) : zoomPending ? (
              // Phase 27 D-06 — zoom 사후 도착 대기. 확대 이미지만 렌더 중이라 로딩
              // placeholder. 도착(onSnapshot) 시 자동으로 위 이미지 분기로 전환된다.
              <View
                style={[styles.imageWrap, styles.imagePending, { height: imgH }]}
                accessibilityRole="progressbar"
                accessibilityLabel="확대 비교 이미지를 준비하고 있어요"
              >
                <ActivityIndicator color={colors.brand} />
                <Text style={styles.pendingText}>확대 비교 이미지를 준비하고 있어요</Text>
              </View>
            ) : null}

            {/* ── 결함 블록 N개 (승인본 card.fault) ────────────────────────── */}
            {view.blocks.map((block) => {
              const blockZoom =
                block.blockRecordIndexForCrop != null
                  ? blockZooms?.[block.blockRecordIndexForCrop] ?? null
                  : null;
              return (
                <View key={block.recordIndex} style={styles.faultCard}>
                  {/* fault-head — 번호 헤더 (4R#2, 블록 매몰 방지). */}
                  <View style={styles.faultHead}>
                    <Text style={styles.faultHeadText}>{block.header}</Text>
                  </View>
                  <View style={styles.faultBody}>
                    {block.statusLine ? (
                      <Text style={styles.headline}>{block.statusLine}</Text>
                    ) : null}
                    {block.whyLine ? (
                      <Text style={styles.why}>{block.whyLine}</Text>
                    ) : null}
                    {/* basis (5R#2) — "어디서 재나요" 굵은 문두 + 본문. 세그먼트를
                        중첩 Text 로 그린다 (RN 은 HTML 을 해석하지 않는다). */}
                    {block.basisLine ? (
                      <View style={styles.basisBox}>
                        <Text style={styles.basisText}>
                          {block.basisLine.map((seg, i) => (
                            <Text
                              key={i}
                              style={seg.bold ? styles.basisBold : undefined}
                            >
                              {seg.text}
                            </Text>
                          ))}
                        </Text>
                      </View>
                    ) : null}
                    {block.cueLine ? (
                      <View style={styles.cueBox}>
                        <Text style={styles.cueText}>{block.cueLine}</Text>
                      </View>
                    ) : null}
                    {/* methodline (5R#3) — 측정 방법 정직 라벨. */}
                    {block.methodLine ? (
                      <View style={styles.infoBox}>
                        <Text style={styles.infoText}>{block.methodLine}</Text>
                      </View>
                    ) : null}
                    {/* numnote (2R) — 수치는 블록 맨 뒤 작은 회색 줄. */}
                    {block.numNote ? (
                      <Text style={styles.numNote}>{block.numNote}</Text>
                    ) : null}
                    {/* 이 블록만의 확대 카드 (M-5) — 상단 크롭과 다른 카드일 때만.
                        기존에 보이던 증거를 조용히 잃지 않는다. */}
                    {blockZoom ? renderCrop(blockZoom) : null}
                  </View>
                </View>
              );
            })}

            {/* facing — 두 사진이 달라 보이는 이유 (기준 정렬로 잰 항목이 있을 때만). */}
            {view.facingLine ? (
              <View style={styles.infoBox}>
                <Text style={styles.infoText}>{view.facingLine}</Text>
              </View>
            ) : null}

            {/* 확인하기 안내 (gate ⑤) + 심사 언어 용어줄(terminologyMap).
                33-15 (D-16) — 대시 나열을 문장화 (조사는 objectJosaKo 로 받침 판정). */}
            <View style={styles.bullets}>
              {termText ? (
                <Text style={styles.bullet}>
                  {`이 지표는 ${termText}${objectJosaKo(termText)} 봐요`}
                </Text>
              ) : null}
              <Text style={styles.bullet}>{CHECK_BULLET}</Text>
            </View>

            {/* 강사 연결 줄 (gate ⑤). */}
            <Text style={styles.coachConnect}>{COACH_CONNECT}</Text>

            {/* AI 추정 고지 박스 (gate ⑤ 하단). */}
            <View style={styles.aiNoteBox}>
              <Text style={styles.aiNoteText}>{AI_DISCLAIMER}</Text>
            </View>
          </ScrollView>

          {/* belle 09-07 — 상시 열려 있는 확대 진입점. 자동 확대 카드가 맞는 부위를
              가리키도록 만드는 대신, 사용자가 그 순간으로 가서 손가락으로 직접 본다
              (belle 원문 "손가락으로 영상을 멈추고 확대할 수 있게"). 위계는 보조
              액션 — 시트의 주 행동은 여전히 '닫기'(brand CTA)라 여기는 design.md §0
              보조 문법(1px inputBorder 테두리 + 투명 배경 + textPrimary 라벨)을
              쓴다. BodyProfilePromptModal.secondary 와 같은 문법 (신규 문법 0). */}
          {onOpenMoment ? (
            <Pressable
              onPress={() => {
                if (momentRecordId) onOpenMoment(momentRecordId);
              }}
              disabled={!momentRecordId}
              accessibilityRole="button"
              accessibilityLabel={MOMENT_BTN_LABEL}
              // 순간이 없는 항목은 눌러도 갈 곳이 없다는 것을 보조기술에도 알린다.
              accessibilityState={
                momentRecordId ? undefined : { disabled: true }
              }
              hitSlop={8}
              style={({ pressed }) => [
                styles.momentBtn,
                !momentRecordId && styles.momentBtnDisabled,
                pressed && momentRecordId ? styles.ctaPressed : null,
              ]}
            >
              <Text style={styles.momentBtnText}>{MOMENT_BTN_LABEL}</Text>
            </Pressable>
          ) : null}

          <Pressable
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="닫기"
            style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
          >
            <Text style={styles.ctaText}>닫기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 32,
    paddingHorizontal: spacing.screenX,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  closeBtn: { padding: 4 },
  closeText: { ...typography.sectionTitle, color: colors.textSecondary },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16, gap: 14 },
  // goalLine (quick-260802-mrg) — 목표 문장 1줄. 기존 토큰만 사용한다
  // (softBg + border + bodySm/textMid = basisBox 와 같은 정보 톤). 결함 블록의
  // brandTint 를 쓰지 않는 이유는 이것이 감점이 아니라 **동작의 목표**여서다.
  goalBox: {
    backgroundColor: colors.softBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.listItem,
    paddingHorizontal: 11,
    paddingVertical: 9,
  },
  goalText: {
    ...typography.bodySm,
    color: colors.textMid,
  },
  // ── 크롭 카드 (승인본 .card) ─────────────────────────────────────────────
  cropCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
    alignItems: 'stretch',
  },
  // 승인본 .chip (radius 999 = pill).
  chip: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipBrand: { backgroundColor: colors.brandTint },
  chipGray: { backgroundColor: colors.softBg },
  chipText: { ...typography.caption, fontWeight: '700' },
  chipTextBrand: { color: colors.brand },
  chipTextGray: { color: colors.textMid },
  // 구 확대 비교 컴포넌트 이미지 pane 이식 — 2:1 합성 이미지.
  imageWrap: {
    width: '100%',
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.divider,
  },
  image: { width: '100%', height: '100%' },
  // Phase 27 D-06 — zoom 사후 도착 대기 placeholder (이미지 카드와 동일 컨테이너).
  imagePending: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  pendingText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // Phase 28 D-04 — refMatch='failed' 전신 폴백 정직 캡션.
  refMatchNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // 승인본 .paircap — 12/800 space-between (좌 내 자세 / 우 기준).
  pairCapRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  pairCapText: {
    ...typography.caption,
    fontWeight: '700',
    color: colors.textMid,
    // 좁은 기기에서 좌우 라벨이 서로 밀어내지 않고 줄바꿈되도록 (space-between 유지).
    flexShrink: 1,
  },
  // 승인본 .onecap — caption ink-2 center.
  oneCap: {
    ...typography.caption,
    color: colors.textMid,
    textAlign: 'center',
    lineHeight: 18,
  },
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 "예상 부위" 배지 (advisoryOrange 재사용,
  // 신규 색 금지). 크롭 이미지 위 칩.
  estimatedBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.advisoryOrangeBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  estimatedBadgeText: {
    ...typography.caption,
    color: colors.advisoryOrange,
    fontWeight: '700',
  },
  halfLabel: {
    position: 'absolute',
    top: 8,
    backgroundColor: colors.brandOverlay,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  halfLabelLeft: { left: 8 },
  halfLabelRight: { right: 8 },
  halfLabelText: { ...typography.caption, color: colors.textWhite, fontWeight: '700' },
  // ── 결함 블록 (승인본 .card.fault + .fault-head) ─────────────────────────
  faultCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1.5,
    borderColor: colors.brandTint,
    borderRadius: radius.card,
    overflow: 'hidden',
  },
  faultHead: {
    backgroundColor: colors.brandTint,
    borderBottomWidth: 1,
    borderBottomColor: colors.brandSoft,
    paddingHorizontal: spacing.cardPadding,
    paddingVertical: 11,
  },
  faultHeadText: {
    ...typography.boxLabel, // 15/700 — 승인본 .fault-head 15/800
    color: colors.brand,
  },
  faultBody: {
    padding: spacing.cardPadding,
    gap: 8,
  },
  headline: {
    ...typography.bodyLg, // 24/700 카드 헤드라인(몸 말/상태) — E2 토큰
    color: colors.textPrimary,
  },
  why: {
    ...typography.bodySm, // 19/400 왜·보조 본문 (lineHeight 25 — 잘림 방지)
    color: colors.textMid,
  },
  // 승인본 .basis — 연회색 배경 + line 보더 (기존 softBg + border 재사용).
  basisBox: {
    backgroundColor: colors.softBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.listItem,
    paddingHorizontal: 11,
    paddingVertical: 9,
  },
  basisText: {
    ...typography.bodySm,
    color: colors.textMid,
  },
  basisBold: {
    fontWeight: '700',
    color: colors.textPrimary,
  },
  // 승인본 .cue — inline-block brand-tint 박스, brand 텍스트 (라벨 없음).
  cueBox: {
    alignSelf: 'flex-start',
    backgroundColor: colors.brandTint,
    borderRadius: radius.button,
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  cueText: { ...typography.bodyMdBold, color: colors.brand }, // 21/700 행동 큐
  // 승인본 .methodline / .facing — 정직 정보 톤 (infoTeal 토큰, 승인 CSS 실측).
  infoBox: {
    backgroundColor: colors.infoTealBg,
    borderWidth: 1,
    borderColor: colors.infoTealBorder,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  infoText: {
    ...typography.bodySm,
    color: colors.infoTeal,
  },
  // 승인본 .numnote — 블록 맨 뒤 작은 회색 줄 (2R 수치 강등).
  numNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // 확인하기 불릿 + 용어줄.
  bullets: { gap: 6 },
  bullet: {
    ...typography.bodySm, // 19/400 (lineHeight 25 — 잘림 방지)
    color: colors.textMid,
  },
  // 강사 연결 줄.
  coachConnect: {
    ...typography.bodySm,
    color: colors.textMid,
  },
  // AI 추정 고지 박스.
  aiNoteBox: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    padding: 12,
  },
  aiNoteText: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  cta: {
    marginTop: 16,
    height: 50,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: { ...typography.button, color: colors.textWhite },
  // belle 09-07 — 보조 액션 문법 (design.md §0, BodyProfilePromptModal.secondary
  // 와 동일): 1px inputBorder 테두리 + 투명 배경 + textPrimary 라벨 + radius.button.
  // 높이는 이 시트의 주 CTA 와 같은 값을 써서 두 버튼이 한 덩어리로 읽히게 한다.
  momentBtn: {
    marginTop: 16,
    height: 50,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: 'transparent',
    justifyContent: 'center',
    alignItems: 'center',
  },
  // 뛰어갈 순간이 없는 항목 — 버튼을 지우지 않고 눌리지 않는 상태로 남긴다.
  momentBtnDisabled: { opacity: 0.4 },
  momentBtnText: { ...typography.buttonSecondary, color: colors.textPrimary },
});
