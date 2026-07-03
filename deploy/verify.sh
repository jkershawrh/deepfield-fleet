#!/bin/bash
# Deployment verification script — RED/GREEN rubric checker
# Usage: ./deploy/verify.sh

set +e

NAMESPACE="deepfield-multimodal"
ROUTE=$(oc get route deepfield-multimodal -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

if [ -z "$ROUTE" ]; then
  echo "✗ No route found. Is the app deployed?"
  exit 1
fi

URL="https://$ROUTE"
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
echo "  DeepField Multimodal — Deployment Rubric"
echo "  Route: $URL"
echo "═══════════════════════════════════════════"

echo ""
echo "INFRASTRUCTURE"
check "Pod running" "oc get pods -n $NAMESPACE -l app=deepfield-multimodal -o jsonpath='{.items[0].status.phase}' | grep -q Running"
check "Health check" "curl -sfk $URL/health | grep -q ok"
check "Frontend loads" "curl -sfk $URL/ | grep -q root"
check "Readiness passing" "oc get pods -n $NAMESPACE -l app=deepfield-multimodal -o jsonpath='{.items[0].status.conditions[?(@.type==\"Ready\")].status}' | grep -q True"

echo ""
echo "API ENDPOINTS"
check "Profiles endpoint" "curl -sfk $URL/api/v1/bootstrap/profiles | grep -q openshift"
check "Infrastructure endpoint" "curl -sfk $URL/api/v1/demo/infrastructure | grep -q agents"
check "Models endpoint" "curl -sfk $URL/api/v1/bootstrap/models | grep -q qwen"
check "Demo state endpoint" "curl -sfk $URL/api/v1/demo/state"

echo ""
echo "BOOTSTRAP LAB"
check "Profile apply" "curl -sfk -X POST $URL/api/v1/bootstrap/profiles/openshift-monitoring/apply | grep -q profile_applied"
check "Rubric endpoint" "curl -sfk $URL/api/v1/bootstrap/rubric | grep -q agents"

echo ""
echo "SECURITY"
check "No hardcoded secrets" "! oc get deployment deepfield-multimodal -n $NAMESPACE -o yaml | grep -q 'sk-'"
check "Secret ref exists" "oc get secret deepfield-secrets -n $NAMESPACE -o name | grep -q secret"

echo ""
echo "═══════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════"
echo ""

if [ $FAIL -gt 0 ]; then
  exit 1
fi
