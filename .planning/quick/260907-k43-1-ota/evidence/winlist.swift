import CoreGraphics
import Foundation
let opts: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
if let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] {
  for w in list {
    let owner = w[kCGWindowOwnerName as String] as? String ?? ""
    guard owner.contains("Simulator") else { continue }
    let name = w[kCGWindowName as String] as? String ?? ""
    if let b = w[kCGWindowBounds as String] as? [String: CGFloat] {
      print("\(owner) | \(name) | X=\(b["X"]!) Y=\(b["Y"]!) W=\(b["Width"]!) H=\(b["Height"]!)")
    }
  }
}
