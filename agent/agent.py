"""Minimaler Agent: nutzt die Kubernetes-API mit den Rechten seines ServiceAccounts."""
from kubernetes import client, config
from kubernetes.client.rest import ApiException

NAMESPACE = "team-a"


def try_action(description, action):
    """Führt eine API-Aktion aus und meldet, ob RBAC sie erlaubt hat."""
    try:
        result = action()
        print(f"ERLAUBT   {description}")
        return result
    except ApiException as e:
        if e.status == 403:
            print(f"VERBOTEN  {description} (403 Forbidden)")
        else:
            print(f"FEHLER    {description} (HTTP {e.status})")
        return None


def main():
    # Liest automatisch den Token des ServiceAccounts, den Kubernetes in den Pod legt
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    print("Agent läuft als ServiceAccount team-a/pod-reader\n")

    pods = try_action("Pods auflisten in team-a",
                      lambda: v1.list_namespaced_pod(NAMESPACE))
    if pods:
        for pod in pods.items:
            print(f"          - {pod.metadata.name} ({pod.status.phase})")

    target = pods.items[0].metadata.name if pods and pods.items else "nginx"
    try_action(f"Pod {target} löschen (Probelauf)",
               lambda: v1.delete_namespaced_pod(target, NAMESPACE, dry_run="All"))

    try_action("Secrets lesen in team-a",
               lambda: v1.list_namespaced_secret(NAMESPACE))

    try_action("Pods auflisten in default",
               lambda: v1.list_namespaced_pod("default"))


if __name__ == "__main__":
    main()
