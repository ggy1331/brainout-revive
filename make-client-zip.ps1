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
& "$Jdk\bin\jlink.exe" --add-modules "java.base,java.desktop,java.naming,java.prefs,java.security.jgss,java.sql,jdk.unsupported,jdk.crypto.ec,jdk.zipfs,java.net.http,jdk.charsets,jdk.localedata,jdk.httpserver,java.management,java.logging,java.xml,java.scripting" `
    --strip-debug --no-man-pages --no-header-files --compress=2 --output "$out\jre"
if ($LASTEXITCODE -ne 0) { throw "jlink failed" }

Write-Host "Copying client..."
Copy-Item "$root\bin\client\brainout-desktop.jar" "$out\client\"
Copy-Item -Recurse "$root\bin\client\packages" "$out\client\"
Copy-Item "$root\connect.bat" "$out\"
Copy-Item "$root\connect-online.bat" "$out\"

# --- solo PvE Conflict Zone: local game server + local back-end + portable Python (from the installed 3.10)
Write-Host "Copying server (solo PvE)..."
New-Item -ItemType Directory -Force "$out\server" | Out-Null
Copy-Item "$root\bin\server\brainout-server.jar" "$out\server\"
Copy-Item -Recurse "$root\bin\server\packages", "$root\bin\server\maps" "$out\server\"
Get-ChildItem "$root\bin\server" -File | Where-Object { $_.Extension -in ".json", ".shuffle", ".xml" } |
    Copy-Item -Destination "$out\server\"
Write-Host "Copying back-end..."
New-Item -ItemType Directory -Force "$out\backend\services" | Out-Null
Copy-Item "$root\tools\mock-backend\backend.py" "$out\backend\"
Copy-Item "$root\tools\mock-backend\services\*.py" "$out\backend\services\"
Write-Host "Portable Python..."
$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310"
if (-not (Test-Path "$py\python310.dll")) { throw "Python 3.10 not found in $py" }
New-Item -ItemType Directory -Force "$out\python" | Out-Null
foreach ($f in "python.exe", "python310.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll", "LICENSE.txt") {
    Copy-Item "$py\$f" "$out\python\"
}
foreach ($f in "_socket.pyd", "select.pyd", "_hashlib.pyd", "_ssl.pyd", "libcrypto-1_1.dll", "libssl-1_1.dll",
               "_uuid.pyd", "_queue.pyd", "unicodedata.pyd", "_ctypes.pyd", "libffi-7.dll", "_bz2.pyd",
               "_lzma.pyd", "pyexpat.pyd", "_overlapped.pyd", "_asyncio.pyd", "_multiprocessing.pyd") {
    Copy-Item "$py\DLLs\$f" "$out\python\"
}
# stdlib as a zip next to python.exe; the ._pth file makes python ignore the user's own installation
& "$root\build\pyenv\Scripts\python.exe" -c @"
import os, sys, zipfile
lib, dst = sys.argv[1], sys.argv[2]
skip = {'test', 'tkinter', 'idlelib', 'turtledemo', 'site-packages', 'ensurepip', 'lib2to3', 'venv', 'pydoc_data', '__pycache__', 'distutils', 'unittest', 'msilib'}
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(lib):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, lib))
"@ "$py\Lib" "$out\python\python310.zip"
if ($LASTEXITCODE -ne 0) { throw "stdlib zip failed" }
[IO.File]::WriteAllText("$out\python\python310._pth", "python310.zip`r`n.`r`n..\backend`r`n")
Copy-Item "$root\play-solo.bat", "$root\play-solo.ps1" "$out\"
Copy-Item "$root\docs\friend-README.txt" "$out\README.txt"

Write-Host "Zipping..."
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $out -DestinationPath $zip -CompressionLevel Optimal
Write-Host ("Done: {0} ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))
