using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UIElements;

namespace HoloAssist.Client.Tests
{
    [TestFixture]
    public class HoloAssistClientEditModeTests
    {
        private static SafetyReport CreateValidSafetyReport()
        {
            const string quote = "SENTETİK KART: Bu ekranda yalnızca test verisi gösteriliyor.";
            return new SafetyReport
            {
                schema_version = "1.0",
                review_id = "test-review-1",
                analysis_request_id = "synthetic-analysis-demo-1",
                catalog_id = "synthetic-dc-motor-rig",
                catalog_version = "1.0.0",
                context_digest = "0123456789abcdef0123456789abcdef",
                source_kind = "synthetic",
                guidance_allowed = false,
                status = "display_allowed",
                reason_code = "verified_informational_step",
                steps = new List<StepResponse>
                {
                    new StepResponse
                    {
                        schema_version = "1.0",
                        step_id = "step-1",
                        instruction_id = "demo-information",
                        part_id = "demo-label",
                        risk = "informational",
                        status = "display_allowed",
                        reason_code = "verified_informational_step",
                        display_text = quote,
                        citations = new List<Citation>
                        {
                            new Citation
                            {
                                schema_version = "1.0",
                                assertion_id = "assert-demo-info",
                                evidence_id = "ev-demo-info-1",
                                document_id = "holoassist-synthetic-safety",
                                document_version = "1.0",
                                checksum = "deadbeef",
                                page = 1,
                                section = "3.1",
                                relation = "supports",
                                quote = quote
                            }
                        }
                    }
                }
            };
        }

        private static SensorDemoPayload CreateValidSensorPayload()
        {
            return new SensorDemoPayload
            {
                schema_version = "1.0",
                fixture_id = "current",
                fixture_checksum = "abc123def456",
                scope = "synthetic_demo",
                series = new SensorSeries
                {
                    schema_version = "1.0",
                    observations = new List<SensorObservation>
                    {
                        new SensorObservation
                        {
                            schema_version = "1.0",
                            equipment_id = "synthetic-rig",
                            sensor_id = "rig-current-sim",
                            timestamp_utc = "2026-01-01T00:00:00Z",
                            quantity = "current",
                            value = 0.42,
                            unit = "A",
                            provenance = "simulated",
                            quality = "valid"
                        },
                        new SensorObservation
                        {
                            schema_version = "1.0",
                            equipment_id = "synthetic-rig",
                            sensor_id = "rig-current-sim",
                            timestamp_utc = "2026-01-01T00:00:05Z",
                            quantity = "current",
                            value = 1.95,
                            unit = "A",
                            provenance = "simulated",
                            quality = "valid"
                        }
                    }
                },
                report = new SensorReport
                {
                    schema_version = "1.0",
                    equipment_id = "synthetic-rig",
                    sensor_id = "rig-current-sim",
                    quantity = "current",
                    unit = "A",
                    provenance = "simulated",
                    guidance_allowed = false,
                    sample_count = 2,
                    start_utc = "2026-01-01T00:00:00Z",
                    end_utc = "2026-01-01T00:00:05Z",
                    status = "summary_available",
                    reason_code = "ok",
                    statistics = new SensorStatistics
                    {
                        schema_version = "1.0",
                        minimum = 0.42,
                        maximum = 1.95,
                        mean = 1.185,
                        median = 1.185,
                        duration_seconds = 5.0,
                        slope_per_second = 0.306,
                        slope_unit = "A/s",
                        slope_direction = "increasing"
                    },
                    outliers = new SensorOutliers
                    {
                        schema_version = "1.0",
                        method = "mad",
                        threshold = 3.5,
                        status = "evaluated",
                        sample_indices = new List<int> { 1 }
                    }
                }
            };
        }

        [Test]
        public void ValidateSafetyReport_AcceptsCitedInformationalSyntheticStep()
        {
            SafetyReport report = CreateValidSafetyReport();
            bool valid = HoloAssistContractValidator.ValidateSafetyReport(report, out string error);

            Assert.That(valid, Is.True);
            Assert.That(error, Is.Empty);
        }

        [Test]
        public void ValidateSafetyReport_RejectsUnsupportedSchemaOrEnabledGuidance()
        {
            SafetyReport badSchema = CreateValidSafetyReport();
            badSchema.schema_version = "2.0";
            Assert.That(HoloAssistContractValidator.ValidateSafetyReport(badSchema, out string schemaErr), Is.False);
            Assert.That(schemaErr, Is.EqualTo("unsupported_schema_version"));

            SafetyReport badGuidance = CreateValidSafetyReport();
            badGuidance.guidance_allowed = true;
            Assert.That(HoloAssistContractValidator.ValidateSafetyReport(badGuidance, out string guidanceErr), Is.False);
            Assert.That(guidanceErr, Is.EqualTo("guidance_must_remain_false"));
        }

        [Test]
        public void ValidateSafetyReport_RejectsUncitedOrQuoteMismatchedDisplayStep()
        {
            SafetyReport uncited = CreateValidSafetyReport();
            uncited.steps[0].citations.Clear();
            Assert.That(HoloAssistContractValidator.ValidateSafetyReport(uncited, out string uncitedErr), Is.False);
            Assert.That(uncitedErr, Is.EqualTo("unbound_display_step"));

            SafetyReport tamperedQuote = CreateValidSafetyReport();
            tamperedQuote.steps[0].display_text = "Kaynaksız değiştirilmiş metin";
            Assert.That(HoloAssistContractValidator.ValidateSafetyReport(tamperedQuote, out string quoteErr), Is.False);
            Assert.That(quoteErr, Is.EqualTo("missing_verified_citation"));
        }

        [Test]
        public void ValidateSensorPayload_RejectsMeasuredProvenanceOrQuantityMismatch()
        {
            SensorDemoPayload validPayload = CreateValidSensorPayload();
            Assert.That(HoloAssistContractValidator.ValidateSensorPayload(validPayload, "current", out _), Is.True);

            Assert.That(HoloAssistContractValidator.ValidateSensorPayload(validPayload, "temperature", out string qtyErr), Is.False);
            Assert.That(qtyErr, Is.EqualTo("sensor_quantity_mismatch"));

            validPayload.series.observations[0].provenance = "measured";
            Assert.That(HoloAssistContractValidator.ValidateSensorPayload(validPayload, "current", out string provErr), Is.False);
            Assert.That(provErr, Is.EqualTo("non_simulated_observation"));
        }

        [Test]
        public void ValidateDiagnosticReport_EnforcesSupportingCitationAndPageLocation()
        {
            DiagnosticReport report = new DiagnosticReport
            {
                schema_version = "1.0",
                request_id = "diag-1",
                catalog_id = "synthetic-dc-motor-rig",
                catalog_version = "1.0.0",
                source_kind = "synthetic",
                guidance_allowed = false,
                status = "hypotheses_available",
                hypotheses = new List<DiagnosticHypothesis>
                {
                    new DiagnosticHypothesis
                    {
                        schema_version = "1.0",
                        code = "synthetic_load_variation",
                        explanation = "Sentetik yük değişimi olasılığı",
                        uncertainty = "conflicting_evidence",
                        supporting_evidence_ids = new List<string> { "ev-sup-1" },
                        contradicting_evidence_ids = new List<string> { "ev-con-1" }
                    }
                },
                assertion_matches = new List<DiagnosticAssertionMatch>
                {
                    new DiagnosticAssertionMatch
                    {
                        schema_version = "1.0",
                        rule_code = "synthetic_load_variation",
                        assertion_id = "a-1",
                        evidence_id = "ev-sup-1",
                        document_id = "synthetic-manual",
                        document_version = "1.0",
                        page = 2,
                        section = "4.2",
                        relation = "supports",
                        quote = "Destekleyen sentetik kayıt"
                    }
                }
            };

            Assert.That(HoloAssistContractValidator.ValidateDiagnosticReport(report, out _), Is.True);

            // Removing page & section must fail citation completeness check
            report.assertion_matches[0].page = 0;
            report.assertion_matches[0].section = string.Empty;
            Assert.That(HoloAssistContractValidator.ValidateDiagnosticReport(report, out string locErr), Is.False);
            Assert.That(locErr, Is.EqualTo("incomplete_diagnostic_citation"));
        }

        [Test]
        public void ResolveVerified3DPart_SuppressesPartOnTrackingLossOrUnknownCatalogPart()
        {
            SafetyReport report = CreateValidSafetyReport();

            Assert.That(HoloAssistContractValidator.ResolveVerified3DPart(report, "tracked"), Is.EqualTo("demo-label"));
            Assert.That(HoloAssistContractValidator.ResolveVerified3DPart(report, "lost"), Is.Empty);

            report.steps[0].part_id = "unknown-part";
            Assert.That(HoloAssistContractValidator.ResolveVerified3DPart(report, "tracked"), Is.Empty);

            report.steps[0].part_id = "demo-critical-part";
            report.status = "needs_approval";
            Assert.That(HoloAssistContractValidator.ResolveVerified3DPart(report, "tracked"), Is.EqualTo("demo-critical-part"));

            report.status = "blocked";
            Assert.That(HoloAssistContractValidator.ResolveVerified3DPart(report, "tracked"), Is.Empty);
        }

        [Test]
        public void MotorRig3D_HighlightsVerifiedPartsAndClearsImmediatelyOnTrackingLoss()
        {
            GameObject camObj = new GameObject("TestRigCamera");
            Camera cam = camObj.AddComponent<Camera>();
            HoloAssistMotorRig3D rig = new HoloAssistMotorRig3D();

            try
            {
                rig.InitializeSceneAndRig(cam);
                Assert.That(rig.ActivePartId, Is.Empty);
                Assert.That(rig.IsCalloutLineVisible, Is.False);
                Assert.That(rig.IsSpatialMarkerVisible, Is.False);

                rig.SetHighlightedPart("demo-label", false);
                Assert.That(rig.ActivePartId, Is.EqualTo("demo-label"));
                Assert.That(rig.IsCalloutLineVisible, Is.True);
                Assert.That(rig.IsSpatialMarkerVisible, Is.True);
                Assert.That(rig.TryGetCalloutWorldTop(out Vector3 topLabel), Is.True);
                Assert.That(topLabel.y, Is.GreaterThan(0.5f));

                // Simulated tracking loss / unknown part must clear stale 3D highlight, callout stem & 3D arrow marker
                rig.SetHighlightedPart(string.Empty, false);
                Assert.That(rig.ActivePartId, Is.Empty);
                Assert.That(rig.IsCalloutLineVisible, Is.False);
                Assert.That(rig.IsSpatialMarkerVisible, Is.False);

                rig.SetHighlightedPart("unknown-part", true);
                Assert.That(rig.ActivePartId, Is.Empty);
                Assert.That(rig.IsCalloutLineVisible, Is.False);
                Assert.That(rig.IsSpatialMarkerVisible, Is.False);
            }
            finally
            {
                rig.Dispose();
                Object.DestroyImmediate(camObj);
            }
        }

        [Test]
        public void ChartRenderer_GeneratesTextureForSimulatedSeriesAndDisposesCleanly()
        {
            HoloAssistChartRenderer renderer = new HoloAssistChartRenderer();
            try
            {
                renderer.RenderSeries(CreateValidSensorPayload());
                Assert.That(renderer.CurrentTexture, Is.Not.Null);
                Assert.That(renderer.CurrentTexture.width, Is.EqualTo(480));
                Assert.That(renderer.CurrentTexture.height, Is.EqualTo(176));
            }
            finally
            {
                renderer.Dispose();
                Assert.That(renderer.CurrentTexture, Is.Null);
            }
        }

        [Test]
        public void ValidateSpatialReport_RejectsActiveArSessionOrUntrackedAnchor()
        {
            SpatialProjectionReport report = new SpatialProjectionReport
            {
                schema_version = "1.0",
                review_id = "spatial-info",
                analysis_request_id = "synthetic-analysis-demo-1",
                catalog_id = "synthetic-spatial-anchor-catalog",
                catalog_version = "test-1",
                safety_status = "display_allowed",
                tracking_status = "tracked",
                ar_session_active = false,
                physical_device_validated = false,
                guidance_allowed = false,
                source_kind = "synthetic",
                active_anchor_count = 1,
                cards = new List<SpatialCardProjection>
                {
                    new SpatialCardProjection
                    {
                        schema_version = "1.0",
                        step_id = "step-1",
                        part_id = "demo-label",
                        anchor_id = "anchor-demo-label",
                        anchor_label = "Sentetik Gövde Bilgi Plakası",
                        render_mode = "card_and_highlight",
                        reason_code = "verified_synthetic_anchor_bound",
                        pose = new AnchorPose3D { schema_version = "1.0", x = 0.0, y = 0.64, z = 0.0, callout_offset_y = 0.24 },
                        source_kind = "synthetic",
                        guidance_allowed = false
                    }
                }
            };

            Assert.That(HoloAssistContractValidator.ValidateSpatialReport(report, out _), Is.True);

            report.ar_session_active = true;
            Assert.That(HoloAssistContractValidator.ValidateSpatialReport(report, out string arErr), Is.False);
            Assert.That(arErr, Is.EqualTo("invalid_spatial_governance"));

            report.ar_session_active = false;
            report.tracking_status = "lost";
            Assert.That(HoloAssistContractValidator.ValidateSpatialReport(report, out string trkErr), Is.False);
            Assert.That(trkErr, Is.EqualTo("untracked_anchor_must_be_suppressed"));
        }

        [Test]
        public void ValidateBenchmarkReport_RejectsPhysicalValidationOrMeasuredClaims()
        {
            SyntheticBenchmarkReport bench = new SyntheticBenchmarkReport
            {
                schema_version = "1.0",
                suite_id = "holoassist-synthetic-benchmark-v1",
                scope = "synthetic_fixture_benchmark",
                equipment_id = "synthetic-rig",
                source_kind = "synthetic",
                provenance = "simulated",
                physical_device_validated = false,
                calibrated_probabilities = false,
                guidance_allowed = false,
                all_synthetic_gates_passed = true,
                total_duration_ms = 250.0,
                vision = new VisionBenchmarkSummary { schema_version = "1.0", f1 = 1.0 },
                rag = new RagBenchmarkSummary { schema_version = "1.0", citation_locator_rate = 1.0 },
                diagnostic = new DiagnosticBenchmarkSummary { schema_version = "1.0", contradiction_preserved = true },
                safety_spatial = new SafetySpatialBenchmarkSummary { schema_version = "1.0", checks_total = 8, checks_passed = 8 }
            };

            Assert.That(HoloAssistContractValidator.ValidateBenchmarkReport(bench, out _), Is.True);

            bench.physical_device_validated = true;
            Assert.That(HoloAssistContractValidator.ValidateBenchmarkReport(bench, out string devErr), Is.False);
            Assert.That(devErr, Is.EqualTo("invalid_benchmark_governance"));
        }

        [Test]
        public void ValidateVisionPayload_EnforcesSyntheticGovernanceAndRejectsIdentityLeakOnUnknown()
        {
            VisionDemoPayload matched = new VisionDemoPayload
            {
                schema_version = "1.0",
                scenario = "warped",
                scope = "synthetic_demo",
                source_kind = "synthetic",
                calibrated_probabilities = false,
                guidance_allowed = false,
                status = "matched",
                reason = "reference_geometry_verified",
                equipment_id = "synthetic-rig",
                reference_kind = "synthetic",
                good_matches = 160,
                inliers = 140,
                inlier_ratio = 0.875,
                corner_error_px = 7.45,
                projected_corners = new List<VisionCorner2D>
                {
                    new VisionCorner2D { schema_version = "1.0", x = 95, y = 70 },
                    new VisionCorner2D { schema_version = "1.0", x = 650, y = 105 },
                    new VisionCorner2D { schema_version = "1.0", x = 615, y = 545 },
                    new VisionCorner2D { schema_version = "1.0", x = 65, y = 510 }
                }
            };

            Assert.That(HoloAssistContractValidator.ValidateVisionPayload(matched, "warped", out _), Is.True);

            matched.calibrated_probabilities = true;
            Assert.That(HoloAssistContractValidator.ValidateVisionPayload(matched, "warped", out string calErr), Is.False);
            Assert.That(calErr, Is.EqualTo("invalid_vision_governance"));

            matched.calibrated_probabilities = false;
            matched.status = "low_confidence";
            Assert.That(HoloAssistContractValidator.ValidateVisionPayload(matched, "warped", out string leakErr), Is.False);
            Assert.That(leakErr, Is.EqualTo("rejected_vision_leaked_identity"));
        }

        [Test]
        public void UiToolkitView_BuildsInteractiveButtonsAndPreservesFullCameraViewport()
        {
            GameObject hostObj = new GameObject("TestUiHost");
            GameObject camObj = new GameObject("TestUiCamera");
            Camera cam = camObj.AddComponent<Camera>();
            cam.rect = new Rect(0.25f, 0.25f, 0.5f, 0.5f);

            HoloAssistUiToolkitView view = new HoloAssistUiToolkitView();
            HoloAssistMotorRig3D rig = new HoloAssistMotorRig3D();
            try
            {
                view.Initialize(hostObj);
                view.RenderLeftNavigation(WorkstationModule.Safety, "information", "current", "complete", "reference");

                Assert.That(view.RootVisualElement, Is.Not.Null);
                Assert.That(view.RootVisualElement.pickingMode, Is.EqualTo(PickingMode.Ignore));

                Assert.That(view.RootVisualElement.Q<Button>("tab-vision"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("tab-safety"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("tab-sensors"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("tab-diagnostic"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("tab-benchmark"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("quick-info-btn"), Is.Not.Null);
                Assert.That(view.RootVisualElement.Q<Button>("quick-critical-btn"), Is.Not.Null);

                Button criticalCard = view.RootVisualElement.Q<Button>("pick-critical");
                Assert.That(criticalCard, Is.Not.Null);
                Assert.That(criticalCard.pickingMode, Is.EqualTo(PickingMode.Position));

                view.RenderLeftNavigation(WorkstationModule.Vision, "information", "current", "complete", "warped");
                Button warpedCard = view.RootVisualElement.Q<Button>("pick-warped");
                Assert.That(warpedCard, Is.Not.Null);

                view.SyncCameraViewportAndSpatialCallout(cam, rig, WorkstationModule.Safety, false);
                Assert.That(cam.rect, Is.EqualTo(new Rect(0f, 0f, 1f, 1f)));
            }
            finally
            {
                view.Dispose();
                rig.Dispose();
                Object.DestroyImmediate(camObj);
                Object.DestroyImmediate(hostObj);
            }
        }
    }
}

