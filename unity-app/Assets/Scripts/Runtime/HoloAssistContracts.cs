using System;
using System.Collections.Generic;

namespace HoloAssist.Client
{
    [Serializable]
    public class HealthResponse
    {
        public string schema_version;
        public string status;
        public string scope;
        public bool guidance_allowed;
    }

    [Serializable]
    public class ReadinessResponse
    {
        public string schema_version;
        public string status;
        public string scope;
        public string storage;
        public bool guidance_allowed;
    }

    [Serializable]
    public class ApiErrorResponse
    {
        public string schema_version;
        public string code;
    }

    [Serializable]
    public class StepRequest
    {
        public string step_id;
        public string instruction_id;
        public string part_id;
    }

    [Serializable]
    public class SafetyRequest
    {
        public string schema_version = "1.0";
        public string review_id;
        public string analysis_request_id;
        public string tracking_status;
        public List<StepRequest> steps;
    }

    [Serializable]
    public class Citation
    {
        public string schema_version;
        public string assertion_id;
        public string evidence_id;
        public string document_id;
        public string document_version;
        public string checksum;
        public int page;
        public string section;
        public string relation;
        public string quote;
    }

    [Serializable]
    public class StepResponse
    {
        public string schema_version;
        public string step_id;
        public string instruction_id;
        public string part_id;
        public string risk;
        public string status;
        public string reason_code;
        public List<Citation> citations;
        public string display_text;
    }

    [Serializable]
    public class SafetyReport
    {
        public string schema_version;
        public string review_id;
        public string analysis_request_id;
        public string catalog_id;
        public string catalog_version;
        public string context_digest;
        public string source_kind;
        public bool guidance_allowed;
        public string status;
        public string reason_code;
        public List<StepResponse> steps;
    }

    [Serializable]
    public class SensorObservation
    {
        public string schema_version;
        public string equipment_id;
        public string sensor_id;
        public string timestamp_utc;
        public string quantity;
        public double value;
        public string unit;
        public string provenance;
        public string quality;
    }

    [Serializable]
    public class SensorSeries
    {
        public string schema_version;
        public List<SensorObservation> observations;
    }

    [Serializable]
    public class SensorStatistics
    {
        public string schema_version;
        public double minimum;
        public double maximum;
        public double mean;
        public double median;
        public double first_value;
        public double last_value;
        public double delta;
        public double duration_seconds;
        public double slope_per_second;
        public string slope_unit;
        public string slope_direction;
    }

    [Serializable]
    public class SensorOutliers
    {
        public string schema_version;
        public string method;
        public double threshold;
        public string status;
        public List<int> sample_indices;
    }

    [Serializable]
    public class SensorReport
    {
        public string schema_version;
        public string equipment_id;
        public string sensor_id;
        public string quantity;
        public string unit;
        public string provenance;
        public bool guidance_allowed;
        public int sample_count;
        public string start_utc;
        public string end_utc;
        public string status;
        public string reason_code;
        public SensorStatistics statistics;
        public SensorOutliers outliers;
    }

    [Serializable]
    public class SensorDemoPayload
    {
        public string schema_version;
        public string fixture_id;
        public string fixture_checksum;
        public string scope;
        public SensorSeries series;
        public SensorReport report;
    }

    [Serializable]
    public class DiagnosticHypothesis
    {
        public string schema_version;
        public string code;
        public string explanation;
        public List<string> supporting_evidence_ids;
        public List<string> contradicting_evidence_ids;
        public string uncertainty;
        public List<string> missing_information;
    }

    [Serializable]
    public class DiagnosticAssertionMatch
    {
        public string schema_version;
        public string rule_code;
        public string assertion_id;
        public string evidence_id;
        public string document_id;
        public string document_version;
        public string checksum;
        public int page;
        public string section;
        public string relation;
        public string quote;
    }

    [Serializable]
    public class DiagnosticReport
    {
        public string schema_version;
        public string request_id;
        public string catalog_id;
        public string catalog_version;
        public string source_kind;
        public bool guidance_allowed;
        public string status;
        public List<DiagnosticHypothesis> hypotheses;
        public List<DiagnosticAssertionMatch> assertion_matches;
        public List<string> missing_information;
        public string reason_code;
    }

    [Serializable]
    public class DemoExportEnvelope
    {
        public string schema_version;
        public string export_id;
        public string generated_utc;
        public string scope;
        public bool independent_sections;
        public bool guidance_allowed;
    }

    [Serializable]
    public class AnchorPose3D
    {
        public string schema_version;
        public double x;
        public double y;
        public double z;
        public double callout_offset_y;
    }

    [Serializable]
    public class SpatialCardProjection
    {
        public string schema_version;
        public string step_id;
        public string part_id;
        public string anchor_id;
        public string anchor_label;
        public string render_mode;
        public string reason_code;
        public AnchorPose3D pose;
        public string display_text;
        public List<Citation> citations;
        public string source_kind;
        public bool guidance_allowed;
    }

    [Serializable]
    public class SpatialProjectionReport
    {
        public string schema_version;
        public string review_id;
        public string analysis_request_id;
        public string catalog_id;
        public string catalog_version;
        public string safety_status;
        public string tracking_status;
        public bool ar_session_active;
        public bool physical_device_validated;
        public bool guidance_allowed;
        public string source_kind;
        public int active_anchor_count;
        public List<SpatialCardProjection> cards;
    }

    [Serializable]
    public class VisionBenchmarkSummary
    {
        public string schema_version;
        public int frames_evaluated;
        public int true_positives;
        public int true_negatives;
        public int false_positives;
        public int false_negatives;
        public double precision;
        public double recall;
        public double f1;
        public double warped_max_corner_error_px;
        public bool calibrated_probabilities;
    }

    [Serializable]
    public class RagBenchmarkSummary
    {
        public string schema_version;
        public int documents_indexed;
        public int chunks_indexed;
        public int queries_executed;
        public double citation_locator_rate;
        public int unsupported_claim_count;
        public int cross_equipment_leakage_count;
        public int cache_hits;
        public int cache_misses;
        public double cold_query_ms;
        public double warm_query_ms;
        public string corpus_digest;
    }

    [Serializable]
    public class DiagnosticBenchmarkSummary
    {
        public string schema_version;
        public int sensor_series_verified;
        public bool supervisor_handoff_ready;
        public bool contradiction_preserved;
        public bool missing_counter_evidence_abstained;
    }

    [Serializable]
    public class SafetySpatialBenchmarkSummary
    {
        public string schema_version;
        public int checks_total;
        public int checks_passed;
        public int safety_violations;
        public bool tracking_loss_suppressed;
        public bool unknown_anchor_suppressed;
        public bool replay_token_rejected;
        public bool digest_tamper_rejected;
    }

    [Serializable]
    public class OpenHardwareGate
    {
        public string schema_version;
        public string gate_id;
        public string status;
        public string summary;
    }

    [Serializable]
    public class VisionCorner2D
    {
        public string schema_version;
        public double x;
        public double y;
    }

    [Serializable]
    public class VisionDemoPayload
    {
        public string schema_version;
        public string scenario;
        public string scope;
        public string source_kind;
        public bool calibrated_probabilities;
        public bool guidance_allowed;
        public string status;
        public string reason;
        public string equipment_id;
        public string reference_kind;
        public int good_matches;
        public int inliers;
        public double inlier_ratio;
        public double corner_error_px;
        public List<VisionCorner2D> projected_corners;
    }

    [Serializable]
    public class SyntheticBenchmarkReport
    {
        public string schema_version;
        public string suite_id;
        public string scope;
        public string equipment_id;
        public string source_kind;
        public string provenance;
        public bool physical_device_validated;
        public bool calibrated_probabilities;
        public bool guidance_allowed;
        public bool all_synthetic_gates_passed;
        public double total_duration_ms;
        public VisionBenchmarkSummary vision;
        public RagBenchmarkSummary rag;
        public DiagnosticBenchmarkSummary diagnostic;
        public SafetySpatialBenchmarkSummary safety_spatial;
        public List<OpenHardwareGate> open_hardware_gates;
    }

    public static class HoloAssistContractValidator
    {
        private static readonly HashSet<string> ValidSafetyStatuses = new HashSet<string>
        {
            "display_allowed",
            "needs_approval",
            "needs_information",
            "blocked"
        };

        private static readonly HashSet<string> Verified3DParts = new HashSet<string>
        {
            "demo-label",
            "demo-critical-part"
        };

        public static bool ValidateSafetyReport(SafetyReport report, out string error)
        {
            error = string.Empty;
            if (report == null)
            {
                error = "null_safety_report";
                return false;
            }
            if (report.schema_version != "1.0")
            {
                error = "unsupported_schema_version";
                return false;
            }
            if (report.guidance_allowed)
            {
                error = "guidance_must_remain_false";
                return false;
            }
            if (report.source_kind != "synthetic")
            {
                error = "unexpected_source_kind";
                return false;
            }
            if (!ValidSafetyStatuses.Contains(report.status))
            {
                error = "unknown_safety_status";
                return false;
            }
            if (report.steps == null || report.steps.Count == 0)
            {
                error = "empty_steps";
                return false;
            }

            if (report.status == "display_allowed")
            {
                foreach (StepResponse step in report.steps)
                {
                    if (step.status != "display_allowed" ||
                        step.risk != "informational" ||
                        string.IsNullOrEmpty(step.display_text) ||
                        step.citations == null ||
                        step.citations.Count == 0)
                    {
                        error = "unbound_display_step";
                        return false;
                    }

                    bool hasSupportingCitation = false;
                    foreach (Citation c in step.citations)
                    {
                        bool hasLocation = c.page > 0 || !string.IsNullOrEmpty(c.section);
                        if (c.relation == "supports" &&
                            c.quote == step.display_text &&
                            !string.IsNullOrEmpty(c.evidence_id) &&
                            !string.IsNullOrEmpty(c.document_id) &&
                            !string.IsNullOrEmpty(c.document_version) &&
                            hasLocation)
                        {
                            hasSupportingCitation = true;
                            break;
                        }
                    }

                    if (!hasSupportingCitation)
                    {
                        error = "missing_verified_citation";
                        return false;
                    }
                }
            }

            return true;
        }

        public static bool ValidateSensorPayload(SensorDemoPayload payload, string expectedQuantity, out string error)
        {
            error = string.Empty;
            if (payload == null || payload.report == null || payload.series == null)
            {
                error = "null_sensor_payload";
                return false;
            }
            if (payload.schema_version != "1.0" || payload.scope != "synthetic_demo")
            {
                error = "invalid_sensor_envelope";
                return false;
            }
            if (payload.fixture_id != expectedQuantity || payload.report.quantity != expectedQuantity)
            {
                error = "sensor_quantity_mismatch";
                return false;
            }
            if (payload.report.provenance != "simulated" || payload.report.guidance_allowed)
            {
                error = "invalid_sensor_governance";
                return false;
            }
            if (payload.series.observations == null || payload.series.observations.Count == 0)
            {
                error = "empty_observations";
                return false;
            }
            foreach (SensorObservation obs in payload.series.observations)
            {
                if (obs.provenance != "simulated")
                {
                    error = "non_simulated_observation";
                    return false;
                }
            }
            return true;
        }

        public static bool ValidateDiagnosticReport(DiagnosticReport report, out string error)
        {
            error = string.Empty;
            if (report == null)
            {
                error = "null_diagnostic_report";
                return false;
            }
            if (report.schema_version != "1.0" || report.source_kind != "synthetic" || report.guidance_allowed)
            {
                error = "invalid_diagnostic_governance";
                return false;
            }
            if (report.status != "hypotheses_available" &&
                report.status != "needs_information" &&
                report.status != "blocked")
            {
                error = "unknown_diagnostic_status";
                return false;
            }
            if (report.status == "hypotheses_available")
            {
                if (report.hypotheses == null || report.assertion_matches == null)
                {
                    error = "missing_hypotheses_arrays";
                    return false;
                }
                foreach (DiagnosticHypothesis hyp in report.hypotheses)
                {
                    bool hasSupport = false;
                    foreach (DiagnosticAssertionMatch m in report.assertion_matches)
                    {
                        if (m.rule_code == hyp.code)
                        {
                            bool validLoc = m.page > 0 || !string.IsNullOrEmpty(m.section);
                            if (string.IsNullOrEmpty(m.evidence_id) ||
                                string.IsNullOrEmpty(m.document_version) ||
                                !validLoc)
                            {
                                error = "incomplete_diagnostic_citation";
                                return false;
                            }
                            if (m.relation == "supports")
                            {
                                hasSupport = true;
                            }
                        }
                    }
                    if (!hasSupport)
                    {
                        error = "unbound_hypothesis";
                        return false;
                    }
                }
            }
            return true;
        }

        public static string ResolveVerified3DPart(SafetyReport report, string trackingStatus)
        {
            if (report == null || trackingStatus != "tracked" || report.steps == null || report.steps.Count == 0)
            {
                return string.Empty;
            }
            if (report.status != "display_allowed" && report.status != "needs_approval")
            {
                return string.Empty;
            }
            string partId = report.steps[0].part_id;
            return Verified3DParts.Contains(partId) ? partId : string.Empty;
        }

        public static bool ValidateSpatialReport(SpatialProjectionReport report, out string error)
        {
            error = string.Empty;
            if (report == null || report.cards == null || report.cards.Count == 0)
            {
                error = "null_or_empty_spatial_report";
                return false;
            }
            if (report.schema_version != "1.0" ||
                report.source_kind != "synthetic" ||
                report.guidance_allowed ||
                report.ar_session_active ||
                report.physical_device_validated)
            {
                error = "invalid_spatial_governance";
                return false;
            }
            if (report.tracking_status != "tracked" && report.active_anchor_count != 0)
            {
                error = "untracked_anchor_must_be_suppressed";
                return false;
            }
            return true;
        }

        public static bool ValidateVisionPayload(VisionDemoPayload payload, string expectedScenario, out string error)
        {
            error = string.Empty;
            if (payload == null)
            {
                error = "null_vision_payload";
                return false;
            }
            if (payload.schema_version != "1.0" ||
                payload.scope != "synthetic_demo" ||
                payload.source_kind != "synthetic" ||
                payload.reference_kind != "synthetic" ||
                payload.calibrated_probabilities ||
                payload.guidance_allowed)
            {
                error = "invalid_vision_governance";
                return false;
            }
            if (payload.scenario != expectedScenario)
            {
                error = "vision_scenario_mismatch";
                return false;
            }
            if (payload.status != "matched" &&
                payload.status != "low_confidence" &&
                payload.status != "unknown")
            {
                error = "unknown_vision_status";
                return false;
            }
            if (payload.inliers > payload.good_matches)
            {
                error = "inliers_exceed_matches";
                return false;
            }
            if (payload.status == "matched")
            {
                if (payload.equipment_id != "synthetic-rig" ||
                    payload.projected_corners == null ||
                    payload.projected_corners.Count != 4)
                {
                    error = "incomplete_matched_vision_geometry";
                    return false;
                }
            }
            else
            {
                if (!string.IsNullOrEmpty(payload.equipment_id) ||
                    (payload.projected_corners != null && payload.projected_corners.Count > 0))
                {
                    error = "rejected_vision_leaked_identity";
                    return false;
                }
            }
            return true;
        }

        public static bool ValidateBenchmarkReport(SyntheticBenchmarkReport report, out string error)
        {
            error = string.Empty;
            if (report == null ||
                report.vision == null ||
                report.rag == null ||
                report.diagnostic == null ||
                report.safety_spatial == null)
            {
                error = "null_benchmark_report";
                return false;
            }
            if (report.schema_version != "1.0" ||
                report.scope != "synthetic_fixture_benchmark" ||
                report.source_kind != "synthetic" ||
                report.provenance != "simulated" ||
                report.guidance_allowed ||
                report.physical_device_validated ||
                report.calibrated_probabilities)
            {
                error = "invalid_benchmark_governance";
                return false;
            }
            return true;
        }
    }
}
