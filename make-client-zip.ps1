# Builds BrainOut-client.zip: client jar + packages + slim JRE (jlink) + connect.bat + README.
# Run after `gradlew desktop:dist` and `make_data client`:
#   powershell -ExecutionPolicy Bypass -File make-client-zip.ps1 [-Jdk "C:\Program Files\Java\jdk-17"]
param(
    [string]$Jdk = "C:\Program Files\Java\jdk-17"
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$out = Join-Path $root "build\friend\BrainOut"
$zip = Join-Path $root "BrainOut-client.zip"

if (-not (Test-Path "$root\bin\client\brainout-desktop.jar")) { throw "bin\client\brainout-desktop.jar not found: run gradlew desktop:dist" }
if (-not (Test-Path "$root\bin\client\packages")) { throw "bin\client\packages not found: run make_data client" }
if (-not (Test-Path "$Jdk\bin\jlink.exe")) { throw "jlink not found in $Jdk (need JDK 17)" }

if (Test-Path (Join-Path $root "build\friend")) { Remove-Item -Recurse -Force (Join-Path $root "build\friend") }
New-Item -ItemType Directory -Force "$out\client" | Out-Null

Write-Host "jlink: slim JRE..."
& "$Jdk\bin\jlink.exe" --add-modules "java.base,java.desktop,java.naming,java.prefs,java.security.jgss,java.sql,jdk.unsupported,jdk.crypto.ec,jdk.zipfs,java.net.http,jdk.charsets,jdk.localedata" `
    --strip-debug --no-man-pages --no-header-files --compress=2 --output "$out\jre"
if ($LASTEXITCODE -ne 0) { throw "jlink failed" }

Write-Host "Copying client..."
Copy-Item "$root\bin\client\brainout-desktop.jar" "$out\client\"
Copy-Item -Recurse "$root\bin\client\packages" "$out\client\"
Copy-Item "$root\connect.bat" "$out\"
Copy-Item "$root\docs\friend-README.txt" "$out\README.txt"

Write-Host "Zipping..."
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $out -DestinationPath $zip -CompressionLevel Optimal
Write-Host ("Done: {0} ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))
