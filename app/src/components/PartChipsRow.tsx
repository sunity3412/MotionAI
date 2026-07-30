// 부위 칩 행 (승인 목업 7R ① `.jointchips` — quick-260730-szk, 33-G S3/F-8).
//
// 승인 스펙 원본 = `.planning/phases/33-result-trust-recovery/mockups/index.html`
// (7R, belle 승인 2026-07-29):
//   `:192-196` `.jointchips{display:flex; gap:8; flex-wrap:wrap}` /
//              `button{border:1px solid line-2; background:#fff; border-radius:999px;
//               padding:8px 14px; font-size:14px; font-weight:800}` /
//              `.ref{color:#8b93a1; border-style:dashed; font-weight:600}`
//   `:338-342` 실제 칩 3개 = `다리` `어깨` `참고: 손`
//   `:317`     "그룹이나 아래 **부위 버튼**을 누르면 ② 상세로 이동해요"
//   `:349`     "화면의 표시 수 = **항목 수** = 3"
//
// 왜 이 컴포넌트가 필요한가: F-8(D-42)로 **상시 마커가 제거**된다(결과 화면에 들어
// 오자마자 설명 없는 표시가 영상을 덮던 것이 belle 반려). 상시 진입점을 잃지 않기
// 위해 승인본 ① 이 원래 갖고 있던 부위 칩 행이 그 역할을 대신한다 — 이 행은 신규
// 발명이 아니라 **승인본에 있었는데 앱에 없던 것**(S3 PARTIAL 의 실체)이다.
//
// 책임 경계: 칩 목록·라벨·부위 정의는 `lib/deductionSheet.buildPartChips` 소유
// (부위 키 사본 0벌 — 시트·마커 그룹과 같은 단위). 이 컴포넌트는 **렌더만** 한다.
//
// 카피 규칙: 새 문장 신설 0 (D-05·S5 "기본 화면 새 문장 0"). 라벨은 빌더 산출,
// 참고 안내는 `ADVISORY_NOTE_KO` 상수. 이모지 0.
//
// 승인 CSS → 앱 토큰 매핑 (목업 px 는 데스크톱 스케일 — 앱은 토큰 우선, hex 리터럴 0):
//   border 1px solid line-2      → colors.divider + StyleSheet.hairlineWidth 대신 1
//   background #fff              → colors.cardBg
//   border-radius 999px          → 999 (pill — 토큰 radius 는 카드/버튼용 유한값뿐)
//   padding 8px 14px             → 8 / 14 (칩 내부 여백, 화면 여백 토큰과 별 축)
//   font-size 14 / weight 800    → typography.badge (D-05 하한 17 준수 — 목업 14 는
//                                  데스크톱 값이라 그대로 쓰면 belle "너무 작음" 재발)
//   .ref dashed / 약한 글자      → borderStyle 'dashed' + colors.advisoryOrange (N-5)
//
// ⚠ 플랫폼 한계 (N-20, 정직 기록): RN iOS 는 `borderRadius > 0` 인 View 의
// `borderStyle: 'dashed'` 를 실선으로 그린다(RN 장기 미해결). 승인본 `.ref` 는
// pill(999px) + dashed 라 iOS 에서는 점선이 표현되지 않을 수 있다. 그 경우 참고 칩의
// 구분은 **라벨 접두("참고: ")+ advisoryOrange 색**이 담당한다 — 둘 다 데이터에서
// 나오는 사실이라 거짓 표기가 아니다. S2 의 판정축인 **영상 위 마커**의 점선은 SVG
// `strokeDasharray` 라 이 한계와 무관하다. 실제 렌더 여부 = 시뮬 확인 위임.

import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ADVISORY_NOTE_KO, type PartChip } from '../lib/deductionSheet';
import { colors, typography } from '../theme';

interface Props {
  /** `buildPartChips` 산출. 빈 배열이면 caller 가 행 자체를 렌더하지 않는다. */
  chips: readonly PartChip[];
  /** 감점 칩 탭 → 그 부위 상세 시트 (기존 시트 state 재사용 — 진입점 추가). */
  onPressPart: (recordIndex: number) => void;
}

export function PartChipsRow({ chips, onPressPart }: Props) {
  // 참고 칩은 시트가 아니라 인라인 안내 1줄을 펼친다 (N-6 — advisory 는 record 가
  // 없어 시트 뷰모델 입력이 성립하지 않는다. 없는 시트를 만드는 것은 새 범위).
  const [noteOpen, setNoteOpen] = useState(false);
  if (chips.length === 0) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {chips.map((chip) => {
          if (chip.kind === 'advisory') {
            return (
              <Pressable
                key={`chip-adv-${chip.partKey}`}
                onPress={() => setNoteOpen((v) => !v)}
                accessibilityRole="button"
                accessibilityLabel={`${chip.label} — ${ADVISORY_NOTE_KO}`}
                accessibilityState={{ expanded: noteOpen }}
                hitSlop={8}
                style={[styles.chip, styles.chipAdvisory]}
              >
                <Text style={[styles.chipText, styles.chipTextAdvisory]}>
                  {chip.label}
                </Text>
              </Pressable>
            );
          }
          const target = chip.firstRecordIndex;
          if (target == null) return null;
          return (
            <Pressable
              key={`chip-${chip.partKey}`}
              onPress={() => onPressPart(target)}
              accessibilityRole="button"
              accessibilityLabel={`${chip.label} 부위 상세 보기`}
              hitSlop={8}
              style={styles.chip}
            >
              <Text style={styles.chipText}>{chip.label}</Text>
            </Pressable>
          );
        })}
      </View>
      {noteOpen ? <Text style={styles.note}>{ADVISORY_NOTE_KO}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 10,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.divider,
    backgroundColor: colors.cardBg,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  chipAdvisory: {
    borderStyle: 'dashed',
    borderColor: colors.advisoryOrange,
  },
  chipText: {
    ...typography.badge,
    color: colors.textPrimary,
  },
  chipTextAdvisory: {
    color: colors.advisoryOrange,
  },
  note: {
    ...typography.caption,
    color: colors.textMid,
    marginTop: 8,
  },
});
