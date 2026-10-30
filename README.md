# Kubernetes RBAC Lab: Least Privilege for AI Agents

[![RBAC tests](https://github.com/chris-schaefer03/k8s-rbac-lab/actions/workflows/rbac-tests.yml/badge.svg)](https://github.com/chris-schaefer03/k8s-rbac-lab/actions/workflows/rbac-tests.yml)

A local Kubernetes lab that shows how to give a program in a cluster exactly the permissions it needs. The ServiceAccount `pod-reader` may read pods in the namespace `team-a` – and nothing else. A test script and a Python agent verify that these boundaries hold.

## Motivation

Autonomous programs such as AI agents access infrastructure with their own identity. If such an agent is compromised or manipulated (e.g. through prompt injection), its permissions define how much damage it can do. In Kubernetes, this identity is a **ServiceAccount**, and **RBAC** defines what it may do.

## Structure

| File | Purpose |
| --- | --- |
| `kind-config.yaml` | Local cluster with one node |
| `manifests/00-namespace.yaml` | Namespace `team-a` |
| `manifests/01-nginx-deployment.yaml` | Sample workload (nginx) |
| `manifests/02-serviceaccount.yaml` | Identity `pod-reader` |
| `manifests/03-role.yaml` | Permissions: only `get`, `list`, `watch` on pods |
| `manifests/04-rolebinding.yaml` | Binds the role to the ServiceAccount |
| `manifests/05-agent-pod.yaml` | Python agent running as `pod-reader` |
| `agent/` | Agent code and Dockerfile |
| `scripts/test-rbac.sh` | Checks 12 cases with `kubectl auth can-i` |
| `audit/audit-policy.yaml` | Audit policy: logs every request of `pod-reader` (metadata only) |
| `scripts/show-audit.sh` | Shows the audit log entries of `pod-reader` |
| `Makefile` | Setup, tests, agent, teardown |
| `.github/workflows/rbac-tests.yml` | CI: runs `make up`, `make test` and `make agent` on every push |

## Usage

Requirements: Docker, [kind](https://kind.sigs.k8s.io/), kubectl, make.

```bash
make up      # create cluster, build and load agent image, apply manifests
make test    # check RBAC rules (exit code 0 = all correct)
make agent   # run the agent and show its output
make audit   # show the agent's requests from the API server audit log
make down    # delete the cluster
```

The same steps run automatically in GitHub Actions on every push.

## Results

### Agent

The agent reads the token that Kubernetes mounts into its pod and calls the API directly:

```
Agent running as ServiceAccount team-a/pod-reader

ALLOWED  List pods in team-a
         - agent (Running)
         - nginx-7f7f9596db-2qx8d (Running)
DENIED   Delete pod agent (dry run) (403 Forbidden)
DENIED   List secrets in team-a (403 Forbidden)
DENIED   List pods in default (403 Forbidden)
```

### Audit log

The API server logs every request of `pod-reader`, including the denied ones (output of one agent run):

```
ALLOWED  200  list pods in team-a
DENIED   403  delete pods in team-a
DENIED   403  list secrets in team-a
DENIED   403  list pods in default
```

The `kubectl auth can-i` checks do not appear here: they only ask whether an action *would* be allowed, while the audit log records real attempts.

### Test script

All 12 cases pass: 3 allowed, 9 denied. `kubectl auth can-i` uses impersonation to ask whether an action *would* be allowed; the agent additionally makes four real API calls with its own token.

<details>
<summary>Show full output</summary>

```
RBAC tests for system:serviceaccount:team-a:pod-reader

Allowed:
  PASS  Get pods in team-a (expected: yes, actual: yes)
  PASS  List pods in team-a (expected: yes, actual: yes)
  PASS  Watch pods in team-a (expected: yes, actual: yes)

Denied:
  PASS  Delete pods in team-a (expected: no, actual: no)
  PASS  Create pods in team-a (expected: no, actual: no)
  PASS  Get pods in default (expected: no, actual: no)
  PASS  Get pods in kube-system (expected: no, actual: no)
  PASS  Get secrets in team-a (expected: no, actual: no)
  PASS  Patch deployments in team-a (expected: no, actual: no)
  PASS  Read pod logs in team-a (expected: no, actual: no)
  PASS  Exec into pods in team-a (expected: no, actual: no)
  PASS  Create rolebindings in team-a (expected: no, actual: no)

Result: 12 passed, 0 failed
```

</details>

## Design decisions

- **Role instead of ClusterRole:** permissions apply only in `team-a`. A compromised agent cannot reach other namespaces.
- **Read-only verbs:** `get`, `list`, `watch` – no `create`, `update` or `delete`.
- **Subresources excluded:** `pods/log` and `pods/exec` are separate resources. `exec` effectively means code execution inside the container.
- **No rights on RoleBindings:** otherwise the identity could grant itself more permissions.
- **Dry run for deletion:** the agent uses `dry_run` so that nothing is deleted even if the RBAC setup were wrong.

## Threat model

**Assets:** secrets in the namespace, running workloads, workloads in other namespaces, and the RBAC configuration itself.

**Assumptions:** the cluster admin and the API server are trusted. The agent is treated as potentially compromised – for example through prompt injection or a stolen token.

| Attacker goal | Attack path | Control | Status |
| --- | --- | --- | --- |
| Steal credentials | Agent reads secrets | Role only covers `pods` | ✅ blocked (403) |
| Disrupt workloads | Agent deletes or modifies pods and deployments | Only `get`, `list`, `watch` | ✅ blocked (403) |
| Run code in a container | `pods/exec` | Subresource not granted | ✅ blocked |
| Take over another identity | Create a pod that uses a more privileged ServiceAccount | No `create` on pods | ✅ blocked |
| Move laterally | Access other namespaces | Role instead of ClusterRole | ✅ blocked (403) |
| Escalate own permissions | Create a RoleBinding | No rights on RBAC objects | ✅ blocked |
| Read sensitive data from pods | Pod specs include environment variables | Reading pods is allowed | ⚠️ open |
| Use a stolen token | Copy the token out of the pod and use it elsewhere | Token expires after about one hour | ⚠️ partial |
| Stay unnoticed | Attempts are not logged | Audit policy logs every request of `pod-reader` | ✅ logged |

## Lesson learned: security tests can be wrong too

`kubectl auth can-i get pods/log` initially returned "yes", because kubectl interprets `pods/log` as *a pod named "log"*. The exec test passed, but for the wrong reason. Subresources have to be checked with `--subresource=log`.

## Limits of RBAC

RBAC only answers: *may this identity perform this action on this resource type?* For autonomous agents, several things are missing:

- **No task context:** RBAC does not know *which task* an agent is working on. Read access applies at all times, not only when the current task requires it.
- **No per-task time limits:** permissions apply as long as the binding exists.
- **No control over data once read:** what the agent does with the information is outside RBAC.
- **Coarse granularity:** permissions apply to all pods in a namespace, not to individual pods.
