// Simulator 두 손가락 핀치 합성기 (CGEvent).
// macOS Simulator 규약: Option 누르면 두 손가락, Option+Shift 드래그는 그 쌍의 중심 이동.
// 사용: pinch <anchorX> <anchorY> <startOff> <endOff> [--shift-move-from <x> <y>]
import Foundation
import CoreGraphics

func die(_ m: String) -> Never { FileHandle.standardError.write((m + "\n").data(using: .utf8)!); exit(2) }

let a = CommandLine.arguments
guard a.count >= 5, let ax = Double(a[1]), let ay = Double(a[2]),
      let s0 = Double(a[3]), let s1 = Double(a[4]) else {
  die("usage: pinch anchorX anchorY startOff endOff [fromX fromY]")
}
var moveFrom: CGPoint? = nil
if a.count >= 7, let fx = Double(a[5]), let fy = Double(a[6]) { moveFrom = CGPoint(x: fx, y: fy) }

guard let src = CGEventSource(stateID: .hidSystemState) else { die("no event source") }
let TAP = CGEventTapLocation.cghidEventTap
let OPT: CGEventFlags = .maskAlternate
let OPTSHIFT: CGEventFlags = [.maskAlternate, .maskShift]
let KC_OPTION: Int64 = 58
let KC_SHIFT: Int64 = 56

func flags(_ f: CGEventFlags, keycode: Int64) {
  guard let e = CGEvent(keyboardEventSource: src, virtualKey: CGKeyCode(keycode), keyDown: true) else { return }
  e.type = .flagsChanged
  e.flags = f
  e.post(tap: TAP)
  usleep(60_000)
}

func mouse(_ type: CGEventType, _ p: CGPoint, _ f: CGEventFlags) {
  guard let e = CGEvent(mouseEventSource: src, mouseType: type, mouseCursorPosition: p, mouseButton: .left) else { return }
  e.flags = f
  e.post(tap: TAP)
}

let anchor = CGPoint(x: ax, y: ay)

// 0) 커서를 창 안으로
mouse(.mouseMoved, moveFrom ?? anchor, [])
usleep(200_000)

// 1) Option+Shift 로 핀치 쌍의 중심을 목표 패널로 옮긴다
if let from = moveFrom {
  flags(OPTSHIFT, keycode: KC_OPTION)
  flags(OPTSHIFT, keycode: KC_SHIFT)
  let steps = 12
  for i in 1...steps {
    let t = Double(i) / Double(steps)
    mouse(.mouseMoved, CGPoint(x: from.x + (anchor.x - from.x) * t,
                               y: from.y + (anchor.y - from.y) * t), OPTSHIFT)
    usleep(25_000)
  }
  // Shift 만 해제 (Option 유지)
  flags(OPT, keycode: KC_SHIFT)
} else {
  flags(OPT, keycode: KC_OPTION)
}

// 2) 시작 간격으로 이동
let p0 = CGPoint(x: anchor.x + s0, y: anchor.y)
mouse(.mouseMoved, p0, OPT)
usleep(250_000)

// 3) 두 손가락 접촉 → 벌리기 → 떼기
mouse(.leftMouseDown, p0, OPT)
usleep(120_000)
let steps = 16
for i in 1...steps {
  let t = Double(i) / Double(steps)
  let off = s0 + (s1 - s0) * t
  mouse(.leftMouseDragged, CGPoint(x: anchor.x + off, y: anchor.y), OPT)
  usleep(30_000)
}
usleep(200_000)
mouse(.leftMouseUp, CGPoint(x: anchor.x + s1, y: anchor.y), OPT)
usleep(120_000)

// 4) 수식어 해제
flags([], keycode: KC_OPTION)
print("posted anchor=(\(ax),\(ay)) off \(s0)->\(s1) shiftMove=\(moveFrom != nil)")
