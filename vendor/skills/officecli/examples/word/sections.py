#!/usr/bin/env python3
"""
Sections Showcase — generates sections.docx exercising the docx `section`
property surface (schemas/help/docx/section.json): the per-section page layout
that has no per-paragraph equivalent.

A section is a run of content sharing one page layout: page size & orientation,
margins, columns, header/footer refs, line numbering, footnote/endnote behaviour
and vertical alignment. A .docx always has ONE trailing "final" section (the
body-level sectPr addressed at path "/"). Every `add / --type section` inserts a
section BREAK: it closes off the content added so far into a new /section[N]
carrying its own SectionProperties, and the still-open trailing section shifts
down to hold whatever comes next.

  Pattern:  add paragraphs  ->  add section (break)  ->  repeat.
  The section you just added owns the paragraphs ABOVE it. Sections are
  addressed /section[N] (query/get/set/remove); the final trailing section is
  addressed "/" (Set rejects a break `type` there — it has no break).

This twin builds three sections with different layouts:
  1. two-column portrait, page-bottom footnotes (lowerRoman, restart each page)
  2. single-column landscape, vertically centered, continuous line numbering
  3. two-column continuous with endnotes collected at document end

Like examples/word/document-formatting.py, this drives the officecli Python SDK
(`pip install officecli-sdk`): one resident, writes shipped over the pipe.

Usage:
  python3 sections.py
"""

import os
import sys
import subprocess

try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sections.docx")


def para(text, **props):
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def section(**props):
    """A section-break `add` at path '/'. Owns the paragraphs added above it."""
    return {"command": "add", "parent": "/", "type": "section", "props": props}


def footnote(para_path, text):
    return {"command": "add", "parent": para_path, "type": "footnote",
            "props": {"text": text}}


def endnote(para_path, text):
    return {"command": "add", "parent": para_path, "type": "endnote",
            "props": {"text": text}}


print("\n==========================================")
print(f"Generating sections showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ----------------------------------------------------------------------
    # SECTION 1 — two-column newsletter body with page-bottom footnotes.
    # Add the flowing content first, then the section break that owns it.
    # ----------------------------------------------------------------------
    # Paragraph indices: p[1] heading, p[2]..p[9] body (enough copy that
    # column 1 fills top-to-bottom and text wraps into column 2).
    print("\n--- Section 1: two columns + footnotes ---")
    doc.batch([
        para("1. Two-Column Layout with Footnotes", style="Heading1"),
        para("Multi-column layout flows text down the first column, then wraps "
             "to the top of the next. This section uses two balanced columns "
             "with a one-centimetre gutter between them, and enough running "
             "text follows that the wrap from the foot of the left column to "
             "the head of the right column is plainly visible on the page."),
        para("Newspapers and newsletters have used the two-column measure for "
             "centuries because a narrower column is easier for the eye to "
             "track: the reader's gaze travels a shorter distance before "
             "returning to the start of the next line, so long passages of body "
             "text feel less tiring than the same words set across the full "
             "page width."),
        para("Footnotes in this section are numbered with lower-case Roman "
             "numerals and the counter restarts on every page, mirroring a "
             "printed periodical. The reference marker sits inline in the "
             "running text, while the note itself is anchored at the bottom of "
             "the page column, beneath a short separator rule."),
        para("Word measures the column width from the page width, minus the "
             "left and right margins, minus the inter-column spacing, divided "
             "across the requested column count. Because equal-width columns "
             "are enabled here, both columns share exactly the same measure, "
             "and the gutter between them is held at the value we set."),
        para("When a column is filled to the bottom margin, the text engine "
             "breaks the flow and resumes typesetting at the top of the next "
             "column on the same page. Only after the last column on a page is "
             "full does the flow move to a new page, so a two-column section "
             "packs roughly twice as many lines onto each sheet."),
        para("This is why the amount of body copy matters for a demonstration: "
             "with only two or three short paragraphs the first column never "
             "fills, and the layout reads on the page as if it were a single "
             "column. Several paragraphs of steady prose, like these, are "
             "needed before the column break actually occurs."),
        para("Balancing is the final refinement. On the last page of a "
             "multi-column section Word tries to even out the columns so they "
             "end at roughly the same height, rather than leaving one long "
             "column beside a short stub — the tidy, squared-off block of text "
             "readers expect from a professionally set page."),
        para("With that, the first section has enough material to spill from "
             "column one into column two and, depending on font and page size, "
             "perhaps onto a second page — exactly the wrapping behaviour a "
             "two-column layout is meant to show."),
    ])
    # Footnotes attach to a body paragraph; they render per footnotePr.pos.
    doc.batch([
        footnote("/body/p[4]", "Column width = (page width - margins - column "
                               "spacing) / column count."),
        footnote("/body/p[8]", "Balanced columns keep the two measures visually "
                               "equal on the final page."),
    ])
    # Section 1 settings: 2 columns, footnotes, A4 portrait, distinct title page.
    doc.batch([section(**{
        "type": "nextPage",
        "pageWidth": "21cm", "pageHeight": "29.7cm", "orientation": "portrait",
        "marginTop": "2.54cm", "marginBottom": "2.54cm",
        "marginLeft": "2.54cm", "marginRight": "2.54cm",
        "marginHeader": "1.25cm", "marginFooter": "1.25cm",
        "columns": "2", "columnSpace": "1cm",
        "titlePage": "true",
        "footnotePr.numFmt": "lowerRoman",
        "footnotePr.numRestart": "eachPage",
        "footnotePr.numStart": "1",
        "footnotePr.pos": "pageBottom",
    })])

    # ----------------------------------------------------------------------
    # SECTION 2 — single-column landscape, vertically centered, line numbers.
    # ----------------------------------------------------------------------
    print("--- Section 2: landscape + vAlign + line numbering ---")
    doc.batch([
        para("2. Landscape, Single Column, Vertically Centered", style="Heading1"),
        para("This section switches to landscape orientation with a single "
             "column and asymmetric margins. The vertical alignment is set to "
             "center, so a short block of content floats in the middle of the "
             "page height instead of hugging the top margin."),
        para("Landscape sections are common for wide tables, timelines and "
             "figures. Because page setup is a per-section property, this page "
             "can be landscape while its neighbours stay portrait, all within "
             "one document."),
        para("Line numbering is enabled here in continuous mode, numbering every "
             "fifth line, with a gutter between the number column and the body "
             "text — the layout used for legal and manuscript review."),
        para("A single-column section does not wrap, so it needs no extra copy "
             "to demonstrate; the point here is the interaction of landscape "
             "geometry, centered vertical alignment, and the margin line numbers "
             "rather than any column flow."),
    ])
    # Section 2 settings: landscape (swapped W/H), 1 column, vAlign, line numbers.
    doc.batch([section(**{
        "type": "nextPage",
        "orientation": "landscape",
        "pageWidth": "29.7cm", "pageHeight": "21cm",
        "marginTop": "2cm", "marginBottom": "2cm",
        "marginLeft": "3cm", "marginRight": "1.5cm",
        "columns": "1",
        "vAlign": "center",
        "lineNumbers": "continuous",
        "lineNumberCountBy": "5",
        "lineNumberDistance": "288",
        "pageNumFmt": "decimal",
        "pageStart": "1",
    })])

    # ----------------------------------------------------------------------
    # SECTION 3 — continuous two-column with endnotes collected at doc end.
    # ----------------------------------------------------------------------
    # Paragraph indices: p[15] heading, p[16]..p[22] body (enough copy for the
    # two continuous columns to fill and wrap on the page).
    print("--- Section 3: continuous two columns + endnotes ---")
    doc.batch([
        para("3. Continuous Two-Column with Endnotes", style="Heading1"),
        para("A continuous section break changes the layout without starting a "
             "new page. This section returns to portrait, splits into two "
             "columns again, and collects its references as endnotes gathered at "
             "the end of the document rather than at the foot of each page."),
        para("Because the break is continuous rather than next-page, the "
             "two-column layout begins immediately below the heading on whatever "
             "page the previous section left off, instead of ejecting to a fresh "
             "sheet. This is the classic magazine construction: a full-width "
             "headline followed by columned body text on the same page."),
        para("Endnotes here use upper-case Roman numerals and restart per "
             "section. Unlike footnotes, endnote bodies are not printed at the "
             "foot of the page; they live in a separate store and are rendered "
             "together where endnotePr.pos points them — here, at the very end."),
        para("The choice between footnotes and endnotes is editorial. Footnotes "
             "keep the reference in the reader's eye on the same page, which "
             "suits explanatory asides, whereas endnotes keep the body text "
             "clean and gather citations in one place, which suits scholarly "
             "bibliographies and long reference lists."),
        para("As with the first section, the wrap only becomes visible once the "
             "first column fills to the bottom margin. These middle paragraphs "
             "exist to supply that volume of copy, so the reader can watch the "
             "text leave the foot of the left column and continue at the top of "
             "the right column without a page break intervening."),
        para("Continuous sections are also how a document mixes column counts on "
             "a single page: a full-width introduction, then a continuous break "
             "into two or three columns, then another continuous break back to "
             "full width for a closing note — all flowing down the same sheet."),
        para("This closing paragraph rounds out the section with enough text "
             "that the two continuous columns fill and balance, completing the "
             "demonstration of a continuous multi-column layout with "
             "document-end endnotes."),
    ])
    # Endnotes attach to a body paragraph, same as footnotes.
    doc.batch([
        endnote("/body/p[18]", "Endnotes are collected per endnotePr.pos; here "
                               "they gather at the document end."),
        endnote("/body/p[22]", "Upper-Roman numbering restarts each section "
                               "under endnotePr.numRestart=eachSect."),
    ])
    # Section 3 settings: continuous break, 2 columns, endnotes at docEnd.
    doc.batch([section(**{
        "type": "continuous",
        "orientation": "portrait",
        "pageWidth": "21cm", "pageHeight": "29.7cm",
        "columns": "2", "columnSpace": "0.8cm",
        "endnotePr.numFmt": "upperRoman",
        "endnotePr.numRestart": "eachSect",
        "endnotePr.numStart": "1",
        "endnotePr.pos": "docEnd",
    })])

    # ----------------------------------------------------------------------
    # FINAL trailing section — addressed "/" (no break type; it is the last
    # one). Set page setup so the tail of the document has a defined layout.
    # ----------------------------------------------------------------------
    print("--- Final trailing section (path '/') ---")
    doc.batch([{"command": "set", "path": "/", "props": {
        "orientation": "portrait",
        "pageWidth": "21cm", "pageHeight": "29.7cm",
        "marginTop": "2.54cm", "marginBottom": "2.54cm",
        "columns": "1", "vAlign": "top",
    }}])

    doc.send({"command": "save"})

    # ----------------------------------------------------------------------
    # Get round-trip: confirm the per-section layout keys read back. We `get`
    # each /section[N] in turn (the SDK `get` mirrors CLI `get /section[N]`;
    # the three break sections plus the trailing final section at "/").
    # ----------------------------------------------------------------------
    print("\n--- Round-trip readback (get each section) ---")
    keys = ["type", "orientation", "columns", "columnSpace", "vAlign",
            "footnotePr.numFmt", "endnotePr.numFmt", "lineNumbers"]
    for path in ["/section[1]", "/section[2]", "/section[3]", "/"]:
        node = doc.send({"command": "get", "path": path})
        fmt = node.get("data", {}).get("results", [{}])[0].get("format", {})
        shown = " ".join(f"{k}={fmt[k]}" for k in keys if k in fmt)
        print(f"  {path}  {shown}")

print("\n--- Validate (fresh process, from disk) ---")
r = subprocess.run(["officecli", "validate", FILE], capture_output=True, text=True)
print(" ", (r.stdout or r.stderr).strip().split("\n")[0])

print(f"\nCreated: {FILE}")
