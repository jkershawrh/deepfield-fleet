from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_open_shift_resources_use_the_deepfield_fleet_identity():
    documents = list(
        yaml.safe_load_all(
            (ROOT / "deploy" / "deployment.yaml").read_text(encoding="utf-8")
        )
    )
    resources = {
        (document["kind"], document["metadata"]["name"]): document
        for document in documents
        if document
    }
    deployment = resources[("Deployment", "deepfield-fleet")]
    service = resources[("Service", "deepfield-fleet")]
    resources[("Route", "deepfield-fleet")]

    assert deployment["spec"]["selector"]["matchLabels"]["app"] == "deepfield-fleet"
    assert service["spec"]["selector"]["app"] == "deepfield-fleet"


def test_installer_requires_and_supplies_gcl_delivery_scope():
    makefile = (ROOT / "deploy" / "Makefile").read_text(encoding="utf-8")
    required = {
        "GCL_EVENT_SINK_URL",
        "GCL_EVENT_SINK_TOKEN",
        "DEEPFIELD_TENANT",
        "DEEPFIELD_ZONE",
        "DEEPFIELD_CLUSTER",
        "DEEPFIELD_NAMESPACE",
    }
    for name in required:
        assert f'--from-literal={name}=' in makefile
        assert f'test -n "$({name})"' in makefile


def test_verifier_targets_deployed_identity():
    verifier = (ROOT / "deploy" / "verify.sh").read_text(encoding="utf-8")
    assert "oc get route deepfield-fleet" in verifier
    assert "-l app=deepfield-fleet" in verifier
    assert "oc get deployment deepfield-fleet" in verifier
