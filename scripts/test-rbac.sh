# Prüft die RBAC-Rechte des ServiceAccounts team-a/pod-reader.
# Exit-Code 0 = alle Tests bestanden, 1 = mindestens einer fehlgeschlagen.

SA="system:serviceaccount:team-a:pod-reader"
PASS=0
FAIL=0

check() {
  expected="$1"
  description="$2"
  shift 2
  actual=$(kubectl auth can-i "$@" --as="$SA" 2>/dev/null)

  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS  $description (erwartet: $expected, ist: $actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $description (erwartet: $expected, ist: $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "RBAC-Tests für $SA"
echo
echo "Erlaubt:"
check yes "Pods lesen in team-a"            get    pods        -n team-a
check yes "Pods auflisten in team-a"        list   pods        -n team-a
check yes "Pods beobachten in team-a"       watch  pods        -n team-a
echo
echo "Verboten:"
check no  "Pods löschen in team-a"          delete pods        -n team-a
check no  "Pods erstellen in team-a"        create pods        -n team-a
check no  "Pods lesen in default"           get    pods        -n default
check no  "Pods lesen in kube-system"       get    pods        -n kube-system
check no  "Secrets lesen in team-a"         get    secrets     -n team-a
check no  "Deployments ändern in team-a"    patch  deployments -n team-a
check no  "Pod-Logs lesen in team-a"        get    pods --subresource=log  -n team-a
check no  "In Pods exec'en in team-a"       create pods --subresource=exec -n team-a
check no  "RoleBindings anlegen in team-a"  create rolebindings -n team-a

echo
echo "Ergebnis: $PASS bestanden, $FAIL fehlgeschlagen"
[[ $FAIL -eq 0 ]]
