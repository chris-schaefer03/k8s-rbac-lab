#!/usr/bin/env bash
# Shows the API requests made by the ServiceAccount team-a/pod-reader,
# as recorded in the audit log of the API server.

NODE="rbac-lab-control-plane"
LOG="/var/log/kubernetes/kube-apiserver-audit.log"
SA="system:serviceaccount:team-a:pod-reader"

echo "Audit log entries for $SA"
echo
docker exec "$NODE" cat "$LOG" \
  | jq -r --arg sa "$SA" '
      select(.user.username == $sa)
      | (if .responseStatus.code < 400 then "ALLOWED" else "DENIED " end)
        + "  \(.responseStatus.code)  \(.verb) \(.objectRef.resource) in \(.objectRef.namespace)"'

# Fail if fewer than 3 denied requests were logged (e.g. audit logging not active)
DENIED=$(docker exec "$NODE" cat "$LOG" | jq -r --arg sa "$SA" 'select(.user.username == $sa and .responseStatus.code == 403) | .verb' | wc -l)
echo
echo "Denied requests: $DENIED"
[[ $DENIED -ge 3 ]]
