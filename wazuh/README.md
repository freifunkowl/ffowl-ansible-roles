# Wazuh für ffowl-ansible-roles

Die Rolle installiert Wazuh **4.14.10** aus signierten DEB-Paketen. Ihr ordnet jedem Host seine Komponenten über das Inventar zu. Auf jedem Manager läuft zusätzlich Filebeat (OSS 7.10.2-2). Die Inventarnamen dienen als Knotennamen und bei Agenten als Identitäten.

| Beispieldatei unter `wazuh/examples/` | Indexer | Manager + Filebeat | Dashboard | Agent |
| --- | --- | --- | --- | --- |
| `inventory.ini` | wazuh01 | wazuh01 | wazuh01 | hv01 |
| `distributed.ini` | idx01 | mgr01 | ui01 | hv01 |
| `cluster.ini` | idx01, idx02, idx03 | mgr01 (Master), mgr02 (Worker) | ui01 | hv01, Ereignisse an mgr02 |

Die optionale standortgebundene Ablage von Alarmen bei einem zentralen Manager ist in [RZ-Installation.md](../RZ-Installation.md) beschrieben. Die Beispielkonfiguration für die drei Standorte steht in [hosts.wazuh](../hosts.wazuh).

## Installation

1. Entpackt `wazuh/` im Stamm von `ffowl-ansible-roles` neben den übrigen Rollen. Beim Wechsel von der vorherigen ZIP-Version ersetzt das alte Rollenverzeichnis als Ganzes. Bereits installierte Zentralen erfordern eine separate Migration.
2. Auf dem Controller werden Python 3, `ansible-core` ab 2.18, `cryptography` und `bcrypt` benötigt. Beispiel für eine eigene Umgebung:

   ```sh
   python3 -m venv ../venv-wazuh
   . ../venv-wazuh/bin/activate
   python -m pip install 'ansible-core>=2.18,<2.20' 'cryptography>=42' bcrypt
   ```

3. Kopiert eine der drei Beispieldateien. Ersetzt die Dokumentationsadressen und setzt den SSH-Benutzer bzw. `become` wie in Eurem übrigen Inventar. Alle drei zentralen Gruppen müssen mindestens einen Host enthalten. Ein Manager überwacht sich selbst als Agent 000. Auf ihm kollidieren die DEB-Pakete von Manager und Agent.

   ```sh
   export ANSIBLE_ROLES_PATH="$PWD${ANSIBLE_ROLES_PATH:+:$ANSIBLE_ROLES_PATH}"
   cp wazuh/examples/cluster.ini ../wazuh-inventory.ini
   ${EDITOR:-vi} ../wazuh-inventory.ini
   ansible-playbook -i ../wazuh-inventory.ini wazuh/examples/wazuh.yml --list-hosts
   ansible-playbook -i ../wazuh-inventory.ini wazuh/examples/wazuh.yml
   ansible-playbook -i ../wazuh-inventory.ini wazuh/tests/verify.yml
   ```

   Für einen Pilotbetrieb könnt Ihr zuerst nur die zentralen Dienste installieren und anschließend einzelne Endpunkte aufnehmen:

   ```sh
   ansible-playbook -i ../wazuh-inventory.ini wazuh/examples/wazuh.yml --limit 'wazuh_indexers:wazuh_servers:wazuh_dashboards'
   ansible-playbook -i ../wazuh-inventory.ini wazuh/examples/wazuh.yml --limit hv01
   ```

Die Zielsysteme benötigen Debian oder Ubuntu mit APT, systemd, Python 3 und SSH-Zugriff für Ansible. Die Zentrale unterstützt die Paketarchitekturen amd64 und arm64. Für den Produktivbetrieb auf einem System mit bis zu 25 Agenten nennt Wazuh 4 vCPU, 8 GiB RAM und 50 GB für 90 Tage Alarmdaten als Richtwerte. Für verteilte Installationen dimensioniert Ihr insbesondere Indexer-Heap und Speicher nach dem Ereignisaufkommen. [Wazuh Quickstart](https://documentation.wazuh.com/current/quickstart.html)

## Inventarvariablen

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `wazuh_cluster_name` | `wazuh` | Eindeutiger und stabiler Name der Installation. Trennt auch die Daten der Installationen auf dem Controller. |
| `wazuh_node_address` | `ansible_host`, sonst Inventarname | Adresse des Dienstnetzes dieses Hosts, etwa `10.48.30.11`. Die Adresse muß lokal bindbar und von den Kommunikationspartnern erreichbar sein. Bei SSH über NAT, Sprunghosts oder Portweiterleitungen ausdrücklich setzen. |
| `wazuh_master_host` | erster Host in `wazuh_servers` | Inventarname des Manager-Masters. Bei mehreren Managern ausdrücklich setzen und stabil halten. Dashboard und Registrierung greifen auf diesen Host zu. |
| `wazuh_manager_address` | Dienstadresse des Registrierungsmanagers | Ziel für den TCP-Ereignisstrom des jeweiligen Agenten. Hier sind auch ein Worker oder ein vorhandener TCP-Loadbalancer möglich. |
| `wazuh_manager_inventory_host` | `wazuh_master_host` | SSH-Ziel für die delegierte Agentenregistrierung. In einem Manager-Cluster muß dies der Master sein. |
| `wazuh_tls_dns_name` | leer | Vollqualifizierter DNS-Name pro zentralem Host. Die private CA nimmt ihn zusätzlich zur Dienstadresse als SAN auf. Bei öffentlichen Zertifikaten ist dies der geprüfte HTTPS-Name. |
| `wazuh_dashboard_letsencrypt` | `false` | Öffentlich vertrauenswürdiges Dashboard-Zertifikat. Im beigefügten Drei-RZ-Inventar für `siem01` aktiviert. |
| `wazuh_indexer_letsencrypt` | `false` | Als globale Inventarvariable auf `true` setzen, um auf sämtlichen Indexern öffentlich vertrauenswürdige HTTPS-Serverzertifikate zu verwenden. |
| `wazuh_indexer_heap` | `1g` | Minimum und Maximum des Java-Heaps je Indexer, z. B. `4g`. |
| `wazuh_state_dir` | `~/.local/share/ffowl-wazuh/<Clustername>` | Absoluter privater Pfad auf dem Controller. Alle Läufe einer Installation müssen denselben Inhalt verwenden. |
| `wazuh_api_request_timeout` | `60` | Serverseitiges Zeitlimit für einzelne Manager-API-Aufrufe in Sekunden. |
| `wazuh_connection_timeout` | `120` | Wartezeit in Sekunden auf eine bestätigte Agentenverbindung. `0` überspringt diese Prüfung. |
| `wazuh_apt_url` | `https://packages.wazuh.com/4.x/apt/` | APT-Quelle für die Wazuh-Pakete. Ein interner Spiegel muß die ursprünglichen signierten Metadaten anbieten. |
| `wazuh_component` | vom Playbook gesetzt | Für die Einbindung in eigene Plays: `indexer`, `manager`, `dashboard` oder `agent`. |

Für den Start von Manager und Indexer läßt systemd bis zu 15 Minuten zu, damit das Laden der Regeln und Plugins auf langsameren VMs abgeschlossen werden kann. Das Playbook startet zunächst die Indexer und initialisiert deren gemeinsame Security-Datenbank einmalig. Es prüft die Knotenzahl über die authentifizierte Cluster-API. Jeder Manager erhält alle Indexer-Adressen für Filebeat und den Wazuh-Indexer-Connector. Bei mehreren Managern prüft der Master die Mitgliedschaft der Worker. Anschließend verbindet sich das Dashboard mit den Indexern und der API des Masters. Das Dashboard-Paket 4.14.10 schaltet im API-Client des Plugins `wazuhCore` die Zertifikatsprüfung ausdrücklich ab. Die Rolle aktiviert diese Einstellung zur Prüfung von CA und Hostname und übergibt dem HTTPS-Client die CA dieser Installation ausdrücklich. Bei einem Versionswechsel muß diese Stelle erneut geprüft werden. Mehrere Dashboard-Hosts sind möglich. Einen Loadbalancer und einen automatischen Wechsel des Manager-Masters müßt Ihr bei Bedarf gesondert vorsehen.

## Verbindungen zwischen den Hosts

| Quelle | Ziel | TCP-Port |
| --- | --- | --- |
| Controller | Alle verwalteten Hosts | Euer SSH-Port |
| Agent | Zugewiesener Manager bzw. Loadbalancer | 1514 |
| Manager-Worker | Manager-Master | 1516 |
| Indexer | Andere Indexer | 9300 |
| Manager/Filebeat und Dashboard | Alle Indexer | 9200 |
| Dashboard | Manager-Master | 55000 |
| Admin-Netz | Dashboard | 443 |

Pflegt die Freigaben in Eurer vorhandenen Firewall. Die Registrierung nutzt vom Controller aus SSH und auf dem Manager den lokalen authd-Socket. TCP 1515 wird dafür nicht benötigt. Der Agent erhält nur seinen eigenen Schlüssel. Bei einem vorhandenen abweichenden Agentenschlüssel bricht die Rolle ab. Nehmt bei einem Hostersatz die alte Maschine außer Betrieb, bevor Ihr denselben Inventarnamen wiederverwendet.

## Zugang und Betrieb

Bei privatem Dashboard-Zertifikat öffnet `https://<Dienstadresse-des-Dashboards>/`. Bei aktiviertem Let’s Encrypt öffnet `https://<wazuh_tls_dns_name>/`. Meldet Euch als `admin` an. Die ACME-Einstellungen, DNS-01 über eine bestehende Certbot-Lineage und die optionale Umschaltung der Indexer-HTTPS-Schnittstellen sind in [RZ-Installation.md](../RZ-Installation.md) beschrieben. Wer Zugriff auf `state.json` hat, besitzt unter anderem den CA-Schlüssel, den Manager-Cluster-Schlüssel und administrative Kennwörter. Sichert das Zustandsverzeichnis verschlüsselt, schützt es mit Modus 0700 und verwendet auf weiteren Controllern ausschließlich eine aktuelle Kopie. Die normalen Indexer- und Manager-Datensicherungen werden zusätzlich benötigt.

Aus dem Zustandsverzeichnis auf dem Controller:

```sh
jq -r '.passwords.admin' state.json
jq -r '.ca.cert' state.json > ffowl-wazuh-root-ca.pem
```

Der zweite Befehl exportiert das öffentliche CA-Zertifikat, dem Ihr bei privatem Dashboard-Zertifikat im Admin-Browser vertrauen könnt. Die Dienstadresse des Dashboards steht im Zertifikat. Die Rolle erzeugt private Dienstzertifikate mit fünf Jahren Laufzeit und eine CA mit zehn Jahren Laufzeit. Plant Verlängerung und Kennwortrotation als Wartung. Für eine neue Dienstadresse erzeugt die Rolle ein neues Knotenzertifikat.

Bei einem abgebrochenen Lauf verwendet Ihr dasselbe Inventar und denselben Controllerzustand erneut. Jede Komponente erhält auf dem Ziel eine Besitzkennung unter `/var/lib/ffowl-wazuh/`. Bei einer fremden oder mit dem früheren All-in-one-Installer eingerichteten Zentrale stoppt der Bootstrap. Für einen Umzug sind insbesondere Indexer-Snapshots, Agentenschlüssel, Regeln und API-Konfiguration zu sichern und zu migrieren. Die DEB-Pakete erhalten einen Hold. Versionswechsel, ein Austausch der CA und Umbauten eines laufenden Quorums erfordern ein geplantes Wartungsfenster. Das gemeinsame Indexer-Play kann mehrere betroffene Dienste gleichzeitig neu starten. [Wazuh-Upgrades](https://documentation.wazuh.com/current/upgrade-guide/index.html)

Für eine Diagnose auf den jeweiligen Hosts:

| Symptom | Erste Prüfung |
| --- | --- |
| Indexer bildet kein Quorum | `journalctl -u wazuh-indexer -b`, zusätzlich das Clusterprotokoll unter `/var/log/wazuh-indexer/`. Stimmt die Dienstadresse und erreichen sich die Indexer auf TCP 9300? |
| Worker fehlt | Auf dem Master `/var/ossec/bin/cluster_control -l`, anschließend `/var/ossec/logs/cluster.log` auf beiden Hosts prüfen. |
| Agent ist verbunden, Alarme fehlen im Dashboard | Auf dem Manager `/var/ossec/logs/alerts/alerts.json` und `filebeat test output` prüfen. |
| Dashboard erreicht den Manager nicht | Vom Dashboard aus Dienstadresse und TCP 55000 prüfen. Die Manager-API protokolliert unter `/var/ossec/logs/api.log`. |
| Agent bleibt getrennt | Auf dem Agenten `grep '^status=' /var/ossec/var/run/wazuh-agentd.state` und `/var/ossec/logs/ossec.log` lesen. Auf dem Manager zeigt `/var/ossec/bin/agent_control -lc` die verbundenen Agenten. |

## Tests

```sh
python -m unittest discover -s wazuh/tests -v
ansible-playbook -i ../wazuh-inventory.ini wazuh/examples/wazuh.yml --syntax-check
ansible-playbook -i ../wazuh-inventory.ini wazuh/tests/verify.yml
```

Die lokalen Tests prüfen alle mitgelieferten Inventare, gerenderte Dienstkonfigurationen, Master und Worker, das CA-Vertrauen, die Wiederverwendung der Schlüssel sowie die Behandlung von Agentenkonflikten. Das Prüfplaybook liest auf den Zielhosts Indexer-Mitgliedschaft, Filebeat-Verbindung, Managerstatus, Dashboard-HTTPS und Agentenstatus. Im zentralen `--check`-Lauf prüft das Installationsplaybook die Platzierung. Die Dienstprüfungen erfordern eine laufende Installation.

Im Testnetz läßt sich auch der vollständige Weg eines Ereignisses prüfen. Der folgende Aufruf hängt auf genau einem Agenten eine als Test erkennbare SSH-Erfolgsmeldung an das standardmäßig überwachte Protokoll `/var/ossec/logs/active-responses.log` an. Er sucht anschließend im Alarmindex nach Agentenname und eindeutiger Testkennung und gibt Index und Regel-ID aus. Die Meldung und der erzeugte Alarm bleiben zur Nachprüfung erhalten.

```sh
ansible-playbook -i ../wazuh-inventory.ini wazuh/tests/event.yml --limit hv01
```

### Geprüfter Stand vom 20. November 2026

| Prüfung | Beobachtung |
| --- | --- |
| Ansible 2.19.15 | Playbook-Syntax für alle drei Inventare geprüft, zusätzlich sämtliche Taskdateien statisch importiert. Acht automatisierte Regressionstests bestanden. |
| Drei Indexer aus dem originalen amd64-Paket | Drei getrennte Prozesse mit eigenen Datenverzeichnissen, Adressen und Zertifikaten meldeten an allen Endpunkten drei Mitglieder und `green`. Nach Neustart mit vorhandener Datenbank und anschließendem Ausfall eines Knotens blieb das Quorum mit zwei Mitgliedern erreichbar (`yellow`). |
| Ein-Host-Inventar | Für `wazuh01` wurden die drei Dienstkonfigurationen gerendert. Drei parallele TLS-Testlistener auf derselben IP lieferten die jeweilige Komponentenidentität und bestanden die Hostnamenprüfung. In einer Debian-13-VM erreichte der echte Indexer die authentifizierte Mitgliedschaftsprüfung. Während der Paketinstallation des Dashboards wurde der VM-Prozeß durch die Testumgebung beendet. Der gemeinsame Betrieb aller drei Dienste in dieser VM ist damit offen. |
| Manager-Master und -Worker | Wazuhs eigener Konfigurationsparser akzeptierte beide gerenderten Konfigurationen und erkannte die jeweilige Rolle und die Adresse des Masters. Synchronisation und Agentenbetrieb an einem laufenden Worker wurden nicht praktisch geprüft. |
| Filebeat und Dashboard | Filebeat erreichte alle drei Indexer mit geprüfter TLS-Kette. Ein Testalarm erschien im Alarmindex. Das Dashboard meldete nach Anmeldung HTTP 200 und `green`. Der gehärtete Plugin-Client akzeptierte die eigene CA und wies eine fremde CA und einen falschen Hostnamen zurück. Der Wazuh-Plugin-Client authentifizierte sich am separaten Manager und erhielt für `GET /manager/status` HTTP 200. |
| Separater Linux-Agent und Manager | Auf zwei Debian-13-VMs (amd64) registrierte Ansible `hv01` über den Master. Der Manager führte ihn als ID 001 und `Active`. Das mitgelieferte Ereignis-Playbook verfolgte die synthetische SSH-Anmeldung über Agent, Manager und Filebeat bis zur Regel 5715 in `wazuh-alerts-4.x-2026.11.20`. Der zweite Agentenlauf ergab `changed=0`. Ein weiterer markierter Alarm erreichte anschließend denselben Index. |

Der Prüfstand verwendete die signierten DEB-Pakete, einen lokalen APT-Spiegel und für die VM-Läufe CPU-Emulation. Die im Paket vorgeschriebenen 47.196 Eigentümer- und Modusoperationen des Managers wurden im langsamen emulierten Gast in einem Prozeß ausgeführt. Beim wiederholten API-Start konnte der Prüfstand das bereits geprüfte, unveränderte OpenAPI-Schema anhand seiner Prüfsumme wiederverwenden. Auf der Ein-Host-VM wurde die Security-Datenbank nach einem Timeout mit demselben Herstellerwerkzeug vom Controller über einen SSH-Tunnel initialisiert. Auf den Zielsystemen verwendet die Rolle den regulären APT-Installationsweg und initialisiert den Indexer lokal. Der verteilte Funktionstest kombinierte zwei systemd-VMs mit eigenständigen Indexer- und Dashboard-Prozessen aus den Originalpaketen.

Die Einrichtung orientiert sich an den komponentenweisen Paketinstallationen von Wazuh. Filebeat-Modul, Indexvorlage und der Wazuh-APT-Schlüssel liegen der Rolle bei. [Indexer](https://documentation.wazuh.com/current/installation-guide/wazuh-indexer/step-by-step.html) · [Server](https://documentation.wazuh.com/current/installation-guide/wazuh-server/step-by-step.html) · [Dashboard](https://documentation.wazuh.com/current/installation-guide/wazuh-dashboard/step-by-step.html)
