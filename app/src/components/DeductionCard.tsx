// 감점 카드 — 3단 문장 + 인라인 확대비교 + 목표 게이지 + 미션 완결형 (32-10 Task 2).
//
// belle 지적(OPTIMAL 악순환 지점): "현재 94° → 기준 71°로 바꾸라"가 해석 불가.
// 해소(D-08/D-20/D-09/D-10): 카드 하나가 상태(몸 말)→왜(감점 이유)→행동(외부 큐)
// 3단으로 읽히고, 결함 확대비교 합성 PNG 1장([내|정은지], 백엔드 fault_zoom._compose)
// 이 인라인으로 붙어 근거가 되며, 목표 게이지가 "얼마나 남았는지"를 길이로 보여주고,
// 미션 배지가 오늘 할 일을 준다 — 상태+증거+게이지+미션이 카드 하나에 완결(D-20).
// 수치는 게이지의 소형 배지(또는 게이지 불가 시 폴백 수치 배지) 1곳에만 노출된다
// (D-09 — 헤드라인 수치 0).
//
// quick-260903-f2w (검토 표 3 행 4 결함): 종전 이 카드는 내/비교 대상 crop 을
// 사진 2장 분리 URI 쌍으로 기다렸지만 doc 의 faultZoomComparisons[] 는 합성 PNG
// 1장(imageUrl) 뿐이라 모양이 안 맞아 히스토리 전체에서 한 번도 배선된 적이
// 없었다 — pending 동안 스피너 쌍만 떴다 사라지고 done 이 돼도 이미지로 못 바뀜.
// 지금은 doc 모양 그대로 `zoom {imageUrl}` 1장을 받고, 접힘 행에는 사진 유무를
// 표시한다 (표 3 행 1 — "5개 틀렸는데 사진 1장" 의 출구).
//
// quick-260903-ftg — 합성 PNG 렌더(프레임·태그·로딩·실패·재발급·pending)는
// ZoomCompositeImage 로 이동. IN-01 저신뢰 경로의 "예상 부위 (참고)" 카드(result.tsx)
// 와 같은 컴포넌트를 소비한다 (렌더 규칙 사본 0). 이 카드는 zoom/zoomPending 을
// 그 컴포넌트에 넘기기만 한다.
//
// quick-260903-lr6 belle "통과한거 다 넣고" — 접힌 행도 zoom 이 오면 사진 인라인(pill 대신).
//
// props 는 로컬 타입(계약 DeductionRecord 직접 의존 금지) — result.tsx 배선(32-11)이
// doc 필드를 이 모양으로 매핑한다. 이 플랜은 컴포넌트만(interface-first). 카드 상호작용
// (물어보기·점프)은 안정 recordId 로 조인한다(배열 index 금지 — 리뷰 반영).
//
// 방어(리뷰 반영·threat T-32-23): statusLine 부재(legacy doc)=라벨 폴백, cueLine
// 부재(fail-closed)=행동문 생략+강사 유도, 줌 이미지 로딩 placeholder + onError 폴백
// (만료 presigned URL 대응 — 크래시·빈 깨짐 0) + onZoomImageError 재발급 트리거.
//
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용. E2 강조 토큰(32-07) 소비.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { computeGaugeGeometry } from '../lib/gaugeGeometry';
import { colors, layout, radius, spacing, typography } from '../theme';
import { GoalGaugeBar, formatGoalBadge } from './GoalGaugeBar';
import { MissionBadge } from './MissionBadge';
import { ZoomCompositeImage } from './ZoomCompositeImage';

// 카드가 소비하는 record 로컬 모양 (계약의 부분집합 매핑 — 32-11 배선이 채운다).
export interface DeductionCardRecord {
  // 안정 조인 키 (contract §12.3). 물어보기·점프가 이 값으로 조인 — index 금지.
  recordId?: string;
  label: string; // criterionLabelKo 결과 (수치 없는 라벨)
  statusLine?: string; // 상태 (몸 말 헤드라인 — 수치 0)
  whyLine?: string; // 왜 (감점 이유 1줄)
  cueLine?: string; // 행동 (외부 큐 — 수행용). 부재 = fail-closed
  points: number; // SIGNED NEGATIVE (참고용 — 헤드라인 미노출)
  measured?: number; // 게이지·수치 배지 재료
  target?: number;
  unit?: string; // 'deg' 등
  tolerance?: number; // 규칙 상수 유래 — 부재 시 게이지 미표시(수치 배지 폴백)
}

// 확대비교 합성 PNG 1장 — 백엔드 fault_zoom._compose 가 [내 영상 | 비교 대상] 을
// 가로로 합성해 imageUrl 하나로 낸다 (사진 2장 분리 URI 아님). result.tsx 가
// resolveZoomImageUrl(fresh 우선·저장 imageUrl 폴백) 로 조회해 넘긴다.
export interface DeductionCardZoom {
  imageUrl: string;
}

export interface DeductionCardMission {
  isMission: boolean;
  isSafety: boolean;
}

interface DeductionCardProps {
  record: DeductionCardRecord;
  // 확정 확대비교 합성 PNG (펼침·접힘 모드 인라인). 부재 + zoomPending 이면 placeholder
  // (펼침 모드만).
  zoom?: DeductionCardZoom;
  // 이미지 로드 실패 시 재발급 트리거 — useFreshFaultZoomUrls.onZoomImageError
  // (시트 renderCrop 과 동일 규칙, 훅이 single-flight 로 무한 루프를 막는다).
  onZoomImageError?: () => void;
  // 접힘 모드 전용 — 이 record 에 확정 확대 사진이 있음을 행에서 보이게 (표 3 행 1).
  hasZoom?: boolean;
  // 줌 사후 도착 대기(result.faultZoomStatus='pending') — placeholder 1개 렌더.
  zoomPending?: boolean;
  mission?: DeductionCardMission;
  // 우측 crop 라벨 — Mode1='정은지 선수' / Mode3='지난 분석'.
  rightLabel?: string;
  // 기본 펼침. false 면 상태문 1줄 + 펼침 유도만 (순서안 #5 — 나머지 카드 기본 접힘).
  expanded?: boolean;
  onToggle?: () => void;
  // D-28 사용자 담기 진입점 — recordId 기반 조인(부재 시 null 전달, index 금지).
  onAskCoach?: (recordId: string | null) => void;
}

const ASK_COACH_LABEL = '강사님께 물어보기';
// cueLine 부재(fail-closed) 시 행동문 대체 — 일반론 조언 대신 강사 확인 유도.
const FAIL_CLOSED_NOTE = '이 부분은 강사님과 함께 확인하면 더 정확해요';
const HAS_ZOOM_PILL_LABEL = '확대 사진';
const GAUGE_FALLBACK_NOTE = '정확한 수치는 아래 자세한 내역에서 볼 수 있어요';

export function DeductionCard({
  record,
  zoom,
  onZoomImageError,
  hasZoom = false,
  zoomPending = false,
  mission,
  rightLabel = '정은지 선수',
  expanded = true,
  onToggle,
  onAskCoach,
}: DeductionCardProps) {
  // 헤드라인 — statusLine 우선, 부재(legacy doc) 시 라벨 폴백. 어느 경로든 수치 삽입
  // 0 (수치는 게이지 배지/폴백 배지 1곳만 — D-09). label=criterionLabelKo 라 수치 없음.
  const hasStatus =
    typeof record.statusLine === 'string' && record.statusLine.trim().length > 0;
  const headline = hasStatus ? (record.statusLine as string) : record.label;

  // 접힘 모드 — 상태문 1줄 + 펼침 유도 + 확대 사진.
  // quick-260903-f2w 표 3 행 1: 접힌 행에 사진 유무가 안 보여 "사진이 하나뿐" 으로
  // 체감됐다 — 사진 있는 행을 행에서 보이게 한다.
  // quick-260903-lr6: zoom 이 오면 헤드라인 행 아래 사진 자체를 인라인(pill 미렌더 —
  // 사진이 있으니 중복). zoom 없이 hasZoom 만 오면 종전 pill(하위호환). Pressable
  // 전체가 탭 대상 그대로(시트 진입). 사진 간격은 styles.card 의 gap.
  if (expanded === false) {
    const collapsedZoom = zoom ?? null;
    const showZoomPill = hasZoom && collapsedZoom == null;
    const announceZoom = hasZoom || collapsedZoom != null;
    return (
      <Pressable
        style={styles.card}
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={`${headline} — 펼쳐 보기${announceZoom ? ' — 확대 사진 있음' : ''}`}
        hitSlop={4}
      >
        <View style={styles.collapsedRow}>
          <Text style={styles.headlineCollapsed} numberOfLines={2}>
            {headline}
          </Text>
          {showZoomPill ? (
            <View style={styles.zoomPill}>
              <Ionicons name="image-outline" size={14} color={colors.textSecondary} />
              <Text style={styles.zoomPillText}>{HAS_ZOOM_PILL_LABEL}</Text>
            </View>
          ) : null}
          <Ionicons name="chevron-down" size={20} color={colors.textSecondary} />
        </View>
        {collapsedZoom ? (
          <ZoomCompositeImage
            imageUrl={collapsedZoom.imageUrl}
            rightLabel={rightLabel}
            onError={onZoomImageError}
            accessibilityLabel={`내 영상과 ${rightLabel} 확대 비교 이미지`}
          />
        ) : null}
      </Pressable>
    );
  }

  // 게이지 재료 — measured/target/tolerance 모두 있고 기하 유효할 때만 게이지.
  // 규칙 상수(tolerance) 부재 등으로 geometry=null 이면 수치 배지+텍스트로 폴백.
  const hasNumericPair = record.measured != null && record.target != null;
  const gaugeGeo =
    record.measured != null && record.target != null && record.tolerance != null
      ? computeGaugeGeometry(record.measured, record.target, record.tolerance)
      : null;
  const direction: 'increase' | 'decrease' | undefined = hasNumericPair
    ? (record.measured as number) < (record.target as number)
      ? 'increase'
      : 'decrease'
    : undefined;

  // D-14 — 안전 미션은 게임 프레임 제외 (배지 미렌더). 위험 결함 전용 안전 톤은
  // InjuryRiskSection 소관. 여기서는 isMission && !isSafety 에서만 배지.
  const showMissionBadge = !!mission?.isMission && !mission?.isSafety;

  return (
    <View style={styles.card}>
      {/* 1) 상태문 — 몸 말 헤드라인 (수치 0). */}
      <Text style={styles.headline}>{headline}</Text>

      {/* 2) 이유문 1줄 — 있을 때만 (감점·위험 이유). */}
      {record.whyLine ? <Text style={styles.why}>{record.whyLine}</Text> : null}

      {/* 3) 인라인 확대비교 — 합성 PNG 1장 [내 영상 | 비교 대상] (D-20 카드 완결).
          zoom 있으면 이미지(정확 종횡비, 레터박스 0), 없고 pending 이면 같은 모양의
          placeholder 1개(onSnapshot 으로 done 도착 시 이미지로 교체), 둘 다 아니면
          생략. 로딩 skeleton + onError 폴백 캡션 + 재발급 트리거는 ZoomCompositeImage
          소유 (quick-260903-ftg — IN-01 카드와 공유). */}
      {zoom ? (
        <ZoomCompositeImage
          imageUrl={zoom.imageUrl}
          rightLabel={rightLabel}
          onError={onZoomImageError}
          accessibilityLabel={`내 영상과 ${rightLabel} 확대 비교 이미지`}
        />
      ) : zoomPending ? (
        <ZoomCompositeImage pending rightLabel={rightLabel} />
      ) : null}

      {/* 4) 목표 게이지 — 소형 수치 배지가 이 카드의 유일한 수치 노출점(D-09).
          게이지 불가(규칙 상수 부재 등)면 수치 배지+텍스트만 폴백 렌더. */}
      {gaugeGeo ? (
        <GoalGaugeBar
          current={record.measured as number}
          target={record.target as number}
          tolerance={record.tolerance}
          unit={record.unit}
          direction={direction}
        />
      ) : hasNumericPair ? (
        <View style={styles.fallbackRow}>
          <View style={styles.badgePill}>
            <Text style={styles.badgeText}>
              {formatGoalBadge(record.measured as number, record.target as number, record.unit)}
            </Text>
          </View>
          <Text style={styles.fallbackNote}>{GAUGE_FALLBACK_NOTE}</Text>
        </View>
      ) : null}

      {/* 5) 행동문 — 외부 큐(시각 강조). cueLine 부재(fail-closed)면 생략 + 강사 유도. */}
      {record.cueLine ? (
        <View style={styles.cueBox}>
          <Text style={styles.cue}>{record.cueLine}</Text>
        </View>
      ) : (
        <Text style={styles.failClosedNote}>{FAIL_CLOSED_NOTE}</Text>
      )}

      {/* 6) 오늘의 미션 배지 — 안전 미션 제외(D-14). */}
      {showMissionBadge ? (
        <MissionBadge variant="mission" label={record.label} />
      ) : null}

      {/* 7) 강사님께 물어보기 — recordId 기반 조인(index 금지). */}
      {onAskCoach ? (
        <Pressable
          style={({ pressed }) => [styles.askBtn, pressed && styles.askBtnPressed]}
          onPress={() => onAskCoach(record.recordId ?? null)}
          accessibilityRole="button"
          accessibilityLabel={ASK_COACH_LABEL}
          hitSlop={4}
        >
          <Ionicons name="chatbubble-ellipses-outline" size={16} color={colors.brand} />
          <Text style={styles.askText}>{ASK_COACH_LABEL}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  // ScoreBreakdownSection.card 관례 mirror — 토큰만.
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
  },
  collapsedRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  headlineCollapsed: {
    ...typography.bodyLg, // 24/700 카드 헤드라인
    color: colors.textPrimary,
    flex: 1,
  },
  headline: {
    ...typography.bodyLg, // 24/700 카드 헤드라인(몸 말/상태)
    color: colors.textPrimary,
  },
  why: {
    ...typography.bodySm, // 19/400 왜·보조 본문
    color: colors.textMid,
  },
  // 접힘 행 확대 사진 유무 pill (표 3 행 1).
  zoomPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  zoomPillText: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  // 게이지 불가 폴백 — 수치 배지 + 안내(수치 노출은 이 배지 1곳).
  fallbackRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  badgePill: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: { ...typography.badge, color: colors.textPrimary },
  fallbackNote: {
    ...typography.caption,
    color: colors.textSecondary,
    flexShrink: 1,
  },
  // 행동문 — 외부 큐 강조 박스.
  // quick-260831-lcc (belle 2026-08-31 결과 화면 재구성 — 빨강 규율): 대형 분홍
  // 박스(brandTint) → 중립 배경(softBg). cue 텍스트는 이미 textPrimary — 무접촉.
  // askBtn 의 brand 테두리는 CTA 라 유지.
  cueBox: {
    backgroundColor: colors.softBg,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  cue: {
    ...typography.bodyMdBold, // 21/700 행동 큐(외부 초점)
    color: colors.textPrimary,
  },
  failClosedNote: {
    ...typography.bodySm,
    color: colors.textSecondary,
  },
  askBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.brand,
  },
  askBtnPressed: { opacity: 0.8 },
  askText: { ...typography.badge, color: colors.brand },
});
