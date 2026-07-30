// Copyright 2026 OfficeCLI (https://OfficeCLI.AI)
// SPDX-License-Identifier: Apache-2.0

using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
using OfficeCli.Core;
using OfficeCli.Core.Plugins;

namespace OfficeCli.Handlers;

public static class DocumentHandlerFactory
{
    public static IDocumentHandler Open(string filePath, bool editable = false)
    {
        // An empty/whitespace path otherwise falls through to File.Exists →
        // "File not found: " with a blank tail, which actively misleads: the
        // caller can't tell the file is *missing as an argument* from *present
        // but wrong*. The single most common way to hit this is an MCP/batch
        // call that omits the top-level `file` (e.g. a model that replicates the
        // single-command shape and puts `file` inside each batch item instead).
        // Give one clear, project-wide message at the shared open chokepoint.
        if (string.IsNullOrWhiteSpace(filePath))
            throw new CliException("No document file specified — the file path is required. "
                + "In MCP/batch, pass `file` as the top-level argument (it applies to every command); "
                + "do not put `file` inside individual batch commands.")
            {
                Code = "file_required",
                Suggestion = "Provide the document path as the top-level file argument."
            };

        if (!File.Exists(filePath))
            throw new CliException($"File not found: {filePath}")
            {
                Code = "file_not_found",
                Suggestion = "Check the file path. Use an absolute path or a path relative to the current directory.",
                Help = "officecli create <path> --type docx|xlsx|pptx"
            };

        // CONSISTENCY(corrupt-file-rejection): a 0-byte file is silently
        // accepted by Open XML SDK 3.x in read-write mode (it materialises an
        // empty Package), but the resulting handler returns a fake root node
        // with no parts. CLI commands that follow then report success and
        // exit 0 even though the document is unusable. Reject the file
        // up-front so the same file_not_found / corrupt_file UX applies that
        // direct-mode (read-only) Open already gave for 0-byte files.
        if (new FileInfo(filePath).Length == 0)
            throw new CliException($"Cannot open {Path.GetFileName(filePath)}: file is 0 bytes (not a valid Office document).")
            {
                Code = "corrupt_file",
                Suggestion = "Recreate the file with: officecli create <path>"
            };

        var ext = Path.GetExtension(filePath).ToLowerInvariant();

        // CONSISTENCY(dos-hardening): reject decompression bombs before the
        // Open XML SDK / System.IO.Packaging touches the package. A few KB of
        // zip can inflate to many gigabytes and OOM the process (or, on a
        // 32-bit size-field overflow, surface only as a raw "Arithmetic
        // operation resulted in an overflow"). Only the native zip formats are
        // inspected; plugin-handled formats may not be zips and are left to
        // their own handler. See DocumentLimits for the thresholds.
        if (ext is ".docx" or ".xlsx" or ".pptx")
            GuardDecompressionBomb(filePath);

        // CONSISTENCY(dangling-rel-repair): the reactive catch below only fires
        // when the SDK throws at Open time (the docx LabelInfo case, where the
        // part graph is walked eagerly). PowerPoint slides load their typed
        // subparts (SlideLayoutPart, diagram drawing parts, …) LAZILY, so a
        // dangling internal relationship on a slide surfaces only later — during
        // `dump`/`query` traversal — where it escapes this try/catch and crashes
        // the command. Real producers ship such decks (e.g. a diagramDrawing
        // rId pointing at a diagrams/drawingN.xml that was never written) and
        // PowerPoint tolerates them. Strip the dangling rels up-front so every
        // command (not just Open) survives, reusing the same in-place repair the
        // reactive path uses. The scan is read-only and only rewrites when a
        // dangling rel is actually present, so the clean-file path pays only a
        // cheap .rels read.
        if ((ext is ".docx" or ".xlsx" or ".pptx") && HasDanglingInternalRels(filePath))
            StripDanglingPackageRels(filePath);

        try
        {
            return OpenHandler(filePath, ext, editable);
        }
        catch (Exception ex) when (IsEncodingException(ex))
        {
            // Files created by python-pptx (lxml) use encoding="ascii" which Open XML SDK rejects.
            // Fix the XML declarations in-place and retry.
            FixXmlEncoding(filePath);
            return OpenHandler(filePath, ext, editable);
        }
        catch (Exception ex) when (IsDanglingPartException(ex))
        {
            // Some producers strip a part (e.g. a sensitivity-label
            // docMetadata/LabelInfo.xml) but leave its relationship behind.
            // The SDK throws "Part: X doesn't exist in the package" on the
            // first part-graph walk, so EVERY command failed on the file even
            // though Word opens it fine (it ignores the dangling rel). Remove
            // the dangling internal relationships in-place and retry — mirrors
            // the FixXmlEncoding repair-and-retry path above.
            StripDanglingPackageRels(filePath);
            return OpenHandler(filePath, ext, editable);
        }
        catch (DocumentFormat.OpenXml.Packaging.OpenXmlPackageException ex)
        {
            throw new CliException($"Cannot open {Path.GetFileName(filePath)}: {ex.Message}", ex)
            {
                Code = "corrupt_file",
                Suggestion = "Verify the file is a valid .docx/.xlsx/.pptx (e.g. unzip -t)."
            };
        }
        catch (System.IO.FileFormatException ex)
        {
            // Thrown by System.IO.Packaging when the file is not a valid OOXML zip container.
            throw new CliException($"Cannot open {Path.GetFileName(filePath)}: {ex.Message}", ex)
            {
                Code = "corrupt_file",
                Suggestion = "Verify the file is a valid .docx/.xlsx/.pptx (e.g. unzip -t)."
            };
        }
    }

    /// <summary>
    /// CONSISTENCY(dos-hardening): inspect the zip container's entry count and
    /// total/ratio of uncompressed bytes and reject obvious decompression
    /// bombs. Uses the central <see cref="ZipFile.OpenRead"/> directory only
    /// (no entry is actually inflated), so this is cheap. A file that is not a
    /// valid zip is left untouched — the normal open path produces the existing
    /// corrupt_file error for it.
    /// </summary>
    private static void GuardDecompressionBomb(string filePath)
    {
        ZipArchive archive;
        try
        {
            archive = ZipFile.OpenRead(filePath);
        }
        catch (InvalidDataException)
        {
            // Not a valid zip container — let OpenHandler surface corrupt_file.
            return;
        }

        using (archive)
        {
            if (archive.Entries.Count > DocumentLimits.MaxZipEntries)
                throw new CliException(
                    $"Cannot open {Path.GetFileName(filePath)}: package has {archive.Entries.Count} entries " +
                    $"(limit {DocumentLimits.MaxZipEntries}); rejected as a potential decompression bomb.")
                {
                    Code = "decompression_bomb",
                    Suggestion = "Verify the file is a genuine .docx/.xlsx/.pptx and not a crafted archive."
                };

            long totalUncompressed = 0;
            long totalCompressed = 0;
            foreach (var entry in archive.Entries)
            {
                totalUncompressed += entry.Length;
                totalCompressed += entry.CompressedLength;

                if (totalUncompressed > DocumentLimits.MaxUncompressedBytes)
                    throw new CliException(
                        $"Cannot open {Path.GetFileName(filePath)}: uncompressed size exceeds " +
                        $"{DocumentLimits.MaxUncompressedBytes / (1024 * 1024 * 1024)} GiB; " +
                        $"rejected as a potential decompression bomb.")
                    {
                        Code = "decompression_bomb",
                        Suggestion = "Verify the file is a genuine .docx/.xlsx/.pptx and not a crafted archive."
                    };
            }

            // Ratio check only once there is enough data to be meaningful (a few
            // KB of highly-compressible XML legitimately exceeds the ratio).
            if (totalCompressed > 64 * 1024 &&
                totalUncompressed / Math.Max(1, totalCompressed) > DocumentLimits.MaxCompressionRatio)
                throw new CliException(
                    $"Cannot open {Path.GetFileName(filePath)}: compression ratio " +
                    $"{totalUncompressed / Math.Max(1, totalCompressed)}× exceeds {DocumentLimits.MaxCompressionRatio}×; " +
                    $"rejected as a potential decompression bomb.")
                {
                    Code = "decompression_bomb",
                    Suggestion = "Verify the file is a genuine .docx/.xlsx/.pptx and not a crafted archive."
                };
        }
    }

    private static IDocumentHandler OpenHandler(string filePath, string ext, bool editable)
    {
        return ext switch
        {
            ".docx" => new WordHandler(filePath, editable),
            ".xlsx" => new ExcelHandler(filePath, editable),
            ".pptx" => new PowerPointHandler(filePath, editable),
            _      => TryOpenViaPlugin(filePath, ext, editable)
                   ?? throw UnsupportedTypeException(ext)
        };
    }

    /// <summary>
    /// Look for an installed plugin that handles <paramref name="ext"/> and, if
    /// found, return a handler that delegates to it. Returns null when no
    /// plugin is installed — callers fall back to the unsupported-type error.
    ///
    /// dump-reader: per plugins/plugin-protocol.md §2.1, the plugin emits a batch
    /// of officecli commands describing the foreign source; main replays them
    /// into a fresh native file whose extension comes from the plugin's
    /// manifest <c>target</c> (docx/xlsx/pptx). The result is cached as a
    /// sibling file <c>&lt;source-stem&gt;.&lt;target&gt;</c> next to the
    /// source so subsequent invocations skip the plugin entirely (regenerated
    /// when the source mtime is newer than the sibling's, or when the sibling
    /// has been deleted). All edits target the sibling file, not the original
    /// source.
    ///
    /// format-handler: not yet wired; resolved plugins produce a clear
    /// "found but not yet wired" exception until the proxy lands.
    /// </summary>
    private static IDocumentHandler? TryOpenViaPlugin(string filePath, string ext, bool editable)
    {
        var dumpReader = PluginRegistry.FindFor(PluginKind.DumpReader, ext);
        if (dumpReader is not null)
        {
            var targetExt = dumpReader.Manifest.ResolveTargetExtension();
            var sibling = Path.ChangeExtension(filePath, targetExt);
            var needRegen = !File.Exists(sibling)
                || File.GetLastWriteTimeUtc(filePath) > File.GetLastWriteTimeUtc(sibling);

            if (needRegen)
            {
                var converted = DumpReaderInvoker.Run(filePath, ext);

                // Some plugins (e.g. Word interop on .doc) inherently write a
                // converted native file in the source directory as a side
                // effect of their conversion path. If the sibling now exists
                // and is current, prefer it over the batch-replayed copy:
                // it's the plugin's direct conversion, higher fidelity than
                // going through batch round-trip serialization.
                var siblingFresh = File.Exists(sibling)
                    && File.GetLastWriteTimeUtc(sibling) >= File.GetLastWriteTimeUtc(filePath);

                if (siblingFresh)
                {
                    try { File.Delete(converted.ConvertedPath); } catch { /* tmp will age out */ }
                }
                else
                {
                    try
                    {
                        var bytes = File.ReadAllBytes(converted.ConvertedPath);
                        File.WriteAllBytes(sibling, bytes);
                        try { File.Delete(converted.ConvertedPath); } catch { /* tmp will age out */ }
                    }
                    catch (Exception ex)
                    {
                        Console.Error.WriteLine(
                            $"[note] could not write sibling {Path.GetFileName(sibling)} ({ex.Message}); falling back to temp file (will reconvert next run)");
                        return OpenHandlerWithRetry(converted.ConvertedPath, targetExt, editable);
                    }
                }
                Console.Error.WriteLine(
                    $"[note] generated {Path.GetFileName(sibling)} from {Path.GetFileName(filePath)}; reusing on future runs (delete or rename it to force reconversion)");
            }

            // The sibling file may be transiently locked right after a fresh
            // plugin run (Word/Excel COM server lingering, Defender scan,
            // OneDrive sync). Retry briefly before surfacing the lock to the
            // user.
            return OpenHandlerWithRetry(sibling, targetExt, editable);
        }

        var formatHandler = PluginRegistry.FindFor(PluginKind.FormatHandler, ext);
        if (formatHandler is not null)
        {
            var session = new FormatHandlerSession(filePath, formatHandler);
            try
            {
                session.Start(editable);
                return new FormatHandlerProxy(session);
            }
            catch
            {
                session.Dispose();
                throw;
            }
        }

        return null;
    }

    private static IDocumentHandler OpenHandlerWithRetry(string path, string ext, bool editable)
    {
        Exception? last = null;
        for (int attempt = 0; attempt < 8; attempt++)
        {
            try { return OpenHandler(path, ext, editable); }
            catch (IOException ex) { last = ex; Thread.Sleep(150 * (attempt + 1)); }
        }
        throw last!;
    }

    private static CliException UnsupportedTypeException(string ext) =>
        new CliException(
            $"Unsupported file type: {ext}. Supported: .docx, .xlsx, .pptx. " +
            $"Other formats may be opened via plugins — run `officecli plugins list` to see installed plugins, " +
            $"or see plugins/plugin-protocol.md for installation paths.")
        {
            Code = "unsupported_type",
            ValidValues = [".docx", ".xlsx", ".pptx"]
        };

    private static bool IsEncodingException(Exception ex)
    {
        // The exception may be thrown directly or wrapped inside another exception
        for (var e = ex; e != null; e = e.InnerException)
        {
            if (e.Message.Contains("Encoding format is not supported", StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    private static bool IsDanglingPartException(Exception ex)
    {
        for (var e = ex; e != null; e = e.InnerException)
        {
            if (e.Message.Contains("doesn't exist in the package", StringComparison.OrdinalIgnoreCase)
                || e.Message.Contains("Specified part does not exist", StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    private static readonly System.Xml.Linq.XNamespace RelsNs =
        "http://schemas.openxmlformats.org/package/2006/relationships";

    /// <summary>
    /// Base directory a .rels file's relative targets resolve against:
    /// "x/_rels/y.xml.rels" -> "x"; the root "_rels/.rels" -> "".
    /// </summary>
    private static string RelsBaseDir(string relsEntryName)
    {
        var relsDir = (Path.GetDirectoryName(relsEntryName) ?? "").Replace('\\', '/');
        return relsDir.EndsWith("_rels", StringComparison.OrdinalIgnoreCase)
            ? relsDir.Substring(0, relsDir.Length - "_rels".Length).TrimEnd('/')
            : relsDir;
    }

    /// <summary>
    /// Resolve a relationship Target (relative or root-absolute) into a
    /// normalized package-internal part name, or null when the relationship is
    /// External or has no usable Target.
    /// </summary>
    private static string? ResolveInternalRelTarget(System.Xml.Linq.XElement rel, string baseDir)
    {
        if (string.Equals((string?)rel.Attribute("TargetMode"), "External", StringComparison.OrdinalIgnoreCase))
            return null;
        var target = (string?)rel.Attribute("Target");
        if (string.IsNullOrEmpty(target)) return null;
        var resolved = target.StartsWith("/")
            ? target.TrimStart('/')
            : (baseDir.Length > 0 ? baseDir + "/" + target : target);
        var segs = new List<string>();
        foreach (var seg in resolved.Split('/'))
        {
            if (seg == "..") { if (segs.Count > 0) segs.RemoveAt(segs.Count - 1); }
            else if (seg != "." && seg.Length > 0) segs.Add(seg);
        }
        return string.Join("/", segs);
    }

    /// <summary>
    /// Read-only scan: does the package contain any internal relationship whose
    /// target part is absent from the package? Used to gate the (mutating)
    /// in-place repair so clean files are never rewritten. Returns false on any
    /// read/parse error — the normal open path then surfaces the real problem.
    /// </summary>
    private static bool HasDanglingInternalRels(string filePath)
    {
        try
        {
            using var zip = ZipFile.OpenRead(filePath);
            var names = new HashSet<string>(zip.Entries.Select(e => e.FullName), StringComparer.OrdinalIgnoreCase);
            foreach (var entry in zip.Entries)
            {
                if (!entry.FullName.EndsWith(".rels", StringComparison.OrdinalIgnoreCase)) continue;
                string content;
                using (var reader = new StreamReader(entry.Open(), Encoding.UTF8))
                    content = reader.ReadToEnd();
                System.Xml.Linq.XDocument xdoc;
                try { xdoc = System.Xml.Linq.XDocument.Parse(content); }
                catch { continue; }
                if (xdoc.Root is null) continue;
                var baseDir = RelsBaseDir(entry.FullName);
                foreach (var rel in xdoc.Root.Elements(RelsNs + "Relationship"))
                {
                    var resolved = ResolveInternalRelTarget(rel, baseDir);
                    if (resolved != null && !names.Contains(resolved))
                        return true;
                }
            }
        }
        catch { return false; }
        return false;
    }

    /// <summary>
    /// Remove internal (non-External) relationships whose target part is
    /// missing from the package. Word/PowerPoint tolerate such dangling rels;
    /// the SDK refuses to open (or crashes mid-traversal on) the file. Only
    /// .rels entries are touched, and only the dangling Relationship nodes are
    /// dropped.
    /// </summary>
    private static void StripDanglingPackageRels(string filePath)
    {
        using var zip = ZipFile.Open(filePath, ZipArchiveMode.Update);
        var names = new HashSet<string>(zip.Entries.Select(e => e.FullName), StringComparer.OrdinalIgnoreCase);
        foreach (var entry in zip.Entries.ToList())
        {
            if (!entry.FullName.EndsWith(".rels", StringComparison.OrdinalIgnoreCase)) continue;
            string content;
            using (var reader = new StreamReader(entry.Open(), Encoding.UTF8))
                content = reader.ReadToEnd();

            System.Xml.Linq.XDocument xdoc;
            try { xdoc = System.Xml.Linq.XDocument.Parse(content); }
            catch { continue; }
            var baseDir = RelsBaseDir(entry.FullName);
            bool changed = false;
            foreach (var rel in xdoc.Root!.Elements(RelsNs + "Relationship").ToList())
            {
                var resolved = ResolveInternalRelTarget(rel, baseDir);
                if (resolved != null && !names.Contains(resolved))
                {
                    rel.Remove();
                    changed = true;
                }
            }
            if (!changed) continue;
            entry.Delete();
            var newEntry = zip.CreateEntry(entry.FullName, CompressionLevel.Optimal);
            using var writer = new StreamWriter(newEntry.Open(), new UTF8Encoding(false));
            writer.Write(xdoc.Declaration != null
                ? xdoc.Declaration + xdoc.ToString(System.Xml.Linq.SaveOptions.DisableFormatting)
                : xdoc.ToString(System.Xml.Linq.SaveOptions.DisableFormatting));
        }
    }

    /// <summary>
    /// Rewrite XML declarations inside an OOXML package that use unsupported encodings
    /// (e.g. encoding="ascii") to encoding="UTF-8".
    /// </summary>
    private static void FixXmlEncoding(string filePath)
    {
        using var zip = ZipFile.Open(filePath, ZipArchiveMode.Update);
        foreach (var entry in zip.Entries.ToList())
        {
            if (!entry.FullName.EndsWith(".xml", StringComparison.OrdinalIgnoreCase) &&
                !entry.FullName.EndsWith(".rels", StringComparison.OrdinalIgnoreCase))
                continue;

            string content;
            using (var reader = new StreamReader(entry.Open(), Encoding.UTF8))
                content = reader.ReadToEnd();

            // Match <?xml ... encoding="xxx" ?> and replace non-standard encodings
            var fixed_ = Regex.Replace(content,
                @"(<\?xml\b[^?]*?\bencoding\s*=\s*"")(?!UTF-8|utf-8|UTF-16|utf-16)[^""]*("")",
                "${1}UTF-8${2}");

            if (fixed_ == content) continue;

            // Rewrite the entry
            entry.Delete();
            var newEntry = zip.CreateEntry(entry.FullName, CompressionLevel.Optimal);
            using var writer = new StreamWriter(newEntry.Open(), new UTF8Encoding(false));
            writer.Write(fixed_);
        }
    }
}
