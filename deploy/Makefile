.PHONY: install uninstall

NAMESPACE ?= deepfield-multimodal
LITELLM_API_BASE ?=
LITELLM_API_KEY ?=

install:
	@echo "Deploying DeepField Multimodal to $(NAMESPACE)"
	oc create secret generic deepfield-oauth-secret \
		--from-literal=client-secret=$$(openssl rand -hex 32) \
		--from-literal=session_secret=$$(openssl rand -hex 32) \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	oc create secret generic deepfield-secrets \
		--from-literal=LITELLM_API_BASE=$(LITELLM_API_BASE) \
		--from-literal=LITELLM_API_KEY=$(LITELLM_API_KEY) \
		--from-literal=BOOTSTRAP_API_BASE=$(LITELLM_API_BASE) \
		--from-literal=BOOTSTRAP_API_KEY=$(LITELLM_API_KEY) \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	sed 's/namespace: deepfield-multimodal/namespace: $(NAMESPACE)/g; \
		s/name: deepfield-reader-binding/name: deepfield-reader-$(NAMESPACE)/g' \
		deployment.yaml | oc apply -f -

uninstall:
	@echo "Removing DeepField Multimodal from $(NAMESPACE)"
	sed 's/namespace: deepfield-multimodal/namespace: $(NAMESPACE)/g; \
		s/name: deepfield-reader-binding/name: deepfield-reader-$(NAMESPACE)/g' \
		deployment.yaml | oc delete --ignore-not-found -f -
	oc delete secret deepfield-oauth-secret deepfield-secrets \
		-n $(NAMESPACE) --ignore-not-found
