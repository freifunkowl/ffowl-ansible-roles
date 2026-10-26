# HopGlass-FFGT-Frontend unter Debian 13

Diese Rolle installiert das npm-basierte HopGlass-Frontend aus dem zugehörigen
Sicherheits-Patchset. Sie setzt **Debian 13 (trixie)** mit funktionierenden,
signierten Debian-Paketquellen einschließlich `trixie-security`, gesammelten
Ansible-Facts und administrativen Rechten voraus. Die Ansible-Verbindung muss
`become_user: hopglass` unterstützen. Git und npm laufen als `hopglass`, APT und
Benutzerverwaltung als Administrator. `acl` unterstützt den Wechsel zwischen
unprivilegierten Ansible- und Build-Benutzern.

## Zuerst die neue Client-Version bereitstellen

Das Client-Patchset und dieses Rollen-Patchset sind getrennte Änderungen.
Die zuvor erstellten Client-Commits wurden nicht zu GitHub gepusht. Daher ist
`hopglass_client_version` absichtlich leer: Die Rolle bricht vor Änderungen mit
einer verständlichen Meldung ab, bis eine veröffentlichte Commit-ID gesetzt ist.

1. Das HopGlass-Sicherheits-Patchset im Client-Repository anwenden.
2. Tests und Build prüfen, den gepatchten Branch in das eigene oder das
   freigegebene Upstream-Repository pushen.
3. Die **tatsächlich veröffentlichte** 40-stellige Commit-ID mit `git rev-parse
   HEAD` bestimmen. `git am` kann andere IDs erzeugen als die ursprünglichen
   Patch-Commits. Keine lokale, auf dem Remote unerreichbare ID eintragen.
4. Repository und Commit im Inventory setzen, beispielsweise:

```yaml
hopglass_client_repo: https://github.com/ffgtso/hopglass.git
hopglass_client_version: '<veroeffentlichte-40-stellige-commit-id>'
hopglass_client_run_tests: true
```

Bei einem Fork entsprechend `hopglass_client_repo` ändern. Die Commit-ID muss
von einem veröffentlichten Branch oder Tag erreichbar sein. Die Rolle erzwingt
keinen beweglichen Branch wie `master` und verwirft keine lokalen Änderungen an
versionierten Dateien (`force: false`). Solche Änderungen vorher sichern und
bereinigen. Ein altes Yarn/Grunt-Checkout wird vor npm-Ausführung abgewiesen.

## Verhalten

- Debian-Pakete `nodejs`, `npm`, `git`, `ca-certificates`, `python3`, `acl` werden
  installiert/aktualisiert. Keine NodeSource-/Yarn-Quelle wird hinzugefügt.
- Die von der alten Rolle angelegte `/etc/apt/apt.conf.d/99darnkey` wird entfernt.
  Aktive NodeSource-16- und Yarn-Einträge werden aus `/etc/apt/sources.list` und
  `sources.list.d/*.list` entfernt, unabhängig vom damaligen Codenamen und vom
  `trusted=yes`-Zusatz. Andere Zeilen bleiben unverändert.
- Das ist eine Migration der **alten Rolle**, keine allgemeine Bereinigung aller
  APT-Quellen: separat eingerichtete Deb822-`.sources`, andere NodeSource-Versionen,
  fremde Pins oder andere globale APT-Ausnahmen müssen vorab zum Debian-13-Zielbild
  passen. Pakete werden nicht erzwungen heruntergestuft oder deinstalliert.
- Bestehende Checkouts werden auf den Benutzer `hopglass` übertragen; Verzeichnisse
  erhalten durchsuchbare Rechte. Globale Git-`safe.directory`-Ausnahmen werden
  nicht mehr benötigt oder neu angelegt.
- Abhängigkeiten: `npm ci --ignore-scripts --include=dev --no-audit --no-fund`.
  Entwicklungsabhängigkeiten sind für Build und Tests erforderlich, auch bei
  einem extern gesetzten `NODE_ENV=production`.
- Danach `npm test` (standardmäßig) und `npm run build`.
- Ein Erfolgsmarker bindet den Build an Git-Commit, Lockfile-Prüfsumme, Node-/npm-
  Version und Testeinstellung. Unveränderte Wiederholung überspringt npm.
  Fehlende Kern-Builddateien oder `node_modules` lösen einen Neuaufbau aus.
- Der Marker wird **vor** einem Buildversuch entfernt und erst nach vollständigem
  Erfolg geschrieben. Ein fehlgeschlagener Versuch wird beim nächsten Lauf
  wiederholt, auch wenn Git dann keine Änderungen meldet.
- `hopglass_client_force_build: true` erzwingt eine Reparatur, beispielsweise bei
  beschädigten Dateien innerhalb eines noch vorhandenen `node_modules` oder bei
  fehlenden Fonts. Der Marker ist keine vollständige Integritätsprüfung.
- Hardwarebilder verwenden einen getrennten Git-Status und lösen keinen Client-
  Build aus. Dafür bleiben `/opt/hopglass/hwpics` und der bisherige Standard-Branch
  erhalten; `hopglass_hwpics_repo` und `hopglass_hwpics_version` sind überschreibbar.
- Die bisherigen drei Konfigurationsvorlagen bleiben unverändert. Gerendertes JSON
  wird vor dem Ersetzen validiert. `build/config.json` und Domain-/Community-Dateien
  bleiben beim Client-Build erhalten. Vorhandene Inventory-Variablen `domaenen`,
  `mapconfig`, `freifunk`, `freifunk_map` usw. werden weiter benötigt.
- `--check` führt keine npm-Kommandos und keine Build-Eingabeprüfung aus. Der
  Check-Modus ersetzt deshalb keinen ersten echten Installationslauf.

Standardpfade bleiben `/opt/hopglass/client/build` und
`/opt/hopglass/hwpics/nodes`, passend zur vorhandenen nginx-Rolle. Wenn der optionale
`hopglass_client_dir` geändert wird, muss die nginx-Konfiguration separat angepasst
werden. Die Rolle richtet weder nginx noch HopGlass Server ein.

`npm audit` bleibt ein separater Freigabeschritt vor dem Rollout; ein veränderlicher
Online-Audit wird nicht bei jedem Konfigurationslauf erzwungen. Auf dem gebauten
Client kann er als `hopglass` im Checkout ausgeführt werden.

## Wechselwirkung mit anderen Rollen

Die im selben Repository vorhandene Rolle `mapserver_hopglass-server` schreibt
weiterhin `99darnkey` und NodeSource-16-Quellen. Sie wurde hier nicht geändert.
Wird sie weiter eingesetzt, muss auch ihre Paketverwaltung auf Debian 13 umgestellt
werden; andernfalls kann sie die unsicheren Einstellungen wiederherstellen oder
vorher bereits bei APT scheitern. Bloßes Umordnen der Rollen ist keine dauerhafte
Lösung. Die Migration des gemeinsamen Node.js betrifft auch einen eventuell
installierten Backend-Dienst; dessen Kompatibilität ist separat zu testen.

## Lokale Tests

Die Tests verändern weder Systempakete noch Benutzer oder Zielserver.
Voraussetzung auf dem Controller: Python 3, `ansible-core` und PyYAML.
Im Stammverzeichnis dieses Rollen-Repositories:

```sh
ANSIBLE_ROLES_PATH="$PWD" ansible-playbook -i localhost, \
  mapserver_hopglass_deb13/tests/syntax.yml --syntax-check
python3 mapserver_hopglass_deb13/tests/test_build.py
python3 mapserver_hopglass_deb13/tests/test_sources.py
```

`test_build.py` führt die tatsächlichen Ansible-Buildtasks aus, ersetzt npm/node
aber durch isolierte Testprogramme. Geprüft werden Erstlauf, unveränderte
Wiederholung, fehlende Ausgaben, geänderte Lockdatei/Commit-ID, fehlgeschlagener
Build mit Wiederaufnahme, Konfigurationserhalt und Ablehnung des alten Checkouts.
Es ist kein Integrationstest der Debian-Paketmigration, des Benutzerwechsels,
des Webservers. Zusätzlich wurden die unveränderten Buildtasks gegen den echten
gepatchten Client mit Node.js 20.19.2/npm 9 ausgeführt (Installation, Regressionstests
und Build erfolgreich). Testumgebung: Ubuntu mit ansible-core 2.19.14, nicht Debian.
Ein vollständiger Rollenlauf auf Debian 13 bleibt vor dem produktiven Einsatz
erforderlich.
