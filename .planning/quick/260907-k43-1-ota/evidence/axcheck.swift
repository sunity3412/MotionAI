import Foundation
import ApplicationServices

// prompt:false — 승인 팝업을 띄우지 않고 현재 신뢰 상태만 읽는다
let opts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: false] as CFDictionary
let trusted = AXIsProcessTrustedWithOptions(opts)
print("AXIsProcessTrusted=\(trusted)")
