// Copyright 2026 OfficeCLI (https://OfficeCLI.AI)
// SPDX-License-Identifier: Apache-2.0

using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;

namespace OfficeCli.Core.Diagram;

/// <summary>
/// Optional high-fidelity path for the <c>diagram</c> element: render the mermaid
/// source with the <b>real mermaid.js</b> to a PNG — covering every mermaid diagram
/// type (gantt / pie / class / state / er / git / mindmap / …) that the native
/// shape synthesizer does not, at full fidelity.
///
/// <para>Backend cascade, best tool first:
/// <list type="number">
///   <item><b>mmdc</b> (the official mermaid-cli), if installed — purpose-built,
///   one call to a tight PNG.</item>
///   <item><b>Chrome-family</b> browser the user already has (via
///   <see cref="HtmlScreenshot"/>): render mermaid.js in a page and screenshot it.
///   Only mermaid.min.js (~3.5 MB) is fetched to a local cache on first use
///   (mirror → CDN); if that fails the page loads mermaid from the CDN live.</item>
///   <item>otherwise the caller falls back to the native synthesizer
///   (<see cref="DiagramCompiler"/>) — zero dependencies, fully editable shapes.</item>
/// </list>
/// PNG (not SVG) throughout: Office cannot draw mermaid's <c>&lt;foreignObject&gt;</c>
/// HTML labels, so a raster that bakes in the browser's own rendering is required.</para>
/// </summary>
/// <summary>
/// The mermaid source is syntactically invalid (as opposed to an infrastructure
/// failure — missing browser, mermaid.js download, screenshot crash). Derives from
/// <see cref="ArgumentException"/> so the CLI surfaces it as a bad-input error
/// (<c>success:false</c> with the message) rather than a process failure, and so the
/// diagram Add path does NOT fall back to the native synthesizer — every backend
/// rejects the same broken source, and the point is to feed the parse error (with its
/// line number) back so the caller can fix it.
/// </summary>
public sealed class MermaidSyntaxException : ArgumentException
{
    public MermaidSyntaxException(string message) : base(message) { }
}

public static class MermaidImageRenderer
{
    // Pin a major version so cache + mirror + CDN agree and rendering is stable.
    private const string MermaidVersion = "11";
    // Own mirror first (offline-first, no third-party dependency at steady state),
    // then the public CDN as a fallback.
    private const string MirrorUrl =
        "https://d.officecli.ai/assets/mermaid-" + MermaidVersion + ".min.js";
    private const string CdnUrl =
        "https://cdn.jsdelivr.net/npm/mermaid@" + MermaidVersion + "/dist/mermaid.min.js";

    /// <summary>Sentinel prefix stamped into the rendered picture's alt-text so the
    /// mermaid source travels inside the document and the diagram stays regenerable.</summary>
    public const string SourceTag = "mermaid:";

    private static string CacheDir => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".officecli", "cache");
    private static string CachedJsPath => Path.Combine(CacheDir, $"mermaid-{MermaidVersion}.min.js");

    /// <summary>True when any image backend is available: mmdc, or a chrome-family browser.</summary>
    public static bool IsAvailable() => TryLocateMmdc(out _) || HtmlScreenshot.HasChromeFamily();

    /// <summary>
    /// Daily-refresh hook, called from <see cref="UpdateChecker"/>'s once-per-24h
    /// background process (already talking to the mirror). Revalidates an <b>already
    /// cached</b> mermaid.js against the mirror with a conditional request and updates
    /// it if the server's copy changed. Never pre-downloads (first-use owns that),
    /// never blocks, never throws. Only the chrome backend uses this cache; mmdc ships
    /// its own mermaid.
    /// </summary>
    public static void RefreshCacheIfPresent()
    {
        try
        {
            if (!File.Exists(CachedJsPath)) return; // refresh only what the user actually uses
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
            using var req = new HttpRequestMessage(HttpMethod.Get, MirrorUrl);
            req.Headers.IfModifiedSince = new DateTimeOffset(File.GetLastWriteTimeUtc(CachedJsPath));
            using var resp = http.SendAsync(req).GetAwaiter().GetResult();
            if (resp.StatusCode == System.Net.HttpStatusCode.NotModified) return; // unchanged → keep cache
            if (!resp.IsSuccessStatusCode) return;                                 // mirror hiccup → keep cache
            var bytes = resp.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult();
            if (bytes.Length > 500_000)
                File.WriteAllBytes(CachedJsPath, bytes);
        }
        catch { /* best effort — the existing cache stays usable */ }
    }

    /// <summary>
    /// Render <paramref name="mermaid"/> to a temporary PNG file and return its path
    /// (caller owns + deletes it). Tries mmdc first (purpose-built, one call), then a
    /// chrome-family browser; degrades between them so a broken mmdc still yields a
    /// render. Throws <see cref="InvalidOperationException"/> only when no backend
    /// works (message carries the underlying tool's error).
    /// </summary>
    public static string RenderToPngFile(string mermaid)
    {
        Exception? failure = null;
        if (TryLocateMmdc(out var mmdc))
        {
            try { return RenderViaMmdc(mermaid, mmdc); }
            catch (MermaidSyntaxException) { throw; } // bad input — the browser would reject it too
            catch (Exception e) { failure = e; }
        }
        if (HtmlScreenshot.HasChromeFamily())
        {
            try { return RenderViaChrome(mermaid); }
            catch (MermaidSyntaxException) { throw; } // surface the parse error, don't mask it
            catch (Exception e) { failure ??= e; }
        }
        throw failure ?? new InvalidOperationException(
            "render=image needs mermaid-cli (mmdc) or a headless browser (Chrome/Chromium/Edge). "
            + "Install one, or use render=native for the built-in synthesizer.");
    }

    // ----- mmdc (official mermaid-cli) --------------------------------------------------

    private static string? _mmdcExe;
    private static bool _mmdcProbed;

    /// <summary>Locate mmdc: OFFICECLI_MMDC (explicit path) wins, else <c>mmdc</c> on PATH.</summary>
    private static bool TryLocateMmdc(out string exe)
    {
        if (!_mmdcProbed)
        {
            _mmdcProbed = true;
            _mmdcExe = ProbeMmdc();
        }
        exe = _mmdcExe ?? "";
        return _mmdcExe != null;
    }

    /// <summary>Heuristic: does mmdc's stderr/stdout describe a source syntax problem
    /// (vs a crash / environment fault)? mmdc surfaces mermaid's own parser text.</summary>
    private static bool LooksLikeSyntaxError(string msg)
    {
        if (string.IsNullOrEmpty(msg)) return false;
        return msg.Contains("Parse error", StringComparison.OrdinalIgnoreCase)
            || msg.Contains("Lexical error", StringComparison.OrdinalIgnoreCase)
            || msg.Contains("No diagram type detected", StringComparison.OrdinalIgnoreCase)
            || msg.Contains("UnknownDiagramError", StringComparison.OrdinalIgnoreCase)
            || msg.Contains("Expecting ", StringComparison.Ordinal);
    }

    private static string? ProbeMmdc()
    {
        // OFFICECLI_MMDC (explicit path) wins; otherwise find `mmdc` on PATH via the
        // same shared lookup used for chrome/playwright (WhichFirst handles PATHEXT,
        // so "mmdc" resolves mmdc.cmd on Windows).
        var env = Environment.GetEnvironmentVariable("OFFICECLI_MMDC");
        if (!string.IsNullOrWhiteSpace(env) && File.Exists(env)) return env;
        return HtmlScreenshot.Which("mmdc");
    }

    private static string RenderViaMmdc(string mermaid, string exe)
    {
        var inPath = Path.Combine(Path.GetTempPath(), $"ocli_mmd_{Guid.NewGuid():N}.mmd");
        var outPath = Path.ChangeExtension(inPath, ".png");
        File.WriteAllText(inPath, mermaid);
        try
        {
            var psi = new ProcessStartInfo(exe)
            {
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            psi.ArgumentList.Add("-i"); psi.ArgumentList.Add(inPath);
            psi.ArgumentList.Add("-o"); psi.ArgumentList.Add(outPath);
            psi.ArgumentList.Add("-b"); psi.ArgumentList.Add("transparent");
            psi.ArgumentList.Add("-s"); psi.ArgumentList.Add("2"); // HiDPI for crisp raster
            var pcfg = Environment.GetEnvironmentVariable("OFFICECLI_MMDC_PUPPETEER");
            if (!string.IsNullOrWhiteSpace(pcfg) && File.Exists(pcfg))
            {
                psi.ArgumentList.Add("-p"); psi.ArgumentList.Add(pcfg);
            }

            using var p = Process.Start(psi)
                ?? throw new InvalidOperationException("failed to start mmdc.");
            // Async-drain both streams: the serial stderr-then-stdout reads
            // interlocked when mmdc filled the stdout pipe first (bounded by
            // the 120s kill below, but a wasted two minutes per diagram).
            var errTask = p.StandardError.ReadToEndAsync();
            var outTask = p.StandardOutput.ReadToEndAsync();
            if (!p.WaitForExit(120_000))
            {
                try { p.Kill(true); } catch { /* best effort */ }
                throw new InvalidOperationException("mmdc timed out after 120s.");
            }
            if (p.ExitCode != 0 || !File.Exists(outPath))
            {
                var msg = $"{errTask.Result}{outTask.Result}".Trim();
                // A parse/unknown-type failure is bad input, not a broken mmdc; class
                // it as syntax so the Add path surfaces it (and does not fall back).
                if (LooksLikeSyntaxError(msg))
                    throw new MermaidSyntaxException(
                        $"mermaid syntax error: {msg} "
                        + "(fix the mermaid source, or use render=native for the built-in subset).");
                throw new InvalidOperationException($"mmdc failed (exit {p.ExitCode}). {msg}".Trim());
            }
            return outPath;
        }
        finally { try { File.Delete(inPath); } catch { /* best effort */ } }
    }

    // ----- chrome-family browser (mermaid.js in a page → sized screenshot) --------------

    /// <summary>Two chrome passes: dump the DOM to read the diagram's viewBox, then
    /// screenshot at exactly that size (HiDPI). PNG bakes in the browser's rendering
    /// so mermaid's foreignObject labels — invisible to Office as SVG — appear.</summary>
    private static string RenderViaChrome(string mermaid)
    {
        var jsRef = ResolveMermaidJsRef();
        var html = BuildHtml(mermaid, jsRef);
        var htmlPath = Path.Combine(Path.GetTempPath(), $"ocli_mmd_{Guid.NewGuid():N}.html");
        File.WriteAllText(htmlPath, html);
        try
        {
            var dom = HtmlScreenshot.DumpDom(htmlPath)
                ?? throw new InvalidOperationException("headless browser produced no output.");

            // The <title> is the AUTHORITATIVE outcome — not the presence of an <svg>.
            // On a syntax error mermaid.parse() rejects (we capture the message) but
            // STILL injects its red "Syntax error" bomb graphic into the DOM anyway
            // (suppressErrorRendering doesn't stop it). So a viewBox is present even on
            // failure; keying off the svg would screenshot the bomb and "succeed".
            // Trust the title: MMDREADY = real render, MMDSYNTAX = bad input, else infra.
            if (dom.Contains("<title>MMDSYNTAX</title>", StringComparison.Ordinal))
                throw new MermaidSyntaxException(
                    "mermaid syntax error: " + ExtractMermaidMessage(dom)
                    + "\n(fix the mermaid source, or use render=native for the built-in subset).");
            if (!dom.Contains("<title>MMDREADY</title>", StringComparison.Ordinal))
                throw new InvalidOperationException(
                    dom.Contains("<title>MMDERR</title>", StringComparison.Ordinal)
                    ? "mermaid failed to render: " + ExtractMermaidMessage(dom)
                    : "mermaid produced no diagram (mermaid.js failed to load or the render timed out).");

            var (w, h) = ParseSvgSize(dom);
            if (w <= 0 || h <= 0)
                throw new InvalidOperationException("mermaid rendered but produced no measurable svg viewBox.");

            var pngPath = Path.ChangeExtension(htmlPath, ".png");
            if (!HtmlScreenshot.CaptureChromeSized(htmlPath, pngPath,
                    (int)Math.Ceiling(w) + 2, (int)Math.Ceiling(h) + 2))
                throw new InvalidOperationException("headless screenshot failed.");
            return pngPath;
        }
        finally { try { File.Delete(htmlPath); } catch { /* best effort */ } }
    }

    /// <summary>Cache → one-time download → live CDN. Returns a URL usable as a
    /// &lt;script src&gt; (a <c>file://</c> for a cached/downloaded copy, else the CDN).</summary>
    private static string ResolveMermaidJsRef()
    {
        try
        {
            if (File.Exists(CachedJsPath) && new FileInfo(CachedJsPath).Length > 500_000)
                return new Uri(CachedJsPath).AbsoluteUri;

            Directory.CreateDirectory(CacheDir);
            foreach (var url in new[] { MirrorUrl, CdnUrl }) // mirror first, CDN fallback
            {
                try
                {
                    using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
                    var bytes = http.GetByteArrayAsync(url).GetAwaiter().GetResult();
                    if (bytes.Length > 500_000)
                    {
                        File.WriteAllBytes(CachedJsPath, bytes);
                        return new Uri(CachedJsPath).AbsoluteUri;
                    }
                }
                catch { /* try next source */ }
            }
        }
        catch { /* fall through to live CDN */ }
        return CdnUrl; // every download failed → reference the CDN directly in the page
    }

    private static string BuildHtml(string mermaid, string jsRef)
    {
        // Pass the source as base64 so no mermaid character can break out of the
        // HTML/JS context. Render explicitly (startOnLoad:false + mermaid.run) and
        // stamp the title so failures are recoverable from the dumped DOM.
        var b64 = Convert.ToBase64String(Encoding.UTF8.GetBytes(mermaid));
        return
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            // svg{display:block}: an inline <svg> sits on the text baseline, leaving a
            // descender gap BELOW it inside the inline-block wrapper. The fixed-height
            // screenshot window then clips those few pixels → the diagram's bottom edge
            // (e.g. a sequence diagram's bottom actor boxes) gets cut. block removes it.
            + "<style>html,body{margin:0;padding:0;background:transparent;font-size:0}"
            + "#d{display:inline-block}#d svg{display:block}</style>"
            + $"<script src=\"{jsRef}\"></script></head>"
            // Hidden sink for a failure message. mermaid's parse error is multi-line
            // with an aligned caret ('^') under the offending column; document.title
            // would flatten the newlines and misalign the caret, so carry the verbatim
            // message here (a <pre> preserves whitespace) and use the title only as the
            // one-word outcome SIGNAL (MMDREADY / MMDSYNTAX / MMDERR).
            + "<body><pre id=\"mmderr\" style=\"display:none\"></pre>"
            + "<div id=\"d\" class=\"mermaid\"></div><script>"
            // atob yields a BYTE string (one Latin-1 char per byte); decode those
            // bytes back as UTF-8 so CJK/emoji in the mermaid source survive. A bare
            // atob() would render "提交" as mojibake ("æ¤").
            + $"const src=new TextDecoder().decode(Uint8Array.from(atob(\"{b64}\"),c=>c.charCodeAt(0)));"
            + "document.getElementById('d').textContent=src;"
            + "window.addEventListener('load',async()=>{try{"
            // htmlLabels:false → mermaid emits real SVG <text> instead of <foreignObject>
            // (HTML), which Office's SVG renderer cannot display — otherwise every
            // node/label comes out blank. securityLevel:loose allows the run.
            // suppressErrorRendering: on invalid syntax mermaid otherwise silently
            // renders a red "Syntax error in text" bomb graphic and returns success —
            // we would screenshot the bomb and embed it. With this off, run() throws.
            + "mermaid.initialize({startOnLoad:false,securityLevel:'loose',htmlLabels:false,"
            + "flowchart:{htmlLabels:false},class:{htmlLabels:false},suppressErrorRendering:true});"
            // Validate first: mermaid.parse() throws a precise, line-numbered error
            // ('Parse error on line N: … Expecting X, got Y') without touching the DOM.
            // Stamp it under a DISTINCT title so the host tells a user syntax error
            // (surface it, let the agent fix the source) apart from an infra failure
            // (browser/mermaid.js problem — fall back to the native synthesizer).
            + "try{await mermaid.parse(src);}catch(pe){"
            + "document.getElementById('mmderr').textContent=(pe&&pe.message?pe.message:String(pe));"
            + "document.title='MMDSYNTAX';return;}"
            + "await mermaid.run({nodes:[document.getElementById('d')]});"
            // Tighten the SVG to its REAL content bounds. mermaid's own viewBox
            // overshoots for some types (sequence diagrams reserve far more width/
            // height than they draw), which otherwise bakes a big transparent band
            // into the screenshot. getBBox() is the true rendered geometry; rewrite
            // viewBox + width/height to it (+small pad) so the capture is a tight crop.
            // pad clears ink that getBBox ignores: getBBox returns pure geometry, but
            // mermaid drop-shadows (filter:drop-shadow(3px 5px 2px …)) paint several px
            // past it — a 4px pad clipped the bottom actor boxes of a sequence diagram.
            // 14 covers the largest shadow (offset 5 + blur 2) with margin to spare.
            + "try{const s=document.querySelector('#d svg');if(s){const b=s.getBBox();"
            + "const p=14,x=b.x-p,y=b.y-p,w=Math.ceil(b.width+2*p),h=Math.ceil(b.height+2*p);"
            + "s.setAttribute('viewBox',x+' '+y+' '+w+' '+h);"
            + "s.setAttribute('width',w);s.setAttribute('height',h);"
            + "s.style.maxWidth=w+'px';s.style.width=w+'px';s.style.height=h+'px';}}catch(e){}"
            + "document.title='MMDREADY';"
            + "}catch(e){document.getElementById('mmderr').textContent="
            + "(e&&e.message?e.message:String(e));document.title='MMDERR';}});"
            + "</script></body></html>";
    }

    /// <summary>Pull the verbatim failure message out of the hidden &lt;pre id="mmderr"&gt;
    /// in the dumped DOM. The &lt;pre&gt; preserves mermaid's newlines (so its caret '^'
    /// stays aligned under the offending column); the browser HTML-escapes the text, so
    /// undo the common entities WITHOUT collapsing whitespace. Falls back to a generic
    /// note if the sink is missing.</summary>
    private static string ExtractMermaidMessage(string dom)
    {
        var m = Regex.Match(dom, "<pre id=\"mmderr\"[^>]*>(.*?)</pre>", RegexOptions.Singleline);
        if (!m.Success || string.IsNullOrWhiteSpace(m.Groups[1].Value))
            return "(no detail reported)";
        var s = m.Groups[1].Value
            .Replace("&amp;", "&").Replace("&lt;", "<").Replace("&gt;", ">")
            .Replace("&quot;", "\"").Replace("&#39;", "'");
        return s.Trim('\n', '\r', ' ', '\t');
    }

    /// <summary>Read the rendered diagram's CSS-pixel size from the svg viewBox in
    /// the dumped DOM (mermaid writes <c>viewBox="0 0 W H"</c>). (0,0) if not found.</summary>
    private static (double w, double h) ParseSvgSize(string dom)
    {
        var m = Regex.Match(dom, @"<svg[^>]*\bviewBox=""[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)""",
            RegexOptions.IgnoreCase);
        if (m.Success
            && double.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out var w)
            && double.TryParse(m.Groups[2].Value, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out var h))
            return (w, h);
        return (0, 0);
    }
}
