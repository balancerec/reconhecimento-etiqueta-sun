$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$bridge=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} | Select-Object -First 1
function Await-Result($Operation,[Type]$ResultType){$task=$bridge.MakeGenericMethod($ResultType).Invoke($null,@($Operation));$task.Wait();return $task.Result}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('pt-BR'))
if(-not $engine){throw 'Windows OCR pt-BR unavailable'}
$inputs=Get-Content -LiteralPath $env:SUN_NATIVE_INPUTS -Raw -Encoding UTF8 | ConvertFrom-Json;$rows=@()
foreach($entry in $inputs){
 $file=Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($entry.path)) ([Windows.Storage.StorageFile]);$stream=Await-Result ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream]);$decoder=Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]);$bitmap=Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]);$result=Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult]);$blocks=@();$index=0
 foreach($line in $result.Lines){$xs=@();$ys=@();$xx=@();$yy=@();foreach($word in $line.Words){$b=$word.BoundingRect;$xs+=$b.X;$ys+=$b.Y;$xx+=($b.X+$b.Width);$yy+=($b.Y+$b.Height)};$x=($xs|Measure-Object -Minimum).Minimum;$y=($ys|Measure-Object -Minimum).Minimum;$right=($xx|Measure-Object -Maximum).Maximum;$bottom=($yy|Measure-Object -Maximum).Maximum;$blocks+=@{id=$index;text=$line.Text;confidence=$null;polygon_local=@(@($x,$y),@($right,$y),@($right,$bottom),@($x,$bottom))};$index++}
 $rows+=@{roi_id=$entry.roi_id;blocks=$blocks;provider='Windows native backend not observable; no CUDA claim';confidence_calibrated=$null};$bitmap.Dispose();$stream.Dispose()
}
ConvertTo-Json -InputObject $rows -Depth 20 | Set-Content -LiteralPath $env:SUN_NATIVE_OUTPUT -Encoding UTF8

