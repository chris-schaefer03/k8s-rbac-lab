#!/usr/bin/env python3
"""Checks the RBAC permissions of the ServiceAccount team-a/pod-reader.

For every case, the script sends a SubjectAccessReview to the API server:
"May this identity perform this action?" `kubectl auth can-i --as` asks the
same question through a SelfSubjectAccessReview with impersonation. Here,
every field - including subresource and API group - is set explicitly
instead of being parsed from a string like "pods/log".

Exit code 0 = all tests passed, 1 = at least one test failed.
"""
import sys
from dataclasses import dataclass

from kubernetes import client, config

SA = "system:serviceaccount:team-a:pod-reader"
# kubectl --as adds these groups automatically for a ServiceAccount;
# a SubjectAccessReview does not, so they are listed explicitly.
GROUPS = ["system:serviceaccounts", "system:serviceaccounts:team-a", "system:authenticated"]


@dataclass
class Case:
    expected: bool
    description: str
    verb: str
    resource: str
    namespace: str
    subresource: str = ""
    group: str = ""  # "" = core API (pods, secrets); deployments live in "apps"


CASES = [
    Case(True,  "Get pods in team-a",            "get",    "pods",         "team-a"),
    Case(True,  "List pods in team-a",           "list",   "pods",         "team-a"),
    Case(True,  "Watch pods in team-a",          "watch",  "pods",         "team-a"),
    Case(False, "Delete pods in team-a",         "delete", "pods",         "team-a"),
    Case(False, "Create pods in team-a",         "create", "pods",         "team-a"),
    Case(False, "Get pods in default",           "get",    "pods",         "default"),
    Case(False, "Get pods in kube-system",       "get",    "pods",         "kube-system"),
    Case(False, "Get secrets in team-a",         "get",    "secrets",      "team-a"),
    Case(False, "Patch deployments in team-a",   "patch",  "deployments",  "team-a", group="apps"),
    Case(False, "Read pod logs in team-a",       "get",    "pods",         "team-a", subresource="log"),
    Case(False, "Exec into pods in team-a",      "create", "pods",         "team-a", subresource="exec"),
    Case(False, "Create rolebindings in team-a", "create", "rolebindings", "team-a",
         group="rbac.authorization.k8s.io"),
]


def is_allowed(api, case):
    """Asks the API server whether the ServiceAccount may perform this action."""
    review = client.V1SubjectAccessReview(
        spec=client.V1SubjectAccessReviewSpec(
            user=SA,
            groups=GROUPS,
            resource_attributes=client.V1ResourceAttributes(
                namespace=case.namespace,
                verb=case.verb,
                resource=case.resource,
                subresource=case.subresource or None,
                group=case.group,
            ),
        )
    )
    return api.create_subject_access_review(review).status.allowed


def yes_no(value):
    return "yes" if value else "no"


def main():
    config.load_kube_config()  # uses the same cluster as kubectl
    api = client.AuthorizationV1Api()
    passed = failed = 0

    print(f"RBAC tests for {SA}")
    for title, expected in (("Allowed:", True), ("Denied:", False)):
        print()
        print(title)
        for case in CASES:
            if case.expected != expected:
                continue
            actual = is_allowed(api, case)
            if actual == case.expected:
                result = "PASS"
                passed += 1
            else:
                result = "FAIL"
                failed += 1
            print(f"  {result}  {case.description} "
                  f"(expected: {yes_no(case.expected)}, actual: {yes_no(actual)})")

    print()
    print(f"Result: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
