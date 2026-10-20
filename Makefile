.PHONY: up test agent down

up:
	kind create cluster --config kind-config.yaml
	kubectl wait --for=condition=Ready node --all --timeout=120s
	docker build -t rbac-agent:0.1 agent/
	kind load docker-image rbac-agent:0.1 --name rbac-lab
	kubectl apply -f manifests/
	kubectl rollout status deployment/nginx -n team-a --timeout=120s

test:
	./scripts/test-rbac.sh

agent:
	kubectl delete pod agent -n team-a --ignore-not-found
	kubectl apply -f manifests/05-agent-pod.yaml
	kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/agent -n team-a --timeout=120s
	kubectl logs agent -n team-a

down:
	kind delete cluster --name rbac-lab
