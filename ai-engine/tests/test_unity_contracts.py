"""Cross-client parity tests: Unity C# contracts, UI Toolkit assets, and EditMode tests."""

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient
from holoassist.api.app import local_app

UNITY_ROOT = Path("unity-app")
UNITY_ASSETS_DIR = UNITY_ROOT / "Assets"
UNITY_SCRIPTS_DIR = UNITY_ASSETS_DIR / "Scripts"
UNITY_RUNTIME_DIR = UNITY_SCRIPTS_DIR / "Runtime"
UNITY_EDITMODE_DIR = UNITY_ASSETS_DIR / "Tests" / "EditMode"
CONTRACTS_CS = UNITY_RUNTIME_DIR / "HoloAssistContracts.cs"
API_CLIENT_CS = UNITY_SCRIPTS_DIR / "HoloAssistApiClient.cs"
UI_TOOLKIT_VIEW_CS = UNITY_RUNTIME_DIR / "HoloAssistUiToolkitView.cs"
USS_FILE = UNITY_ASSETS_DIR / "Resources" / "HoloAssistWorkstation.uss"
TSS_FILE = UNITY_ASSETS_DIR / "Resources" / "HoloAssistTheme.tss"
MANIFEST_JSON = UNITY_ROOT / "Packages" / "manifest.json"


def _extract_cs_class_fields(cs_source: str, class_name: str) -> set[str]:
    pattern = rf"public\s+class\s+{class_name}\s*\{{(.*?)\n\s*\}}"
    match = re.search(pattern, cs_source, flags=re.DOTALL)
    assert match is not None, f"Missing C# contract class: {class_name}"
    body = match.group(1)
    return set(re.findall(r"public\s+[\w<>]+\s+(\w+)\s*(?:=|;)", body))


def test_unity_cs_contracts_cover_live_api_payload_fields():
    cs_source = CONTRACTS_CS.read_text(encoding="utf-8")

    with TestClient(local_app()) as client:
        health_json = client.get("/health").json()
        ready_json = client.get("/ready").json()
        safety_req = {
            "schema_version": "1.0",
            "review_id": "parity-check",
            "analysis_request_id": "synthetic-analysis-demo-1",
            "tracking_status": "tracked",
            "steps": [
                {
                    "step_id": "step-1",
                    "instruction_id": "demo-information",
                    "part_id": "demo-label",
                }
            ],
        }
        safety_json = client.post("/v1/demo/safety/evaluate", json=safety_req).json()
        vision_matched_json = client.get("/v1/demo/vision/warped").json()
        vision_rejected_json = client.get("/v1/demo/vision/unknown").json()
        sensor_json = client.get("/v1/demo/sensors/current").json()
        diag_json = client.get("/v1/demo/diagnostic/complete").json()
        spatial_json = client.get("/v1/demo/spatial/information").json()
        export_json = client.get(
            "/v1/demo/report?safety=information&sensor=current&diagnostic=complete"
        ).json()

    assert vision_matched_json["status"] == "matched"
    assert vision_matched_json["equipment_id"] == "synthetic-rig"
    assert vision_matched_json["calibrated_probabilities"] is False
    assert vision_matched_json["guidance_allowed"] is False
    assert len(vision_matched_json["projected_corners"]) == 4

    assert vision_rejected_json["status"] in ("low_confidence", "unknown")
    assert vision_rejected_json["equipment_id"] is None
    assert vision_rejected_json["projected_corners"] == []

    assert set(vision_matched_json.keys()) <= _extract_cs_class_fields(
        cs_source, "VisionDemoPayload"
    )
    assert set(vision_matched_json["projected_corners"][0].keys()) <= _extract_cs_class_fields(
        cs_source, "VisionCorner2D"
    )

    assert set(health_json.keys()) <= _extract_cs_class_fields(cs_source, "HealthResponse")
    assert set(ready_json.keys()) <= _extract_cs_class_fields(cs_source, "ReadinessResponse")
    assert set(safety_req.keys()) <= _extract_cs_class_fields(cs_source, "SafetyRequest")
    assert set(safety_json.keys()) <= _extract_cs_class_fields(cs_source, "SafetyReport")
    assert set(safety_json["steps"][0].keys()) <= _extract_cs_class_fields(
        cs_source, "StepResponse"
    )
    assert set(safety_json["steps"][0]["citations"][0].keys()) <= _extract_cs_class_fields(
        cs_source, "Citation"
    )
    assert set(sensor_json.keys()) <= _extract_cs_class_fields(cs_source, "SensorDemoPayload")
    assert set(diag_json.keys()) <= _extract_cs_class_fields(cs_source, "DiagnosticReport")
    assert set(spatial_json.keys()) <= _extract_cs_class_fields(
        cs_source, "SpatialProjectionReport"
    )
    assert set(spatial_json["cards"][0].keys()) <= _extract_cs_class_fields(
        cs_source, "SpatialCardProjection"
    )
    assert set(spatial_json["cards"][0]["pose"].keys()) <= _extract_cs_class_fields(
        cs_source, "AnchorPose3D"
    )

    saved_bench = json.loads(
        Path("docs/examples/synthetic-benchmark-report.json").read_text(encoding="utf-8")
    )
    bench_keys = set(saved_bench.keys()) - {"fixture_digests"}
    assert bench_keys <= _extract_cs_class_fields(cs_source, "SyntheticBenchmarkReport")
    assert set(saved_bench["vision"].keys()) <= _extract_cs_class_fields(
        cs_source, "VisionBenchmarkSummary"
    )
    assert set(saved_bench["rag"].keys()) <= _extract_cs_class_fields(
        cs_source, "RagBenchmarkSummary"
    )
    assert set(saved_bench["diagnostic"].keys()) <= _extract_cs_class_fields(
        cs_source, "DiagnosticBenchmarkSummary"
    )
    assert set(saved_bench["safety_spatial"].keys()) <= _extract_cs_class_fields(
        cs_source, "SafetySpatialBenchmarkSummary"
    )

    envelope_keys = {
        "schema_version",
        "export_id",
        "generated_utc",
        "scope",
        "independent_sections",
        "guidance_allowed",
    }
    assert envelope_keys <= set(export_json.keys())
    assert envelope_keys <= _extract_cs_class_fields(cs_source, "DemoExportEnvelope")


def test_unity_assets_contain_no_embedded_secrets_or_tokens():
    forbidden = (
        "HOLOASSIST_API_OPERATOR_TOKEN",
        "HOLOASSIST_API_REVIEWER_TOKEN",
        "POSTGRES_PASSWORD",
        "OPENAI_API_KEY",
        "Authorization",
        "Bearer ",
    )
    checked_files = (
        list(UNITY_ASSETS_DIR.rglob("*.cs"))
        + list(UNITY_ASSETS_DIR.rglob("*.uss"))
        + list(UNITY_ASSETS_DIR.rglob("*.tss"))
        + list(UNITY_ASSETS_DIR.rglob("*.asmdef"))
    )
    assert len(checked_files) >= 8
    for asset_file in checked_files:
        text = asset_file.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"Forbidden secret/auth marker {marker} in {asset_file}"


def test_unity_validator_enforces_synthetic_and_tracking_guards():
    cs_source = CONTRACTS_CS.read_text(encoding="utf-8")
    for required_guard in (
        'report.schema_version != "1.0"',
        "report.guidance_allowed",
        'report.source_kind != "synthetic"',
        'obs.provenance != "simulated"',
        'trackingStatus != "tracked"',
        '"demo-label"',
        '"demo-critical-part"',
    ):
        assert required_guard in cs_source


def test_unity_ui_toolkit_and_editmode_test_framework_configured():
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    deps = manifest["dependencies"]
    assert "com.unity.ui" in deps
    assert "com.unity.ugui" in deps
    assert "com.unity.test-framework" in deps
    assert "com.unity.modules.uielements" in deps

    assert UI_TOOLKIT_VIEW_CS.is_file()
    assert USS_FILE.is_file()
    assert TSS_FILE.is_file()

    client_source = API_CLIENT_CS.read_text(encoding="utf-8")
    assert "HoloAssistUiToolkitView" in client_source
    assert "EventSystem" in client_source
    assert "StandaloneInputModule" in client_source
    assert "void OnGUI(" not in client_source

    view_source = UI_TOOLKIT_VIEW_CS.read_text(encoding="utf-8")
    assert "using UnityEngine.UIElements;" in view_source
    assert "UIDocument" in view_source
    assert "PanelSettings" in view_source
    assert "ScaleWithScreenSize" in view_source
    assert "CameraTransformWorldToPanel" in view_source

    editor_bootstrap = UNITY_SCRIPTS_DIR / "Editor" / "HoloAssistEditorBootstrap.cs"
    assert editor_bootstrap.is_file()
    assert "NormalizeAllGameViews" in editor_bootstrap.read_text(encoding="utf-8")

    editmode_asmdef = UNITY_EDITMODE_DIR / "HoloAssist.Client.EditModeTests.asmdef"
    editmode_tests = UNITY_EDITMODE_DIR / "HoloAssistClientEditModeTests.cs"
    assert editmode_asmdef.is_file()
    assert editmode_tests.is_file()

    test_source = editmode_tests.read_text(encoding="utf-8")
    assert "[TestFixture]" in test_source
    assert "MotorRig3D_HighlightsVerifiedPartsAndClearsImmediatelyOnTrackingLoss" in test_source
