import Foundation
import Vision
import ImageIO

guard CommandLine.arguments.count == 2 else {
  fputs("Usage: vision_ocr <image>\n", stderr)
  exit(2)
}
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
  fputs("Cannot read image\n", stderr)
  exit(1)
}
let width = image.width
let height = image.height
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: image, options: [:])
try handler.perform([request])
let lines: [[String: Any]] = (request.results ?? []).compactMap { observation in
  guard let candidate = observation.topCandidates(1).first else { return nil }
  let box = observation.boundingBox
  let x = Int((box.origin.x * CGFloat(width)).rounded())
  let y = Int(((1 - box.origin.y - box.height) * CGFloat(height)).rounded())
  let w = Int((box.width * CGFloat(width)).rounded())
  let h = Int((box.height * CGFloat(height)).rounded())
  guard !candidate.string.isEmpty, w > 0, h > 0 else { return nil }
  return ["text": candidate.string, "bbox": [x, y, w, h], "score": candidate.confidence]
}
let output: [String: Any] = ["canonical": ["lines": lines]]
let data = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write("\n".data(using: .utf8)!)
