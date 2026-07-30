#!/usr/bin/env python3
"""
Beautiful Charts Showcase — generates charts.xlsx with 8 chart types: combo
(columns + secondary-axis line), 3D bar, scatter+trendline, exploded 3D pie,
bubble, stock OHLC candlestick (red up / green down), filled radar, and a
multi-ring (nested) doughnut. 4 data sheets feed them: monthly sales (Sheet1),
spend/sales analysis (Analysis), OHLC stock data (StockData), and capability
assessment (Assessment).

SDK twin of charts.sh (officecli CLI). Both produce an equivalent charts.xlsx.
This one drives the **officecli Python SDK** (`pip install officecli-sdk`): one
resident is started and every command is shipped over the named pipe. Cell data
goes out per-sheet in a single `doc.batch(...)` round-trip; seven of the charts
are then a single high-level `add --type chart` send each (chartType + dataRange
or inline data + styling props). The bubble (Chart 5) stays on raw-set — the
high-level command can't map a dataRange to a single x/y/size series — so it uses
`add-part` (relId captured into the anchor) + two `raw-set` calls. Each item is
the same `{"command",...,"props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts.py
"""

import os
import re
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts.xlsx")

CHART_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"


# ---------------------------------------------------------------- batch helpers
def cell(path, value, **props):
    """One `set <cell>` item in batch-shape."""
    return {"command": "set", "path": path, "props": {"value": str(value), **props}}


def add_sheet(name):
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


HDR = {"font.bold": "true", "alignment.horizontal": "center"}


def header(path, value, fill, font_color, size=None):
    p = {"value": value, "fill": fill, "font.color": font_color, **HDR}
    if size is not None:
        p["font.size"] = str(size)
    return {"command": "set", "path": path, "props": p}


# ---------------------------------------------------------------- chart helpers
def add_chart_part(doc, parent):
    """`add-part --type chart`; return the created relationship id.
    as_json=False yields the plain 'Created chart part: relId=... path=...' line
    (same string the .sh greps), from which we pull relId."""
    msg = doc.send({"command": "add-part", "parent": parent, "type": "chart"},
                   as_json=False)
    m = re.search(r"relId=(\S+)", msg if isinstance(msg, str) else str(msg))
    if not m:
        raise RuntimeError(f"add-part did not return a relId: {msg!r}")
    return m.group(1)


def set_chart_xml(doc, chart_path, xml):
    """`raw-set` the whole chartSpace (replace /c:chartSpace). raw-set's target
    part is the `part` field (the CLI positional arg), not `path`."""
    doc.send({"command": "raw-set", "part": chart_path,
              "xpath": "/c:chartSpace", "action": "replace", "xml": xml})


def add_anchor(doc, sheet, from_col, from_row, to_col, to_row, cnvpr_id, name, rel_id):
    """`raw-set` append a twoCellAnchor graphicFrame referencing the chart."""
    xml = (
        '<xdr:twoCellAnchor>'
        f'<xdr:from><xdr:col>{from_col}</xdr:col><xdr:colOff>0</xdr:colOff>'
        f'<xdr:row>{from_row}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
        f'<xdr:to><xdr:col>{to_col}</xdr:col><xdr:colOff>0</xdr:colOff>'
        f'<xdr:row>{to_row}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
        '<xdr:graphicFrame macro="">'
        f'<xdr:nvGraphicFramePr><xdr:cNvPr id="{cnvpr_id}" name="{name}" />'
        '<xdr:cNvGraphicFramePr /></xdr:nvGraphicFramePr>'
        '<xdr:xfrm><a:off x="0" y="0" /><a:ext cx="0" cy="0" /></xdr:xfrm>'
        f'<a:graphic><a:graphicData uri="{CHART_URI}">'
        f'<c:chart r:id="{rel_id}" /></a:graphicData></a:graphic>'
        '</xdr:graphicFrame><xdr:clientData />'
        '</xdr:twoCellAnchor>'
    )
    doc.send({"command": "raw-set", "part": f"/{sheet}/drawing",
              "xpath": "//xdr:wsDr", "action": "append", "xml": xml})


# ---------------------------------------------------------------- chart XML
CHART5_XML = '''
<c:chartSpace>
  <c:chart>
    <c:title>
      <c:tx><c:rich><a:bodyPr /><a:lstStyle />
        <a:p><a:pPr><a:defRPr sz="1600" b="1"><a:solidFill><a:srgbClr val="7030A0" /></a:solidFill></a:defRPr></a:pPr>
        <a:r><a:rPr lang="en-US" sz="1600" b="1" /><a:t>Spend-Revenue-Market Share Bubble</a:t></a:r></a:p>
      </c:rich></c:tx>
      <c:overlay val="0" />
    </c:title>
    <c:plotArea>
      <c:layout />
      <c:bubbleChart>
        <c:varyColors val="0" />
        <c:ser>
          <c:idx val="0" /><c:order val="0" />
          <c:tx><c:strRef><c:f>Analysis!$D$1</c:f></c:strRef></c:tx>
          <c:spPr>
            <a:solidFill><a:srgbClr val="7030A0"><a:alpha val="60000" /></a:srgbClr></a:solidFill>
            <a:ln w="19050"><a:solidFill><a:srgbClr val="7030A0" /></a:solidFill></a:ln>
            <a:effectLst><a:outerShdw blurRad="40000" dist="23000" dir="5400000"><a:srgbClr val="000000"><a:alpha val="25000" /></a:srgbClr></a:outerShdw></a:effectLst>
          </c:spPr>
          <c:xVal><c:numRef><c:f>Analysis!$A$2:$A$16</c:f></c:numRef></c:xVal>
          <c:yVal><c:numRef><c:f>Analysis!$B$2:$B$16</c:f></c:numRef></c:yVal>
          <c:bubbleSize><c:numRef><c:f>Analysis!$D$2:$D$16</c:f></c:numRef></c:bubbleSize>
          <c:bubble3D val="1" />
        </c:ser>
        <c:axId val="300" /><c:axId val="400" />
      </c:bubbleChart>
      <c:valAx>
        <c:axId val="300" /><c:scaling><c:orientation val="minMax" /></c:scaling><c:delete val="0" /><c:axPos val="b" />
        <c:title><c:tx><c:rich><a:bodyPr /><a:lstStyle /><a:p><a:pPr><a:defRPr sz="1000" /></a:pPr><a:r><a:rPr lang="en-US" sz="1000" /><a:t>Ad Spend (10K)</a:t></a:r></a:p></c:rich></c:tx></c:title>
        <c:numFmt formatCode="#,##0" sourceLinked="0" /><c:crossAx val="400" />
      </c:valAx>
      <c:valAx>
        <c:axId val="400" /><c:scaling><c:orientation val="minMax" /></c:scaling><c:delete val="0" /><c:axPos val="l" />
        <c:title><c:tx><c:rich><a:bodyPr rot="-5400000" /><a:lstStyle /><a:p><a:pPr><a:defRPr sz="1000" /></a:pPr><a:r><a:rPr lang="en-US" sz="1000" /><a:t>Sales (10K)</a:t></a:r></a:p></c:rich></c:tx></c:title>
        <c:numFmt formatCode="#,##0" sourceLinked="0" /><c:crossAx val="300" />
      </c:valAx>
    </c:plotArea>
    <c:legend><c:legendPos val="b" /><c:overlay val="0" /></c:legend>
    <c:plotVisOnly val="1" />
  </c:chart>
</c:chartSpace>'''


print("\n==========================================")
print(f"Generating beautiful charts document: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet1: Monthly sales data
    # ======================================================================
    print("  -> Populating Sheet1: Monthly sales data")
    s1 = [
        header("/Sheet1/A1", "Month", "1F4E79", "FFFFFF", 11),
        header("/Sheet1/B1", "East Sales", "2E75B6", "FFFFFF", 11),
        header("/Sheet1/C1", "South Sales", "9DC3E6", "1F4E79", 11),
        header("/Sheet1/D1", "North Sales", "BDD7EE", "1F4E79", 11),
        header("/Sheet1/E1", "Total", "C55A11", "FFFFFF", 11),
        header("/Sheet1/F1", "YoY Growth %", "548235", "FFFFFF", 11),
    ]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    east = [120, 135, 148, 162, 155, 178, 195, 210, 188, 172, 165, 198]
    south = [95, 108, 115, 128, 142, 155, 168, 175, 160, 148, 135, 158]
    north = [88, 92, 105, 118, 125, 138, 145, 152, 140, 130, 122, 142]
    total = [303, 335, 368, 408, 422, 471, 508, 537, 488, 450, 422, 498]
    growth = [5.2, 8.1, 12.3, 15.6, 10.2, 18.5, 22.1, 25.3, 16.8, 11.2, 7.5, 19.8]
    for i in range(12):
        r = i + 2
        s1.append(cell(f"/Sheet1/A{r}", months[i], **{"alignment.horizontal": "center"}))
        s1.append(cell(f"/Sheet1/B{r}", east[i], numFmt="#,##0", **{"alignment.horizontal": "center"}))
        s1.append(cell(f"/Sheet1/C{r}", south[i], numFmt="#,##0", **{"alignment.horizontal": "center"}))
        s1.append(cell(f"/Sheet1/D{r}", north[i], numFmt="#,##0", **{"alignment.horizontal": "center"}))
        s1.append(cell(f"/Sheet1/E{r}", total[i], numFmt="#,##0",
                       **{"font.bold": "true", "alignment.horizontal": "center"}))
        s1.append(cell(f"/Sheet1/F{r}", growth[i], numFmt='0.0"%"', **{"alignment.horizontal": "center"}))
    doc.batch(s1)
    print("  Done: Sheet1 data")

    # ======================================================================
    # Sheet2: Analysis (scatter/bubble) data
    # ======================================================================
    print("  -> Populating Sheet2: Analysis data")
    s2 = [add_sheet("Analysis")]
    for col, title in zip("ABCD", ["Ad Spend (10K)", "Sales (10K)", "Margin %", "Market Share %"]):
        s2.append(header(f"/Analysis/{col}1", title, "7030A0", "FFFFFF"))
    ad_spend = [10, 15, 22, 28, 35, 42, 50, 58, 65, 72, 80, 88, 95, 105, 115]
    sales_rev = [45, 68, 95, 120, 155, 180, 220, 260, 290, 335, 370, 410, 445, 500, 550]
    profit = [8.5, 10.2, 12.1, 14.5, 16.8, 15.2, 18.3, 20.1, 19.5, 22.3, 21.8, 24.5, 23.1, 26.8, 28.2]
    mkt_share = [2.1, 3.2, 4.5, 5.8, 7.2, 8.5, 10.1, 11.8, 12.5, 14.2, 15.8, 17.5, 18.2, 20.5, 22.1]
    for i in range(15):
        r = i + 2
        for col, vals in zip("ABCD", [ad_spend, sales_rev, profit, mkt_share]):
            s2.append(cell(f"/Analysis/{col}{r}", vals[i], **{"alignment.horizontal": "center"}))
    doc.batch(s2)
    print("  Done: Sheet2 data")

    # ======================================================================
    # Sheet3: StockData (red up / green down coloring)
    # ======================================================================
    print("  -> Populating Sheet3: Stock data")
    s3 = [add_sheet("StockData")]
    for col, title in zip("ABCDEF", ["Date", "Open", "High", "Low", "Close", "Volume (10K)"]):
        s3.append(header(f"/StockData/{col}1", title, "C00000", "FFFFFF"))
    dates = ["3/1", "3/2", "3/3", "3/4", "3/5", "3/6", "3/7", "3/8", "3/9", "3/10",
             "3/11", "3/12", "3/13", "3/14", "3/15", "3/16", "3/17", "3/18", "3/19", "3/20"]
    s_open = [52.3, 53.1, 52.8, 54.2, 55.1, 54.5, 56.2, 57.8, 58.5, 57.2,
              56.8, 58.3, 59.5, 60.2, 59.8, 61.5, 62.3, 61.8, 63.5, 64.2]
    s_high = [53.8, 54.2, 54.5, 55.8, 56.3, 56.8, 58.1, 59.2, 59.8, 58.5,
              58.2, 59.8, 61.2, 61.5, 61.8, 63.2, 63.8, 63.5, 65.2, 65.8]
    s_low = [51.5, 52.2, 51.8, 53.5, 54.2, 53.8, 55.5, 56.8, 57.2, 56.1,
             55.8, 57.5, 58.8, 59.2, 58.5, 60.8, 61.2, 60.5, 62.8, 63.5]
    s_close = [53.1, 52.8, 54.2, 55.1, 54.5, 56.2, 57.8, 58.5, 57.2, 56.8,
               58.3, 59.5, 60.2, 59.8, 61.5, 62.3, 61.8, 63.5, 64.2, 65.1]
    volume = [285, 312, 268, 345, 298, 378, 425, 468, 395, 310,
              352, 415, 485, 442, 368, 512, 548, 478, 562, 598]
    for i in range(20):
        r = i + 2
        if s_close[i] > s_open[i]:
            color, bg = "FF0000", "FFF2F2"   # Up: red
        elif s_close[i] < s_open[i]:
            color, bg = "008000", "F2FFF2"   # Down: green
        else:
            color, bg = "666666", "F5F5F5"   # Flat: gray
        common = {"alignment.horizontal": "center", "font.color": color, "fill": bg}
        s3.append(cell(f"/StockData/A{r}", dates[i], **common))
        s3.append(cell(f"/StockData/B{r}", s_open[i], numFmt="0.00", **common))
        s3.append(cell(f"/StockData/C{r}", s_high[i], numFmt="0.00", **common))
        s3.append(cell(f"/StockData/D{r}", s_low[i], numFmt="0.00", **common))
        s3.append(cell(f"/StockData/E{r}", s_close[i], numFmt="0.00", **common))
        s3.append(cell(f"/StockData/F{r}", volume[i], numFmt="#,##0", **common))
    doc.batch(s3)
    print("  Done: Sheet3 stock data (with red/green coloring)")

    # ======================================================================
    # Sheet4: Assessment (radar) data
    # ======================================================================
    print("  -> Populating Sheet4: Capability assessment")
    s4 = [add_sheet("Assessment")]
    s4.append(header("/Assessment/A1", "Dimension", "002060", "FFFFFF"))
    s4.append(header("/Assessment/B1", "Product A", "0070C0", "FFFFFF"))
    s4.append(header("/Assessment/C1", "Product B", "00B050", "FFFFFF"))
    s4.append(header("/Assessment/D1", "Product C", "FFC000", "000000"))
    dims = ["Performance", "Stability", "Usability", "Security",
            "Scalability", "Value", "Ecosystem", "Docs"]
    pa = [92, 88, 75, 95, 82, 70, 85, 78]
    pb = [78, 92, 88, 80, 90, 85, 72, 82]
    pc = [85, 76, 92, 72, 78, 92, 88, 70]
    for i in range(8):
        r = i + 2
        for col, vals in zip("ABCD", [dims, pa, pb, pc]):
            s4.append(cell(f"/Assessment/{col}{r}", vals[i], **{"alignment.horizontal": "center"}))
    doc.batch(s4)
    print("  Done: Sheet4 data")

    # ======================================================================
    # Charts — HIGH-LEVEL API. Each chart is a single `add --type chart` send
    # (chartType + a cell dataRange, or inline data for the pie/doughnut whose
    # source cells aren't contiguous) with styling props. Exception: Chart 5
    # (bubble) stays on raw-set — the high-level command can't map a dataRange
    # to a single x/y/size series (multi-point bubble). Positions use
    # x/y/width/height in cell units.
    # ======================================================================
    def add_chart(parent, **props):
        doc.send({"command": "add", "parent": parent, "type": "chart", "props": props})

    print("  -> Chart 1: Combo (columns + secondary-axis line)")
    add_chart("/Sheet1", chartType="combo",
              title="Monthly Sales and YoY Growth Trend",
              dataRange="Sheet1!A1:F13",
              combotypes="column,column,column,column,line",
              secondaryaxis="5", colors="2E75B6,9DC3E6,BDD7EE,C55A11,FF0000",
              legend="b", axisTitle="Sales (10K)", x="7", y="0", width="11", height="18")

    print("  -> Chart 2: 3D bar chart")
    add_chart("/Sheet1", chartType="column3d", title="3D Regional Sales Comparison",
              dataRange="Sheet1!A1:D13", view3d="15,20,30",
              colors="4472C4,ED7D31,70AD47", legend="b",
              x="7", y="19", width="11", height="18")

    print("  -> Chart 3: Scatter plot + trendline")
    add_chart("/Analysis", chartType="scatter", title="Ad Spend vs Sales Correlation",
              dataRange="Analysis!A1:B16", trendline="linear", colors="7030A0",
              catTitle="Ad Spend (10K)", axisTitle="Sales (10K)", legend="b",
              x="5", y="0", width="11", height="18")

    print("  -> Chart 4: 3D pie chart (exploded)")
    add_chart("/Sheet1", chartType="pie3d", title="July Regional Sales Share (3D)",
              categories="East Sales,South Sales,North Sales", series1="Jul:195,168,145",
              explosion="10", view3d="30,70,30", dataLabels="percent",
              colors="1F4E79,C55A11,548235", legend="b",
              x="19", y="0", width="9", height="18")

    # Chart 5 (bubble) — raw-set (see note above): high-level can't express a
    # single multi-point x/y/size bubble series from a dataRange.
    print("  -> Chart 5: Bubble chart (raw-set)")
    rel = add_chart_part(doc, "/Analysis")
    set_chart_xml(doc, "/Analysis/chart[2]", CHART5_XML)
    add_anchor(doc, "Analysis", 5, 19, 16, 37, 3, "Chart 5", rel)

    print("  -> Chart 6: Stock OHLC chart")
    add_chart("/StockData", chartType="stock", title="Stock Candlestick Chart (OHLC)",
              dataRange="StockData!A1:E21", hilowlines="true",
              updownbars="100:FF0000:00B050", legend="b",
              x="7", y="0", width="13", height="22")

    print("  -> Chart 7: Filled radar chart")
    add_chart("/Assessment", chartType="radar", radarStyle="filled",
              title="Product Capability Radar Comparison", dataRange="Assessment!A1:D9",
              colors="4472C4,00B050,FFC000", legend="b",
              x="5", y="0", width="11", height="20")

    print("  -> Chart 8: Multi-ring doughnut chart")
    add_chart("/Sheet1", chartType="doughnut", title="Aug vs Dec Regional Sales Multi-Ring",
              categories="East,South,North", series1="Aug:210,175,152",
              series2="Dec:198,158,142", dataLabels="percent",
              colors="1F4E79,C55A11,548235", legend="b",
              x="19", y="19", width="9", height="18")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nGenerated: {FILE}")
