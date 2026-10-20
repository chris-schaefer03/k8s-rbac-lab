.PHONY: up test down

up:
	kind create cluster --config kind-config.yaml
	kubectl wait --for=condition=Ready node --all --timeout=120s
	kubectl apply -f manifests/
	kubectl rollout status deployment/nginx -n team-a --timeout=120s

test:
	./scripts/test-rbac.sh

down:
	kind delete cluster --name rbac-lab
