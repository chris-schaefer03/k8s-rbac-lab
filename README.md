# Kubernetes RBAC Lab: Least Privilege für Workload-Identitäten

![RBAC tests](https://github.com/chris-schaefer03/k8s-rbac-lab/actions/workflows/rbac-tests.yml/badge.svg)

Ein lokales Kubernetes-Projekt, das zeigt, wie man einem Programm im Cluster nur genau die Rechte gibt, die es braucht. Ein ServiceAccount `pod-reader` darf Pods im Namespace `team-a` lesen – und sonst nichts. Ein Testskript und ein Python-Agent prüfen, dass diese Grenzen halten.

## Motivation

Autonome Programme wie KI-Agenten greifen mit eigener Identität auf Infrastruktur zu. Wird so ein Agent kompromittiert oder manipuliert (z. B. durch Prompt Injection), entscheidet sein Rechteumfang über den Schaden. In Kubernetes ist diese Identität ein **ServiceAccount**, und was er darf, regelt **RBAC**.

## Aufbau

| Datei | Inhalt |
| --- | --- |
| `kind-config.yaml` | Lokaler Cluster mit einem Node |
| `manifests/00-namespace.yaml` | Namespace `team-a` |
| `manifests/01-nginx-deployment.yaml` | Beispiel-Workload (nginx) |
| `manifests/02-serviceaccount.yaml` | Identität `pod-reader` |
| `manifests/03-role.yaml` | Rechte: nur `get`, `list`, `watch` auf Pods |
| `manifests/04-rolebinding.yaml` | Verbindet Role und ServiceAccount |
| `manifests/05-agent-pod.yaml` | Python-Agent, läuft als `pod-reader` |
| `agent/` | Code und Dockerfile des Agenten |
| `scripts/test-rbac.sh` | Prüft 12 Fälle mit `kubectl auth can-i` |
| `Makefile` | Aufbau, Tests, Agent, Abbau |

## Ausführen

Voraussetzungen: Docker, [kind](https://kind.sigs.k8s.io/), kubectl, make.

```bash
make up      # Cluster erstellen, Agent-Image bauen und laden, Manifeste anwenden
make test    # RBAC-Regeln prüfen (Exit-Code 0 = alles korrekt)
make agent   # Agent starten und Ausgabe anzeigen
make down    # Cluster löschen
```

## Ergebnisse

### Agent

Der Agent nutzt den Token, den Kubernetes automatisch in seinen Pod legt, und ruft die API direkt auf:

```
Agent läuft als ServiceAccount team-a/pod-reader

ERLAUBT   Pods auflisten in team-a
          - agent (Running)
          - nginx-7f7f9596db-24wzf (Running)
VERBOTEN  Pod agent löschen (Probelauf) (403 Forbidden)
VERBOTEN  Secrets lesen in team-a (403 Forbidden)
VERBOTEN  Pods auflisten in default (403 Forbidden)
```

### Testskript

Alle 12 Fälle bestehen: 3 erlaubte Aktionen, 9 verbotene. `kubectl auth can-i` fragt per Impersonation, ob eine Aktion erlaubt *wäre*; der Agent bestätigt dasselbe mit echten API-Aufrufen.

<details>
<summary>Vollständige Ausgabe anzeigen</summary>

```
RBAC-Tests für system:serviceaccount:team-a:pod-reader

Erlaubt:
  PASS  Pods lesen in team-a (erwartet: yes, ist: yes)
  PASS  Pods auflisten in team-a (erwartet: yes, ist: yes)
  PASS  Pods beobachten in team-a (erwartet: yes, ist: yes)

Verboten:
  PASS  Pods löschen in team-a (erwartet: no, ist: no)
  PASS  Pods erstellen in team-a (erwartet: no, ist: no)
  PASS  Pods lesen in default (erwartet: no, ist: no)
  PASS  Pods lesen in kube-system (erwartet: no, ist: no)
  PASS  Secrets lesen in team-a (erwartet: no, ist: no)
  PASS  Deployments ändern in team-a (erwartet: no, ist: no)
  PASS  Pod-Logs lesen in team-a (erwartet: no, ist: no)
  PASS  In Pods exec'en in team-a (erwartet: no, ist: no)
  PASS  RoleBindings anlegen in team-a (erwartet: no, ist: no)

Ergebnis: 12 bestanden, 0 fehlgeschlagen
```

</details>

## Designentscheidungen

- **Role statt ClusterRole:** Die Rechte gelten nur in `team-a`. Ein kompromittierter Agent kommt nicht in andere Namespaces.
- **Nur lesende Verben:** `get`, `list`, `watch` – kein `create`, `update`, `delete`.
- **Subressourcen ausgeschlossen:** `pods/log` und `pods/exec` sind eigene Ressourcen. `exec` bedeutet faktisch Codeausführung im Container.
- **Keine Rechte auf RoleBindings:** Sonst könnte sich die Identität selbst weitere Rechte geben.
- **Probelauf beim Löschen:** Der Agent nutzt `dry_run`, damit auch bei einer Fehlkonfiguration nichts gelöscht wird.

## Erkenntnis: Auch Sicherheitstests können falsch sein

`kubectl auth can-i get pods/log` lieferte zunächst „yes“, weil kubectl `pods/log` als *Pod mit dem Namen „log“* interpretiert. Der exec-Test war grün, aber aus dem falschen Grund. Subressourcen prüft man korrekt mit `--subresource=log`.

## Grenzen von RBAC

RBAC beantwortet nur: *Darf diese Identität diese Aktion auf diesem Ressourcentyp?* Für autonome Agenten fehlt dabei einiges:

- **Kein Kontext:** RBAC weiß nicht, *für welche Aufgabe* ein Agent handelt. Leserechte gelten immer, nicht nur wenn der aktuelle Auftrag sie verlangt.
- **Keine zeitliche Begrenzung pro Aufgabe:** Rechte gelten, solange das Binding existiert.
- **Keine Kontrolle über die Daten danach:** Was der Agent mit gelesenen Informationen macht, liegt außerhalb von RBAC.
- **Grobe Granularität:** Rechte gelten für alle Pods eines Namespace, nicht für einzelne Pods.

