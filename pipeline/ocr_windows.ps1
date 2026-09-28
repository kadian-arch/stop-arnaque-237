# Reads text from images with the OCR engine built into Windows 10/11 (no install).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File ocr_windows.ps1 -ListFile images.txt
# images.txt holds one absolute image path per line. Output: JSON {path: {"en": text, "fr": text}} on stdout.
param([Parameter(Mandatory = $true)][string]$ListFile)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($op, [Type]$type) {
    $task = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$engines = @{}
foreach ($tag in @('en-US', 'fr-FR')) {
    $e = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($tag))
    if ($e) { $engines[$tag.Substring(0, 2)] = $e }
}

$out = @{}
foreach ($path in Get-Content -LiteralPath $ListFile -Encoding UTF8) {
    if (-not $path.Trim()) { continue }
    $res = @{}
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        foreach ($k in $engines.Keys) {
            $r = Await ($engines[$k].RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $res[$k] = (($r.Lines | ForEach-Object { $_.Text }) -join "`n")
        }
        $stream.Dispose()
    }
    catch { $res['error'] = $_.Exception.Message }
    $out[$path] = $res
}
$out | ConvertTo-Json -Depth 4 -Compress
