.PHONY: check-config install uninstall

NAMESPACE ?= fleet-llm-d
LITELLM_API_BASE ?=
LITELLM_API_KEY ?=
GCL_EVENT_SINK_URL ?= http://gcl-app.governed-cognitive-loop.svc:8000/api/v1/events/deepfield
GCL_EVENT_SINK_TOKEN ?=
DEEPFIELD_TENANT ?=
DEEPFIELD_ZONE ?=
DEEPFIELD_CLUSTER ?=
DEEPFIELD_NAMESPACE ?= $(NAMESPACE)

check-config:
	@test -n "$(GCL_EVENT_SINK_URL)" || { echo "GCL_EVENT_SINK_URL is required"; exit 1; }
	@test -n "$(GCL_EVENT_SINK_TOKEN)" || { echo "GCL_EVENT_SINK_TOKEN is required"; exit 1; }
	@test -n "$(DEEPFIELD_TENANT)" || { echo "DEEPFIELD_TENANT is required"; exit 1; }
	@test -n "$(DEEPFIELD_ZONE)" || { echo "DEEPFIELD_ZONE is required"; exit 1; }
	@test -n "$(DEEPFIELD_CLUSTER)" || { echo "DEEPFIELD_CLUSTER is required"; exit 1; }
	@test -n "$(DEEPFIELD_NAMESPACE)" || { echo "DEEPFIELD_NAMESPACE is required"; exit 1; }

install: check-config
	@echo "Deploying deepfield-fleet to $(NAMESPACE)"
	@oc create secret generic deepfield-oauth-secret \
		--from-literal=client-secret=$$(openssl rand -hex 32) \
		--from-literal=session_secret=$$(openssl rand -hex 32) \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	@oc create secret generic deepfield-secrets \
		--from-literal=LITELLM_API_BASE='$(LITELLM_API_BASE)' \
		--from-literal=LITELLM_API_KEY='$(LITELLM_API_KEY)' \
		--from-literal=BOOTSTRAP_API_BASE='$(LITELLM_API_BASE)' \
		--from-literal=BOOTSTRAP_API_KEY='$(LITELLM_API_KEY)' \
		--from-literal=GCL_EVENT_SINK_URL='$(GCL_EVENT_SINK_URL)' \
		--from-literal=GCL_EVENT_SINK_TOKEN='$(GCL_EVENT_SINK_TOKEN)' \
		--from-literal=DEEPFIELD_TENANT='$(DEEPFIELD_TENANT)' \
		--from-literal=DEEPFIELD_ZONE='$(DEEPFIELD_ZONE)' \
		--from-literal=DEEPFIELD_CLUSTER='$(DEEPFIELD_CLUSTER)' \
		--from-literal=DEEPFIELD_NAMESPACE='$(DEEPFIELD_NAMESPACE)' \
		-n $(NAMESPACE) --dry-run=client -o yaml | oc apply -f -
	sed 's/namespace: deepfield-fleet/namespace: $(NAMESPACE)/g; \
		s/name: deepfield-reader-binding/name: deepfield-reader-$(NAMESPACE)/g' \
		deployment.yaml | oc apply -f -

uninstall:
	@echo "Removing deepfield-fleet from $(NAMESPACE)"
	sed 's/namespace: deepfield-fleet/namespace: $(NAMESPACE)/g; \
		s/name: deepfield-reader-binding/name: deepfield-reader-$(NAMESPACE)/g' \
		deployment.yaml | oc delete --ignore-not-found -f -
	oc delete secret deepfield-oauth-secret deepfield-secrets \
		-n $(NAMESPACE) --ignore-not-found
