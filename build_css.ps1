# Recompila el CSS de Tailwind tras editar plantillas o static/src/input.css.
# Requiere tailwindcss.exe en la carpeta (CLI standalone; no necesita Node).
# IMPORTANTE: borra static/css antes de compilar; el binario v4 (Bun) en Windows/OneDrive
# falla con EEXIST si la carpeta de salida ya existe.
# Uso:  .\build_css.ps1

if (-not (Test-Path ".\tailwindcss.exe")) {
  Write-Host "Falta tailwindcss.exe. Descárgalo de:" -ForegroundColor Yellow
  Write-Host "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe"
  exit 1
}

Remove-Item static\css -Recurse -Force -ErrorAction SilentlyContinue
& .\tailwindcss.exe -i static\src\input.css -o static\css\app.css --minify 2>&1 | Out-String | Out-Null

if (Test-Path static\css\app.css) {
  Write-Host ("OK: static/css/app.css " + [math]::Round((Get-Item static\css\app.css).Length/1kb,1) + " KB") -ForegroundColor Green
} else {
  Write-Host "ERROR: no se generó el CSS" -ForegroundColor Red
}
