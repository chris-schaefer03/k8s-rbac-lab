#!/usr/bin/env bash
# Checks the RBAC permissions of the ServiceAccount team-a/pod-reader.
# Exit code 0 = all tests passed, 1 = at least one test failed.

SA="system:serviceaccount:team-a:pod-reader"
PASS=0
FAIL=0

check() {
  expected="$1"
  description="$2"
  shift 2
  actual=$(kubectl auth can-i "$@" --as="$SA" 2>/dev/null)

  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS  $description (expected: $expected, actual: $actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $description (expected: $expected, actual: $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "RBAC tests for $SA"
echo
echo "Allowed:"
check yes "Get pods in team-a"              get    pods        -n team-a
check yes "List pods in team-a"             list   pods        -n team-a
check yes "Watch pods in team-a"            watch  pods        -n team-a
echo
echo "Denied:"
check no  "Delete pods in team-a"           delete pods        -n team-a
check no  "Create pods in team-a"           create pods        -n team-a
check no  "Get pods in default"             get    pods        -n default
check no  "Get pods in kube-system"         get    pods        -n kube-system
check no  "Get secrets in team-a"           get    secrets     -n team-a
check no  "Patch deployments in team-a"     patch  deployments -n team-a
check no  "Read pod logs in team-a"         get    pods --subresource=log  -n team-a
check no  "Exec into pods in team-a"        create pods --subresource=exec -n team-a
check no  "Create rolebindings in team-a"   create rolebindings -n team-a

echo
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
