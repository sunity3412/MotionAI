"""Phase 35 — 합성 비교 영상 기계 판정 리그 (돌파 ②의 첫 조각, 라이브러리).

기원: backend/scripts/verify_render_prototype.py 의 **순수 이동** (quick-260808-jix).
렌더 결과를 belle/앱에 보내기 **전에** 기계가 판독한다 — "전 항목 PASS 아니면 전달 없음".
운영 소비자 = pipeline `_run_deferred_compare_render`: verify ALL PASS 인 mp4 만
S3 업로드 + doc renderedCompare done 부착 (FAIL = failed 마킹, 업로드 0).

판정 항목 (v0 + v1 + v2):
  A. 길이 — 실제 mp4 길이 == 렌더 계획 길이 (±0.3s)
  A2. 정지 수 — 렌더된 정지 수 == 계획 정지 수 (조용한 탈락 검출)
  B. 정지 정적성 — 각 freeze 창 중앙 1s 의 프레임 차분(diff) ≈ 0 (프리즈가 진짜 멈춰있나)
  C. 재생 동적성 — 재생 구간 표본의 프레임 차분 > 정지의 10배 (영상이 진짜 움직이나)
  D. 음성 배치 — 각 voice 창 mean dB > -45 (발화 존재), 재생 구간 표본 < -70 (무음)
  E. 저더(v2, 클러스터 스터터) — **전 재생 구간 스캔**, 좌/우 패널 각각 모션-괄호
     정지 이벤트(dup run 2..5, 양옆 실모션)가 2s 창에 4회+ 몰리면 FAIL.
     v1(창 표집 반복률 ≤15%)의 교체 근거 (2026-08-08 실 E2E 라운드, orchestrator
     처분 ②): 창-반복률은 승인 5편이 전 구간 16~24% 균일 저속(run=1) 문법을
     보유한 걸 표집 운으로만 통과시키고, 신선 doc 의 같은 문법을 창 착지 위치
     때문에 FAIL 시킨 결함 판정기였다. v2 는 belle 가 실제 반려한 v1 증상
     ("가다-서다" 클러스터)을 전 구간에서 잡고, 승인 문법(균일 슬로모·경계 정착
     버스트·스틸 크롤)은 통과시킨다 — 완화가 아니라 판정 대상의 교정 + 표집 운
     제거(강화). 상수 근거는 stutter_stop_events/STUTTER_* 주석.
  F. 웹 재생성 — moov(재생정보)가 mdat(본체) 앞 (faststart — 사파리 스트리밍)

v0 미포함(후속): whisper 전사 == 자막 문장 대조(로컬 whisper 미설치 — Pod 리그에서),
자막 픽셀 OCR. 미포함은 여기 명시해 둔다 — 조용한 생략 금지.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()

# ── E v2 (클러스터 스터터) 상수 — 전부 구조 유도, 근거 박제 ─────────────────
# dup 임계 — v1 승계 (360px 그레이스케일 평균 절대차; 동일 인코드 프레임 ≈ 0).
STUTTER_DUP_MAX = 0.05
# '가다'(실모션) 하한 = dup 임계 ×10 — C 재생 동적성의 decade-분리 구조 승계
# ("재생 diff > 정지의 10배"). 스틸 콘텐츠의 0.05~0.2대 플리커(승인 pdshapefault
# 헤드 실측 0.05~0.06 이웃)는 '가다'가 아니므로 정지 이벤트를 만들지 못한다.
STUTTER_MOTION_MIN = 0.5
# 정지 이벤트 run 대역 = 2..5 프레임 (67~167ms @30fps):
#   run 1 (33ms) = 표준 풀다운 계열 비가시 홀드 — 승인 5편 실측의 지배 성분
#     (elbow 56/peterpan 4/fresh 62 전부 run=1, 균일 슬로모 문법).
#   run ≥6 (≥200ms) = '멈춤/스틸' 의미론 (승인 pdshapefault 크롤 run 7·9 —
#     의도 정지는 B 가, 콘텐츠 스틸은 저더가 아님).
STUTTER_RUN_MIN = 2
STUTTER_RUN_MAX = 5
# 지속 리듬 판정 — 2s 창에 정지 이벤트 4회+ = "가다-서다" 반복 성립.
#   승인 코퍼스 실측 상계 = 3회 (powerspin 꼬리 30.8~31.2s / pdshapefault 헤드
#   0.5~0.8s — 구간 경계 ~0.5s 정착 버스트, belle 승인 렌더). v1 저더 케이던스
#   (hold 2~3 + move 2~3 반복) = 초당 5~7회 → 2s 창 10회+ — 4 는 승인 상계 초과
#   & v1 대비 1/2.5 여유의 최소 정수.
STUTTER_WIN_S = 2.0
STUTTER_FAIL_COUNT = 4
# 재생 구간 경계 margin — freeze 진입/복귀 크로스페이드(FADE_S 0.17s) + 반올림
# 배제. 0.5s 미만 구간은 스캔 생략 (이벤트 리듬 판정 불능 길이).
PLAYBACK_MARGIN_S = 0.3


def playback_regions(report: dict, actual: float, margin: float = PLAYBACK_MARGIN_S) -> list[tuple[float, float]]:
    """재생 구간 (freeze 밖, 경계 margin 제외) — (start, end) out-초 목록."""
    ivs = sorted(
        (fz["voiceStartOutS"], fz["voiceStartOutS"] + fz["freezeS"])
        for fz in report.get("freezes", [])
    )
    regions: list[tuple[float, float]] = []
    prev = 0.0
    for s, e in ivs:
        if s - prev > 2 * margin:
            regions.append((prev + margin, s - margin))
        prev = max(prev, e)
    if actual - prev > 2 * margin:
        regions.append((prev + margin, actual - margin))
    return regions


def stutter_stop_events(diffs: np.ndarray, fps: float = 30.0) -> list[float]:
    """모션-괄호 정지 이벤트 시각 목록 (초, 구간-로컬) — E v2 의 순수 판정 코어.

    이벤트 = dup(diff<STUTTER_DUP_MAX) 최대 run 중:
      · 길이 STUTTER_RUN_MIN..MAX (67~167ms 스터터 지각 대역)
      · **양옆** 인접 비-dup 전이가 실모션(≥STUTTER_MOTION_MIN) — "가다-서다-가다"
        의 '가다' 성립. 구간 가장자리에 닿은 run 은 한쪽 '가다'를 확인할 수 없어
        이벤트 아님 (fail-closed 아님 주의 — 저더는 지속 리듬이라 가장자리 1개
        제외가 판정을 바꾸지 않고, 경계 정착 버스트 오검을 줄인다).
    합성 역검증: tests/phase35/test_compare_verify_stutter.py (v1형 케이던스 FAIL 핀).
    """
    dup = diffs < STUTTER_DUP_MAX
    events: list[float] = []
    i, n = 0, len(dup)
    while i < n:
        if not dup[i]:
            i += 1
            continue
        j = i
        while j < n and dup[j]:
            j += 1
        run = j - i
        if (
            STUTTER_RUN_MIN <= run <= STUTTER_RUN_MAX
            and i > 0 and j < n  # 양옆 이웃 존재 (구간 가장자리 run 제외)
            and diffs[i - 1] >= STUTTER_MOTION_MIN
            and diffs[j] >= STUTTER_MOTION_MIN
        ):
            events.append(i / fps)
        i = j
    return events


def worst_stutter_window(events: list[float], win_s: float = STUTTER_WIN_S) -> int:
    """슬라이딩 창(win_s) 내 최대 이벤트 수 — 지속 리듬 판정량."""
    if not events:
        return 0
    ts = sorted(events)
    return max(sum(1 for t in ts if t0 <= t < t0 + win_s) for t0 in ts)


def duration_s(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def mean_db(path: Path, start: float, dur: float) -> float:
    out = subprocess.run(
        [FF, "-ss", str(start), "-t", str(dur), "-i", str(path),
         "-map", "0:a", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.search(r"mean_volume: ([-\d.]+) dB", out)
    return float(m.group(1)) if m else -120.0


def frame_diff(path: Path, start: float, tmp: Path, n: int = 6, fps: float = 6.0) -> float:
    for f in tmp.glob("*.png"):
        f.unlink()
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(start), "-t", str(n / fps),
                    "-i", str(path), "-vf", f"fps={fps},scale=180:-2", str(tmp / "%03d.png")],
                   check=True)
    imgs = [np.asarray(Image.open(p).convert("L"), dtype=float)
            for p in sorted(tmp.glob("*.png"))]
    if len(imgs) < 2:
        return -1.0
    return float(np.mean([np.mean(np.abs(imgs[i + 1] - imgs[i])) for i in range(len(imgs) - 1)]))


def verify(mp4: Path, report: dict, workdir: Path) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    def check(name: str, passed: bool, detail: str):
        nonlocal ok
        ok &= passed
        lines.append(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    tmp = workdir / "_rigtmp"
    tmp.mkdir(parents=True, exist_ok=True)

    actual = duration_s(mp4)
    planned = float(report["outDurationS"])
    check("A 길이", abs(actual - planned) <= 0.3, f"actual={actual:.2f}s planned={planned:.2f}s")

    # A2. 정지 소실 — mp3 를 가진 record 수와 렌더된 정지 수가 다르면 조용한 탈락
    # (피터팬 실측: 순간이 영상 끝 밖이라 정지 0 으로 통과했던 갭의 기계화).
    expected = report.get("expectedFreezes")
    if expected is not None:
        check("A2 정지 수", len(report.get("freezes", [])) == int(expected),
              f"rendered={len(report.get('freezes', []))} expected={expected}")

    freezes = report.get("freezes", [])
    play_probe = 1.0 if not freezes or freezes[0]["voiceStartOutS"] > 2.0 else max(
        0.2, freezes[0]["voiceStartOutS"] - 1.5)
    # 실 E2E 라운드 (2026-08-08, analysis 2fe3ae94…) — C/D-무음 probe 침범 교정.
    # 첫 정지가 이른 편(voiceStart 0.47s)에서 play_probe=0.2 의 측정창(C 1.0s /
    # D-무음 0.8s)이 첫 정지 음성 구간과 겹쳐, 실제로는 무음인 재생 구간
    # (실측: 0.2~0.45s -91dB / 정지-간 -91dB / tail -120dB)을 -24.6dB FAIL 로
    # 오판했다. E 가 이미 가진 "이른 첫 정지 → 창 이동" 계열의 측정창 교정 —
    # 판정 기준(무음 <-70dB, 동적성 임계)은 그대로다 (리그 완화 아님).
    # 침범 시에만 첫 재생 갭(≥1.5s)으로 재배치 — 침범 없는 편(픽스처 3편 실측
    # head 갭 6s+)은 현행 probe 그대로 (승인 판정 라인 불변).
    probe_win_s = 1.0  # C frame_diff(n=6, fps=6) 창 — D-무음 0.8s 를 포함
    intervals = [
        (fz["voiceStartOutS"], fz["voiceStartOutS"] + fz["freezeS"]) for fz in freezes
    ]
    if any(s < play_probe + probe_win_s and play_probe < e for s, e in intervals):
        prev_end = 0.0
        for s, e in intervals:
            if s - prev_end >= 1.5:
                break
            prev_end = e
        gap_start, gap_end = prev_end, next(
            (s for s, _ in intervals if s > prev_end), actual
        )
        if gap_end - gap_start >= 1.5:
            relocated = gap_start + 0.3
            lines.append(
                f"  [INFO] probe 재배치: {play_probe:.1f}s -> {relocated:.1f}s "
                f"(첫 정지 침범 — 재생 갭 {gap_start:.1f}~{gap_end:.1f}s)"
            )
            play_probe = relocated
        # 갭 1.5s 미만(정지 연속 편성) = 현행 probe 유지 — 정직 FAIL 허용.

    diffs_frozen = []
    for fz in freezes:
        mid = fz["voiceStartOutS"] + fz["freezeS"] / 2
        d = frame_diff(mp4, mid, tmp)
        diffs_frozen.append(d)
        check(f"B 정지 정적성 {fz['rid']}", 0 <= d < 0.5, f"diff={d:.3f} @out {mid:.1f}s")

    d_play = frame_diff(mp4, play_probe, tmp)
    if freezes:
        base = max(max(diffs_frozen), 1e-3)
        check("C 재생 동적성", d_play > 10 * base or d_play > 2.0,
              f"play diff={d_play:.2f} vs frozen max={max(diffs_frozen):.3f}")
    else:
        check("C 재생 동적성", d_play > 1.0, f"play diff={d_play:.2f} (freeze 0 편)")

    for fz in freezes:
        db = mean_db(mp4, fz["voiceStartOutS"] + 0.2, min(2.5, fz["freezeS"] - 0.6))
        check(f"D 음성 존재 {fz['rid']}", db > -45, f"mean={db:.1f}dB @out {fz['voiceStartOutS']:.1f}s")
    if freezes:
        db_sil = mean_db(mp4, play_probe, 0.8)
        check("D 재생 무음", db_sil < -70, f"mean={db_sil:.1f}dB @out {play_probe:.1f}s")

    # E v2. 클러스터 스터터 — **전 재생 구간 스캔** (창 표집의 착지-운 제거).
    # 좌/우 패널 각각: 모션-괄호 정지 이벤트(stutter_stop_events)가 어느 2s 창에
    # STUTTER_FAIL_COUNT(4)회+ 몰리면 "가다-서다" 지속 리듬 = FAIL. 균일 슬로모
    # (전 run=1)·경계 정착 버스트(승인 실측 3회@0.4s)·스틸 크롤(run≥6)은 PASS.
    regions = playback_regions(report, actual)
    scanned = 0
    worst = {"user": 0, "ref": 0}
    total = {"user": 0, "ref": 0}
    for (rs, re_) in regions:
        if re_ - rs < 0.5:
            continue  # 리듬 판정 불능 길이 — 스캔 생략
        for f in tmp.glob("*.png"):
            f.unlink()
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(rs), "-t", str(re_ - rs),
                        "-i", str(mp4), "-vf", "fps=30,scale=360:-2", str(tmp / "%04d.png")],
                       check=True)
        imgs = [np.asarray(Image.open(p).convert("L"), dtype=float)
                for p in sorted(tmp.glob("*.png"))]
        if len(imgs) < 3:
            continue
        scanned += len(imgs)
        half = imgs[0].shape[1] // 2
        for label, sl in (("user", slice(None, half)), ("ref", slice(half, None))):
            diffs = np.array([np.mean(np.abs(b[:, sl] - a[:, sl]))
                              for a, b in zip(imgs, imgs[1:])])
            events = stutter_stop_events(diffs)
            total[label] += len(events)
            worst[label] = max(worst[label], worst_stutter_window(events))
    if scanned >= 10:
        for label in ("user", "ref"):
            check(
                f"E 저더 {label}",
                worst[label] < STUTTER_FAIL_COUNT,
                f"정지이벤트={total[label]} 최악{STUTTER_WIN_S:.0f}s창={worst[label]} "
                f"(임계 {STUTTER_FAIL_COUNT}, 재생 {scanned}프레임 전수 스캔)",
            )
    else:
        check("E 저더", False, "재생 구간 프레임 추출 부족")

    # F. 웹 재생성 — moov(재생정보)가 mdat(본체) 앞에 있어야 사파리 스트리밍이
    # 소리·스크럽 정상 (2026-08-07 belle "오디오 안 나옴·확 멈춤" 원인 박제).
    head = open(mp4, "rb").read(64 * 1024)
    mi, di = head.find(b"moov"), head.find(b"mdat")
    check("F 웹 재생성(faststart)", 0 <= mi < di if di >= 0 else mi >= 0,
          f"moov@{mi} mdat@{di} (64KB 헤더 내)")

    return ok, lines
