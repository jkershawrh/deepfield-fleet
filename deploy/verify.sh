#!/bin/bash
# Deployment verification script — RED/GREEN rubric checker
# Usage: NAMESPACE=fleet-llm-d ./deploy/verify.sh

set +e

NAMESPACE="${NAMESPACE:-fleet-llm-d}"
ROUTE=$(oc get route deepfield-fleet -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -z "$ROUTE" ]; then
  echo "✗ No route found for deepfield-fleet in $NAMESPACE. Is the app deployed?"
  exit 1
fi

URL="https://$ROUTE"
TOKEN=$(oc whoami -t 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
  echo "✗ An OpenShift bearer token is required to verify the OAuth-protected route."
  exit 1
fi

route_get() {
  curl -sfk -H "Authorization: Bearer $TOKEN" "$1"
}

route_post() {
  curl -sfk -H "Authorization: Bearer $TOKEN" -X POST "$1"
}

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ $name"
    ((PASS++))
  else
    echo "  ✗ $name"
    ((FAIL++))
  fi
}

echo ""
echo "═══════════════════════════════════════════"
echo "  fleet-llm-d — Deployment Rubric"
echo "  Route: $URL"
echo "  Namespace: $NAMESPACE"
echo "═══════════════════════════════════════════"

echo ""
echo "INFRASTRUCTURE"
check "deepfield-fleet pod running" "oc get pods -n $NAMESPACE -l app=deepfield-fleet -o jsonpath='{.items[0].status.phase}' | grep -q Running"
check "fleet-controller pod running" "oc get pods -n $NAMESPACE -l app=fleet-controller -o jsonpath='{.items[0].status.phase}' | grep -q Running"
check "Health check" "route_get $URL/health | grep -q ok"
check "Readiness passing" "oc get pods -n $NAMESPACE -l app=deepfield-fleet -o jsonpath='{.items[0].status.conditions[?(@.type==\"Ready\")].status}' | grep -q True"

echo ""
echo "FLEET API"
check "Fleet health" "route_get $URL/api/v1/fleet/health | grep -q status"
check "Fleet cost" "route_get $URL/api/v1/fleet/cost | grep -q savings"
check "Fleet event profiles" "route_get $URL/api/v1/fleet/event-profiles | grep -q profiles"
check "Fleet forecast" "route_post $URL/api/v1/fleet/forecast | grep -q forecast"
check "Demo state" "route_get $URL/api/v1/demo/state"
check "Infrastructure" "route_get $URL/api/v1/demo/infrastructure | grep -q agents"

echo ""
echo "MOCK INFERENCE"
check "Mock inference pod running" "oc get pods -n $NAMESPACE -l app=mock-inference -o jsonpath='{.items[0].status.phase}' | grep -q Running"
check "Mock models endpoint" "curl -sfk http://mock-inference.$NAMESPACE.svc/v1/models | grep -q granite"

echo ""
echo "SECURITY"
check "No hardcoded secrets" "! oc get deployment deepfield-fleet -n $NAMESPACE -o yaml | grep -q 'sk-'"
check "Pre-commit hooks exist" "test -f .pre-commit-config.yaml"

echo ""
echo "═══════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════"
echo ""

if [ $FAIL -gt 0 ]; then
  exit 1
fi
