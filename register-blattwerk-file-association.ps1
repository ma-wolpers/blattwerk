<#
.SYNOPSIS
  Traegt Blattwerk unter "Oeffnen mit" fuer .md-Dateien ein (nur fuer den aktuellen Windows-Benutzer).

.DESCRIPTION
  WAS   Legt unter HKEY_CURRENT_USER\Software\Classes einen Anwendungseintrag "Blattwerk.exe" an und
        verknuepft ihn mit der Endung .md. Der Befehl dahinter startet
            .venv\Scripts\pythonw.exe blattwerk.py "<Datei>"
        (Pfade werden aus dem Ordner dieses Skripts abgeleitet).
  WANN  Einmal nach dem Einrichten von Blattwerk. Erneut ausfuehren, wenn der Blattwerk-Ordner
        verschoben oder die .venv neu angelegt wurde (der gespeicherte Pfad zeigt sonst ins Leere).
  WOFUER Rechtsklick auf eine .md-Datei -> "Oeffnen mit" -> "Blattwerk". Laeuft Blattwerk bereits,
        oeffnet sich die Datei als neuer Tab im bestehenden Fenster (kein zweites Fenster).
  WIESO HKCU statt HKLM: gilt nur fuer diesen Benutzer, braucht keine Administratorrechte und
        aendert nichts an anderen Benutzern oder am System.
        Es wird KEIN Standardprogramm gesetzt: .md-Dateien oeffnen sich weiter mit dem bisherigen
        Programm, Blattwerk erscheint nur zusaetzlich in der Auswahl.
  RUECKGAENGIG  unregister-blattwerk-file-association.ps1
  Ausfuehrliche Erklaerung: docs\nutzer\OEFFNEN_MIT_EINRICHTEN.md

.PARAMETER ClassesRoot
  Wurzel der Registry-Klassen. Standard: HKCU:\Software\Classes. Nur fuer Tests auf einen anderen
  Schluessel umlenken.

.EXAMPLE
  .\register-blattwerk-file-association.ps1 -WhatIf
  Zeigt nur an, welche Registry-Eintraege geschrieben wuerden, ohne etwas zu aendern.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ClassesRoot = 'HKCU:\Software\Classes'
)

$ErrorActionPreference = 'Stop'

$AppKeyName = 'Blattwerk.exe'
$Extension = '.md'

$repoRoot = $PSScriptRoot
$pythonw = Join-Path $repoRoot '.venv\Scripts\pythonw.exe'
$entry = Join-Path $repoRoot 'blattwerk.py'
$icon = Join-Path $repoRoot 'assets\app.ico'

if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "Blattwerk-Umgebung fehlt: $pythonw`nBitte zuerst die .venv einrichten (siehe start-blattwerk.bat)."
}
if (-not (Test-Path -LiteralPath $entry)) {
    throw "Startdatei nicht gefunden: $entry"
}

function Set-RegistryValue {
    # Legt den Schluessel bei Bedarf an (ohne vorhandene Werte zu loeschen) und setzt einen Wert.
    param([string]$Key, [string]$Name, [string]$Value, [string]$What)
    if ($PSCmdlet.ShouldProcess("$Key [$Name]", $What)) {
        # -Force legt fehlende Elternschluessel mit an; er wird nur fuer NEUE Schluessel aufgerufen
        # (Test-Path davor), damit vorhandene Schluessel samt Werten nie ueberschrieben werden.
        if (-not (Test-Path -LiteralPath $Key)) {
            New-Item -Path $Key -Force | Out-Null
        }
        Set-ItemProperty -LiteralPath $Key -Name $Name -Value $Value
    }
}

$appKey = Join-Path $ClassesRoot "Applications\$AppKeyName"
$command = '"{0}" "{1}" "%1"' -f $pythonw, $entry

# 1) Anwendungseintrag: Name in der "Oeffnen mit"-Liste und der Startbefehl.
Set-RegistryValue -Key $appKey -Name 'FriendlyAppName' -Value 'Blattwerk' -What 'Anzeigename setzen'
Set-RegistryValue -Key "$appKey\shell\open\command" -Name '(default)' -Value $command -What 'Startbefehl setzen'
if (Test-Path -LiteralPath $icon) {
    Set-RegistryValue -Key "$appKey\DefaultIcon" -Name '(default)' -Value $icon -What 'Symbol setzen'
}

# 2) Endung .md: Blattwerk als moegliches Programm anbieten (kein Standardprogramm!).
Set-RegistryValue -Key "$appKey\SupportedTypes" -Name $Extension -Value '' -What 'Endung als unterstuetzt melden'
if ($PSCmdlet.ShouldProcess("$ClassesRoot\$Extension\OpenWithList\$AppKeyName", 'in Auswahlliste eintragen')) {
    $listKey = Join-Path $ClassesRoot "$Extension\OpenWithList\$AppKeyName"
    if (-not (Test-Path -LiteralPath $listKey)) {
        New-Item -Path $listKey -Force | Out-Null
    }
}

# 3) Explorer ueber die geaenderte Zuordnung informieren (nur fuer die echte Registry).
if ($ClassesRoot -eq 'HKCU:\Software\Classes' -and -not $WhatIfPreference) {
    Add-Type -Namespace Win32 -Name Shell -MemberDefinition '[System.Runtime.InteropServices.DllImport("shell32.dll")] public static extern void SHChangeNotify(int eventId, uint flags, System.IntPtr item1, System.IntPtr item2);'
    [Win32.Shell]::SHChangeNotify(0x08000000, 0, [System.IntPtr]::Zero, [System.IntPtr]::Zero)
}

Write-Host ''
Write-Host "Fertig. Startbefehl: $command"
Write-Host 'Rechtsklick auf eine .md-Datei -> "Oeffnen mit" -> "Blattwerk".'
Write-Host 'Falls der Eintrag fehlt: Explorer-Fenster schliessen und neu oeffnen, ggf. einmal ab- und wieder anmelden.'
