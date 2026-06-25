' ============================================================
' Mumbai Local Delay Analytics — Excel VBA Data Refresh Macro
' ============================================================
' PURPOSE:
'   Pulls live data from the FastAPI backend (/api/export/excel)
'   and saves it as a fresh .xlsx in the same folder as this macro.
'   Demonstrates API→Excel automation as described in the JPMC JD:
'   "pulling data from various APIs / databases and presenting them
'    in consumable format" and "automation of various processes".
'
' HOW TO USE:
'   Option A — Full workbook download (recommended):
'     1. Open Excel, press Alt+F11 to open VBA editor.
'     2. Insert → Module → paste this file's contents.
'     3. Run RefreshWorkbook() to download a fresh .xlsx from the API.
'
'   Option B — Live JSON parse into current workbook:
'     Run RefreshRankingsSheet() to populate a "Rankings" sheet
'     directly from /api/rankings endpoint JSON.
'
' REQUIREMENTS:
'   - Excel 2016+ (Windows) with VBA enabled
'   - API running locally:  uvicorn api.main:app --reload
'     OR deployed URL set in API_BASE constant below
'
' SECURITY NOTE:
'   Microsoft XML (MSXML2.XMLHTTP) is used — no external libraries.
'   All data stays within your organisation's network.
' ============================================================

Option Explicit

' ── Configuration ────────────────────────────────────────────────────────────
' Change to your deployed URL when running in production:
'   e.g. "https://mumbai-local-delay.onrender.com"
Private Const API_BASE As String = "http://localhost:8000"

Private Const SHEET_RANKINGS As String = "Rankings"
Private Const SHEET_ANOMALIES As String = "Anomalies"
Private Const SHEET_TRENDS As String = "Line Trends"

' ── Colour constants (matches Python export + React UI) ───────────────────────
Private Const CLR_HDR      As Long = 1857367    ' #1C3557 navy
Private Const CLR_HDR_TXT  As Long = 16777215   ' #FFFFFF white
Private Const CLR_RED      As Long = 16764108   ' #FFCCCC
Private Const CLR_YELLOW   As Long = 16777164   ' #FFFFCC
Private Const CLR_GREEN    As Long = 14483163   ' #CCFFCC


' ============================================================
' PUBLIC: Download full .xlsx from /api/export/excel
' ============================================================
Public Sub RefreshWorkbook()
    Dim url As String
    url = API_BASE & "/api/export/excel"

    Dim savePath As String
    savePath = ThisWorkbook.Path & "\mumbai_local_delays_" & Format(Now, "YYYYMMDD") & ".xlsx"

    MsgBox "Downloading workbook from " & url & " ..." & vbCrLf & _
           "Save path: " & savePath, vbInformation, "Mumbai Local — Refresh"

    Dim req As Object
    Set req = CreateObject("MSXML2.ServerXMLHTTP.6.0")

    On Error GoTo ErrHandler
    req.Open "GET", url, False
    req.setRequestHeader "Accept", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    req.send

    If req.Status = 200 Then
        ' Write binary response to disk
        Dim stream As Object
        Set stream = CreateObject("ADODB.Stream")
        stream.Type = 1  ' binary
        stream.Open
        stream.Write req.responseBody
        stream.SaveToFile savePath, 2  ' overwrite
        stream.Close

        MsgBox "Done! File saved:" & vbCrLf & savePath & vbCrLf & vbCrLf & _
               "Opening now...", vbInformation, "Mumbai Local — Success"

        Workbooks.Open savePath
    Else
        MsgBox "API returned HTTP " & req.Status & vbCrLf & _
               "Response: " & req.responseText, vbCritical, "Mumbai Local — Error"
    End If
    Exit Sub

ErrHandler:
    MsgBox "Connection failed." & vbCrLf & _
           "Is the API running? Try: uvicorn api.main:app --reload" & vbCrLf & vbCrLf & _
           "Error: " & Err.Description, vbCritical, "Mumbai Local — Connection Error"
End Sub


' ============================================================
' PUBLIC: Refresh Rankings sheet from /api/rankings JSON
' ============================================================
Public Sub RefreshRankingsSheet()
    Dim ws As Worksheet
    Set ws = GetOrCreateSheet(SHEET_RANKINGS)
    ws.Cells.Clear

    Dim lines(2) As String
    lines(0) = "Central"
    lines(1) = "Western"
    lines(2) = "Harbour"

    Dim periods(3) As String
    periods(0) = "morning_peak"
    periods(1) = "evening_peak"
    periods(2) = "off_peak"
    periods(3) = "night"

    ' Write header
    Dim headers(5) As String
    headers(0) = "Station"
    headers(1) = "Line"
    headers(2) = "Period"
    headers(3) = "Avg Delay (min)"
    headers(4) = "CI Lower"
    headers(5) = "CI Upper"
    WriteHeader ws, headers, 1

    Dim dataRow As Long
    dataRow = 2

    Dim i As Integer, j As Integer
    For i = 0 To 2
        For j = 0 To 3
            Dim url As String
            url = API_BASE & "/api/rankings?line=" & lines(i) & "&period=" & periods(j)
            Dim json As String
            json = HttpGet(url)

            If json <> "" And json <> "[]" Then
                dataRow = ParseRankingsJSON(ws, json, lines(i), periods(j), dataRow)
            End If
        Next j
    Next i

    ws.Columns("A:F").AutoFit
    ws.Range("A1").Select
    ws.Activate

    AddTimestamp ws

    MsgBox "Rankings refreshed — " & (dataRow - 2) & " rows written.", vbInformation, "Mumbai Local"
End Sub


' ============================================================
' PUBLIC: Refresh Anomalies sheet from /api/anomalies JSON
' ============================================================
Public Sub RefreshAnomaliesSheet()
    Dim ws As Worksheet
    Set ws = GetOrCreateSheet(SHEET_ANOMALIES)
    ws.Cells.Clear

    Dim headers(5) As String
    headers(0) = "Station"
    headers(1) = "Severity"
    headers(2) = "Actual Delay (min)"
    headers(3) = "Expected (min)"
    headers(4) = "Upper Bound"
    headers(5) = "Date"
    WriteHeader ws, headers, 1

    Dim url As String
    url = API_BASE & "/api/anomalies"
    Dim json As String
    json = HttpGet(url)

    Dim dataRow As Long
    dataRow = 2

    If json <> "" And json <> "[]" Then
        dataRow = ParseAnomaliesJSON(ws, json, dataRow)
    End If

    ws.Columns("A:F").AutoFit
    AddTimestamp ws

    MsgBox "Anomalies refreshed — " & (dataRow - 2) & " rows written.", vbInformation, "Mumbai Local"
End Sub


' ============================================================
' PUBLIC: Refresh all sheets in one shot
' ============================================================
Public Sub RefreshAll()
    Application.ScreenUpdating = False
    On Error Resume Next
    RefreshRankingsSheet
    RefreshAnomaliesSheet
    Application.ScreenUpdating = True
    MsgBox "All sheets refreshed.", vbInformation, "Mumbai Local"
End Sub


' ============================================================
' PRIVATE: HTTP GET helper
' ============================================================
Private Function HttpGet(url As String) As String
    On Error GoTo ErrHandler
    Dim req As Object
    Set req = CreateObject("MSXML2.XMLHTTP.6.0")
    req.Open "GET", url, False
    req.setRequestHeader "Accept", "application/json"
    req.send
    If req.Status = 200 Then
        HttpGet = req.responseText
    Else
        HttpGet = ""
    End If
    Exit Function
ErrHandler:
    HttpGet = ""
End Function


' ============================================================
' PRIVATE: Minimal JSON array parser for rankings
' Returns next available dataRow
' ============================================================
Private Function ParseRankingsJSON(ws As Worksheet, json As String, _
                                   line As String, period As String, _
                                   startRow As Long) As Long
    Dim row As Long
    row = startRow

    ' Strip outer brackets
    json = Trim(json)
    If Left(json, 1) = "[" Then json = Mid(json, 2, Len(json) - 2)

    ' Split into objects by "},"
    Dim items() As String
    items = Split(json, "},{")

    Dim i As Integer
    For i = 0 To UBound(items)
        Dim obj As String
        obj = items(i)
        obj = Replace(obj, "{", "")
        obj = Replace(obj, "}", "")

        Dim station As String
        station = ExtractJsonString(obj, "station_name")
        Dim avgDelay As Double
        avgDelay = ExtractJsonNumber(obj, "avg_delay")
        Dim ciLower As String
        ciLower = ExtractJsonRaw(obj, "ci_lower")
        Dim ciUpper As String
        ciUpper = ExtractJsonRaw(obj, "ci_upper")

        If station <> "" Then
            ws.Cells(row, 1).Value = station
            ws.Cells(row, 2).Value = line
            ws.Cells(row, 3).Value = Replace(period, "_", " ")
            ws.Cells(row, 4).Value = avgDelay
            ws.Cells(row, 4).NumberFormat = "0.00"
            If ciLower <> "null" Then ws.Cells(row, 5).Value = CDbl(ciLower)
            If ciUpper <> "null" Then ws.Cells(row, 6).Value = CDbl(ciUpper)

            ' Traffic-light fill on Avg Delay
            If avgDelay >= 5 Then
                ws.Cells(row, 4).Interior.Color = CLR_RED
            ElseIf avgDelay >= 3 Then
                ws.Cells(row, 4).Interior.Color = CLR_YELLOW
            Else
                ws.Cells(row, 4).Interior.Color = CLR_GREEN
            End If

            row = row + 1
        End If
    Next i

    ParseRankingsJSON = row
End Function


' ============================================================
' PRIVATE: Minimal JSON array parser for anomalies
' ============================================================
Private Function ParseAnomaliesJSON(ws As Worksheet, json As String, startRow As Long) As Long
    Dim row As Long
    row = startRow

    json = Trim(json)
    If Left(json, 1) = "[" Then json = Mid(json, 2, Len(json) - 2)

    Dim items() As String
    items = Split(json, "},{")

    Dim i As Integer
    For i = 0 To UBound(items)
        Dim obj As String
        obj = items(i)
        obj = Replace(obj, "{", "")
        obj = Replace(obj, "}", "")

        Dim station As String
        station = ExtractJsonString(obj, "station")
        Dim severity As String
        severity = ExtractJsonString(obj, "severity")
        Dim actual As Double
        actual = ExtractJsonNumber(obj, "actual")
        Dim expected As Double
        expected = ExtractJsonNumber(obj, "expected")
        Dim upper As Double
        upper = ExtractJsonNumber(obj, "upper")
        Dim dt As String
        dt = ExtractJsonString(obj, "date")

        If station <> "" Then
            ws.Cells(row, 1).Value = station
            ws.Cells(row, 2).Value = severity
            ws.Cells(row, 3).Value = actual
            ws.Cells(row, 3).NumberFormat = "0.00"
            ws.Cells(row, 4).Value = expected
            ws.Cells(row, 4).NumberFormat = "0.00"
            ws.Cells(row, 5).Value = upper
            ws.Cells(row, 5).NumberFormat = "0.00"
            ws.Cells(row, 6).Value = dt

            Select Case UCase(severity)
                Case "HIGH"
                    ws.Cells(row, 2).Interior.Color = CLR_RED
                Case "MEDIUM"
                    ws.Cells(row, 2).Interior.Color = CLR_YELLOW
                Case Else
                    ws.Cells(row, 2).Interior.Color = CLR_GREEN
            End Select

            row = row + 1
        End If
    Next i

    ParseAnomaliesJSON = row
End Function


' ============================================================
' PRIVATE: JSON field extraction helpers (no external library)
' ============================================================
Private Function ExtractJsonString(json As String, key As String) As String
    Dim pattern As String
    pattern = """" & key & """:"""
    Dim pos As Long
    pos = InStr(json, pattern)
    If pos = 0 Then
        ExtractJsonString = ""
        Exit Function
    End If
    pos = pos + Len(pattern)
    Dim endPos As Long
    endPos = InStr(pos, json, """")
    ExtractJsonString = Mid(json, pos, endPos - pos)
End Function

Private Function ExtractJsonNumber(json As String, key As String) As Double
    Dim raw As String
    raw = ExtractJsonRaw(json, key)
    If raw = "" Or raw = "null" Then
        ExtractJsonNumber = 0
    Else
        ExtractJsonNumber = CDbl(raw)
    End If
End Function

Private Function ExtractJsonRaw(json As String, key As String) As String
    Dim pattern As String
    pattern = """" & key & """:"
    Dim pos As Long
    pos = InStr(json, pattern)
    If pos = 0 Then
        ExtractJsonRaw = ""
        Exit Function
    End If
    pos = pos + Len(pattern)
    Dim endPos As Long
    Dim commaPos As Long, bracePos As Long
    commaPos = InStr(pos, json, ",")
    bracePos = InStr(pos, json, "}")
    If commaPos = 0 Then commaPos = Len(json) + 1
    If bracePos = 0 Then bracePos = Len(json) + 1
    endPos = IIf(commaPos < bracePos, commaPos, bracePos)
    ExtractJsonRaw = Trim(Mid(json, pos, endPos - pos))
End Function


' ============================================================
' PRIVATE: Sheet management helpers
' ============================================================
Private Function GetOrCreateSheet(name As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(name)
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = name
    End If
    Set GetOrCreateSheet = ws
End Function

Private Sub WriteHeader(ws As Worksheet, headers() As String, headerRow As Long)
    Dim i As Integer
    For i = 0 To UBound(headers)
        Dim cell As Range
        Set cell = ws.Cells(headerRow, i + 1)
        cell.Value = headers(i)
        cell.Font.Bold = True
        cell.Font.Color = CLR_HDR_TXT
        cell.Interior.Color = CLR_HDR
        cell.HorizontalAlignment = xlCenter
    Next i
    ws.Rows(headerRow).RowHeight = 18
    ws.Application.ActiveWindow.FreezePanes = False
    ws.Rows(headerRow + 1).Select
    ws.Application.ActiveWindow.FreezePanes = True
End Sub

Private Sub AddTimestamp(ws As Worksheet)
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 2
    ws.Cells(lastRow, 1).Value = "Generated: " & Format(Now, "YYYY-MM-DD HH:NN")
    ws.Cells(lastRow, 1).Font.Italic = True
    ws.Cells(lastRow, 1).Font.Color = RGB(136, 136, 136)
    ws.Cells(lastRow, 1).Font.Size = 9
End Sub
