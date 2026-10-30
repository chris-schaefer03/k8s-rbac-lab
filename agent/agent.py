"""Minimal agent: uses the Kubernetes API with the permissions of its ServiceAccount."""
from kubernetes import client, config
from kubernetes.client.rest import ApiException

NAMESPACE = "team-a"


def try_action(description, action):
    """Runs an API action and reports whether RBAC allowed it."""
    try:
        result = action()
        print(f"ALLOWED  {description}")
        return result
    except ApiException as e:
        if e.status == 403:
            print(f"DENIED   {description} (403 Forbidden)")
        else:
            print(f"ERROR    {description} (HTTP {e.status})")
        return None


def main():
    # Reads the ServiceAccount token that Kubernetes mounts into the pod automatically
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    print("Agent running as ServiceAccount team-a/pod-reader\n")

    pods = try_action("List pods in team-a",
                      lambda: v1.list_namespaced_pod(NAMESPACE))
    if pods:
        for pod in pods.items:
            print(f"         - {pod.metadata.name} ({pod.status.phase})")

    target = pods.items[0].metadata.name if pods and pods.items else "nginx"
    try_action(f"Delete pod {target} (dry run)",
               lambda: v1.delete_namespaced_pod(target, NAMESPACE, dry_run="All"))

    try_action("List secrets in team-a",
               lambda: v1.list_namespaced_secret(NAMESPACE))

    try_action("List pods in default",
               lambda: v1.list_namespaced_pod("default"))


if __name__ == "__main__":
    main()
