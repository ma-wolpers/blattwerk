<#
.SYNOPSIS
  Entfernt die Blattwerk-Eintraege aus "Oeffnen mit" wieder (Gegenstueck zu register-blattwerk-file-association.ps1).

.DESCRIPTION
  Loescht ausschliesslich die von Blattwerk angelegten Schluessel unter HKEY_CURRENT_USER\Software\Classes:
    Applications\Blattwerk.exe            (samt Unterschluesseln)
    .md\OpenWithList\Blattwerk.exe
  Andere Zuordnungen fuer .md bleiben unangetastet. Ohne Administratorrechte, nur fuer den aktuellen Benutzer.
  Nicht vorhandene Eintraege werden uebersprungen (das Skript ist beliebig oft ausfuehrbar).

.PARAMETER ClassesRoot
  Wurzel der Registry-Klassen. Standard: HKCU:\Software\Classes. Nur fuer Tests umlenken.

.EXAMPLE
  .\unregister-blattwerk-file-association.ps1 -WhatIf
  Zeigt nur an, was entfernt wuerde.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ClassesRoot = 'HKCU:\Software\Classes'
)

$ErrorActionPreference = 'Stop'

$AppKeyName = 'Blattwerk.exe'
$Extension = '.md'

$targets = @(
    (Join-Path $ClassesRoot "Applications\$AppKeyName"),
    (Join-Path $ClassesRoot "$Extension\OpenWithList\$AppKeyName")
)

foreach ($key in $targets) {
    if (-not (Test-Path -LiteralPath $key)) {
        Write-Host "Nicht vorhanden, uebersprungen: $key"
        continue
    }
    if ($PSCmdlet.ShouldProcess($key, 'Schluessel samt Unterschluesseln entfernen')) {
        Remove-Item -LiteralPath $key -Recurse -Force
        Write-Host "Entfernt: $key"
    }
}

if ($ClassesRoot -eq 'HKCU:\Software\Classes' -and -not $WhatIfPreference) {
    Add-Type -Namespace Win32 -Name Shell -MemberDefinition '[System.Runtime.InteropServices.DllImport("shell32.dll")] public static extern void SHChangeNotify(int eventId, uint flags, System.IntPtr item1, System.IntPtr item2);'
    [Win32.Shell]::SHChangeNotify(0x08000000, 0, [System.IntPtr]::Zero, [System.IntPtr]::Zero)
}

Write-Host 'Fertig.'
