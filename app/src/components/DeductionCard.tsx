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
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { computeGaugeGeometry } from '../lib/gaugeGeometry';
import { colors, layout, radius, spacing, typography } from '../theme';
import { GoalGaugeBar, formatGoalBadge } from './GoalGaugeBar';
import { MissionBadge } from './MissionBadge';

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
  // 확정 확대비교 합성 PNG (펼침 모드 인라인). 부재 + zoomPending 이면 placeholder.
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
const IMG_FAILED_CAPTION = '이미지를 불러오지 못했어요';
const ZOOM_PENDING_CAPTION = '확대 비교 이미지를 준비하고 있어요';
const HAS_ZOOM_PILL_LABEL = '확대 사진';
const GAUGE_FALLBACK_NOTE = '정확한 수치는 아래 자세한 내역에서 볼 수 있어요';

// 합성 PNG 종횡비 — 백엔드 fault_zoom._compose lockstep: `_OUT=360` 정사각 crop 2장
// + `gap=6` 흰 구분선 → 캔버스 (726, 360). 카드는 이 정확 비율로 컨테이너를 잡아
// contain 레터박스 0 (시트는 imgW/2 근사를 쓴다 — 정확값은 여기서만). 백엔드
// 상수가 바뀌면 같이 바꾼다.
const ZOOM_COMPOSITE_ASPECT = (360 * 2 + 6) / 360;

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
  // 줌 이미지 상태 — 합성 1장 로딩/실패 추적 (만료 presigned URL 방어). 훅은 조기
  // 반환 전 항상 호출(Rules of Hooks).
  const [zoomImgLoading, setZoomImgLoading] = useState(true);
  const [zoomImgFailed, setZoomImgFailed] = useState(false);
  // 재발급으로 imageUrl 이 바뀌면(onZoomImageError → fresh 맵 갱신) 실패 캡션이
  // 남지 않게 리셋 — 새 URL 로 다시 시도한다.
  const zoomImageUrl = zoom?.imageUrl;
  useEffect(() => {
    setZoomImgLoading(true);
    setZoomImgFailed(false);
  }, [zoomImageUrl]);

  // 헤드라인 — statusLine 우선, 부재(legacy doc) 시 라벨 폴백. 어느 경로든 수치 삽입
  // 0 (수치는 게이지 배지/폴백 배지 1곳만 — D-09). label=criterionLabelKo 라 수치 없음.
  const hasStatus =
    typeof record.statusLine === 'string' && record.statusLine.trim().length > 0;
  const headline = hasStatus ? (record.statusLine as string) : record.label;

  // 접힘 모드 — 상태문 1줄 + 펼침 유도 + (있으면) 확대 사진 유무 pill.
  // quick-260903-f2w 표 3 행 1: 접힌 행에 사진 유무가 안 보여 "사진이 하나뿐" 으로
  // 체감됐다 — 사진 있는 행을 행에서 보이게 한다.
  if (expanded === false) {
    return (
      <Pressable
        style={styles.card}
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={`${headline} — 펼쳐 보기${hasZoom ? ' — 확대 사진 있음' : ''}`}
        hitSlop={4}
      >
        <View style={styles.collapsedRow}>
          <Text style={styles.headlineCollapsed} numberOfLines={2}>
            {headline}
          </Text>
          {hasZoom ? (
            <View style={styles.zoomPill}>
              <Ionicons name="image-outline" size={14} color={colors.textSecondary} />
              <Text style={styles.zoomPillText}>{HAS_ZOOM_PILL_LABEL}</Text>
            </View>
          ) : null}
          <Ionicons name="chevron-down" size={20} color={colors.textSecondary} />
        </View>
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
          생략. 로딩 skeleton + onError 폴백 캡션 + 재발급 트리거(시트와 동일). */}
      {zoom ? (
        <View style={styles.zoomFrame}>
          {zoomImgFailed ? (
            <View style={styles.zoomFallback}>
              <Text style={styles.zoomFallbackText}>{IMG_FAILED_CAPTION}</Text>
            </View>
          ) : (
            <>
              <Image
                source={{ uri: zoom.imageUrl }}
                style={styles.zoomImage}
                resizeMode="contain"
                onLoadEnd={() => setZoomImgLoading(false)}
                onError={() => {
                  setZoomImgFailed(true);
                  setZoomImgLoading(false);
                  onZoomImageError?.();
                }}
                accessibilityLabel={`내 영상과 ${rightLabel} 확대 비교 이미지`}
              />
              {zoomImgLoading ? (
                <View style={styles.zoomSkeleton}>
                  <ActivityIndicator color={colors.brand} />
                </View>
              ) : null}
              <View style={[styles.zoomTag, styles.zoomTagLeft]}>
                <Text style={styles.zoomTagText}>내 영상</Text>
              </View>
              <View style={[styles.zoomTag, styles.zoomTagRight]}>
                <Text style={styles.zoomTagText}>{rightLabel}</Text>
              </View>
            </>
          )}
        </View>
      ) : zoomPending ? (
        <View
          style={[styles.zoomFrame, styles.zoomPending]}
          accessibilityRole="progressbar"
          accessibilityLabel={ZOOM_PENDING_CAPTION}
        >
          <ActivityIndicator color={colors.brand} />
          <Text style={styles.zoomPendingText}>{ZOOM_PENDING_CAPTION}</Text>
        </View>
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
  // 인라인 확대비교 컨테이너 — 합성 PNG 정확 종횡비 (fault_zoom._compose lockstep).
  zoomFrame: {
    width: '100%',
    aspectRatio: ZOOM_COMPOSITE_ASPECT,
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.softBg,
    position: 'relative',
  },
  zoomImage: { width: '100%', height: '100%' },
  // 로딩 중 skeleton 오버레이 (토큰 배경).
  zoomSkeleton: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.softBg,
  },
  // onError 폴백 — 이미지 숨김 + 소형 캡션(빈 깨짐 0).
  zoomFallback: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
    backgroundColor: colors.softBg,
  },
  zoomFallbackText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // 사후 도착 대기 placeholder — 이미지와 같은 컨테이너(zoomFrame) 위에 스피너 +
  // 캡션 (시트 imagePending 미러).
  zoomPending: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  zoomPendingText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // 좌/우 반쪽 태그 — 시트 halfLabel 미러.
  zoomTag: {
    position: 'absolute',
    top: 8,
    backgroundColor: colors.brandOverlay,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  zoomTagLeft: { left: 8 },
  zoomTagRight: { right: 8 },
  zoomTagText: {
    ...typography.caption,
    color: colors.textWhite,
    fontWeight: '700',
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
