using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.UIElements;

namespace HoloAssist.Client
{
    public enum WorkstationModule
    {
        Vision = 0,
        Safety = 1,
        Sensors = 2,
        Diagnostic = 3,
        Benchmark = 4
    }

    public sealed class HoloAssistUiToolkitView
    {
        private PanelSettings runtimePanelSettings;
        private ThemeStyleSheet fallbackTheme;
        private UIDocument uiDocument;

        private VisualElement root;
        private VisualElement centerStage;

        // Top Bar Controls
        private Label healthPill;
        private Button port8001Btn;
        private Button port8000Btn;

        // Left Dock Controls
        private Button tabVisionBtn;
        private Button tabSafetyBtn;
        private Button tabSensorsBtn;
        private Button tabDiagBtn;
        private Button tabBenchBtn;
        private VisualElement leftModuleOptionsContainer;
        private Button spinToggleBtn;
        private Button stageQuickSpinBtn;
        private readonly Dictionary<string, Button> visionButtons = new Dictionary<string, Button>();
        private readonly Dictionary<string, Button> safetyButtons = new Dictionary<string, Button>();
        private readonly Dictionary<string, Button> sensorButtons = new Dictionary<string, Button>();
        private readonly Dictionary<string, Button> diagButtons = new Dictionary<string, Button>();

        public VisualElement RootVisualElement => root;

        // Center 3D Stage Overlays
        private Label stageTrackingPill;
        private VisualElement spatialCalloutBox;
        private Label spatialCalloutLabel;
        private VisualElement stageBottomNotice;
        private Label stageBottomNoticeText;

        // Right Dock Containers
        private VisualElement rightModuleContent;
        private Label expPillSafety;
        private Label expPillSensor;
        private Label expPillDiag;
        private Button exportBtn;
        private Label exportStatusLabel;

        // Pointer orbit state
        private bool isOrbitDragging;
        private int activePointerId = -1;
        private Vector2 lastPointerPos;

        // Protocol inspector toggle
        private bool protocolExpanded = true;

        // Callbacks into controller
        public event Action<string> OnPortSelected;
        public event Action OnRefreshRequested;
        public event Action OnOpenWebPlatform;
        public event Action<WorkstationModule> OnModuleSelected;
        public event Action<string> OnVisionScenarioSelected;
        public event Action<string> OnSafetyScenarioSelected;
        public event Action OnRunSafetyWalkthroughRequested;
        public event Action<string> OnSensorSelected;
        public event Action<string> OnDiagnosticSelected;
        public event Action OnBenchmarkRefreshRequested;
        public event Action OnResetCameraRequested;
        public event Action OnToggleSpinRequested;
        public event Action<Vector2> OnViewportOrbitDelta;
        public event Action<float> OnViewportZoomDelta;
        public event Action OnExportRequested;

        public void Initialize(GameObject hostObject)
        {
            if (hostObject == null) throw new ArgumentNullException(nameof(hostObject));

            ThemeStyleSheet theme = Resources.Load<ThemeStyleSheet>("HoloAssistTheme");
            if (theme == null)
            {
                fallbackTheme = ScriptableObject.CreateInstance<ThemeStyleSheet>();
                theme = fallbackTheme;
            }

            runtimePanelSettings = ScriptableObject.CreateInstance<PanelSettings>();
            runtimePanelSettings.name = "HoloAssistRuntimePanelSettings";
            runtimePanelSettings.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            runtimePanelSettings.referenceResolution = new Vector2Int(1380, 800);
            runtimePanelSettings.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
            runtimePanelSettings.match = 0.5f;
            runtimePanelSettings.sortingOrder = 10;
            runtimePanelSettings.themeStyleSheet = theme;

            uiDocument = hostObject.GetComponent<UIDocument>();
            if (uiDocument == null)
            {
                uiDocument = hostObject.AddComponent<UIDocument>();
            }
            uiDocument.panelSettings = runtimePanelSettings;

            root = uiDocument.rootVisualElement;
            root.Clear();
            root.pickingMode = PickingMode.Ignore;
            root.style.position = Position.Absolute;
            root.style.left = 0f;
            root.style.right = 0f;
            root.style.top = 0f;
            root.style.bottom = 0f;
            root.style.width = Length.Percent(100f);
            root.style.height = Length.Percent(100f);

            StyleSheet uss = Resources.Load<StyleSheet>("HoloAssistWorkstation");
            if (uss != null)
            {
                root.styleSheets.Add(uss);
            }

            BuildVisualTree();
        }

        private void BuildVisualTree()
        {
            VisualElement shell = new VisualElement();
            shell.AddToClassList("workstation-root");
            shell.pickingMode = PickingMode.Ignore;
            root.Add(shell);

            shell.Add(BuildTopTelemetryBar());

            VisualElement workspaceBody = new VisualElement();
            workspaceBody.AddToClassList("workspace-body");
            workspaceBody.pickingMode = PickingMode.Ignore;
            shell.Add(workspaceBody);

            workspaceBody.Add(BuildLeftControlDock());
            workspaceBody.Add(BuildCenter3DStage());
            workspaceBody.Add(BuildRightInspectorDock());
        }

        private VisualElement BuildTopTelemetryBar()
        {
            VisualElement bar = new VisualElement();
            bar.AddToClassList("top-bar");

            VisualElement leftGroup = new VisualElement();
            leftGroup.AddToClassList("top-left-group");
            leftGroup.pickingMode = PickingMode.Ignore;

            Label mark = new Label("H·");
            mark.AddToClassList("brand-mark");
            mark.pickingMode = PickingMode.Ignore;
            leftGroup.Add(mark);

            Label brandTitle = new Label("HoloAssist AI");
            brandTitle.AddToClassList("brand-title");
            brandTitle.pickingMode = PickingMode.Ignore;
            leftGroup.Add(brandTitle);

            Label brandSub = new Label("| 3D TEKNİK DENETİM İSTASYONU");
            brandSub.AddToClassList("brand-sub");
            brandSub.pickingMode = PickingMode.Ignore;
            leftGroup.Add(brandSub);

            Label govPill = new Label("SENTETİK DEMO · AR DEĞİLDİR · guidance_allowed: false");
            govPill.AddToClassList("gov-pill");
            govPill.pickingMode = PickingMode.Ignore;
            leftGroup.Add(govPill);

            bar.Add(leftGroup);

            VisualElement rightGroup = new VisualElement();
            rightGroup.AddToClassList("top-right-group");
            rightGroup.pickingMode = PickingMode.Ignore;

            healthPill = new Label("● Kontrol ediliyor…");
            healthPill.AddToClassList("health-pill");
            healthPill.pickingMode = PickingMode.Ignore;
            rightGroup.Add(healthPill);

            port8001Btn = new Button(() => OnPortSelected?.Invoke("http://127.0.0.1:8001")) { text = ":8001" };
            port8001Btn.name = "btn-port-8001";
            port8001Btn.AddToClassList("top-btn");
            port8001Btn.AddToClassList("top-btn-active");
            rightGroup.Add(port8001Btn);

            port8000Btn = new Button(() => OnPortSelected?.Invoke("http://127.0.0.1:8000")) { text = ":8000" };
            port8000Btn.name = "btn-port-8000";
            port8000Btn.AddToClassList("top-btn");
            rightGroup.Add(port8000Btn);

            Button refreshBtn = new Button(() => OnRefreshRequested?.Invoke()) { text = "Yenile ↻" };
            refreshBtn.name = "btn-refresh";
            refreshBtn.AddToClassList("top-btn");
            rightGroup.Add(refreshBtn);

            Button webBtn = new Button(() => OnOpenWebPlatform?.Invoke()) { text = "Web Platformu ↗" };
            webBtn.name = "btn-open-web";
            webBtn.AddToClassList("top-btn");
            webBtn.AddToClassList("top-btn-web");
            rightGroup.Add(webBtn);

            bar.Add(rightGroup);
            return bar;
        }

        private VisualElement BuildLeftControlDock()
        {
            VisualElement dock = new VisualElement();
            dock.AddToClassList("left-dock");

            Label eyebrow = new Label("YOL HARİTASI MODÜLLERİ (H1–H12)");
            eyebrow.AddToClassList("section-eyebrow");
            dock.Add(eyebrow);

            VisualElement tabs = new VisualElement();
            tabs.AddToClassList("module-tabs");

            tabVisionBtn = new Button(() => OnModuleSelected?.Invoke(WorkstationModule.Vision)) { text = "01 Tanıma" };
            tabVisionBtn.name = "tab-vision";
            tabVisionBtn.AddToClassList("tab-btn");
            tabs.Add(tabVisionBtn);

            tabSafetyBtn = new Button(() => OnModuleSelected?.Invoke(WorkstationModule.Safety)) { text = "02 Güven" };
            tabSafetyBtn.name = "tab-safety";
            tabSafetyBtn.AddToClassList("tab-btn");
            tabSafetyBtn.AddToClassList("tab-btn-active");
            tabs.Add(tabSafetyBtn);

            tabSensorsBtn = new Button(() => OnModuleSelected?.Invoke(WorkstationModule.Sensors)) { text = "03 Sensör" };
            tabSensorsBtn.name = "tab-sensors";
            tabSensorsBtn.AddToClassList("tab-btn");
            tabs.Add(tabSensorsBtn);

            tabDiagBtn = new Button(() => OnModuleSelected?.Invoke(WorkstationModule.Diagnostic)) { text = "04 Kanıt" };
            tabDiagBtn.name = "tab-diagnostic";
            tabDiagBtn.AddToClassList("tab-btn");
            tabs.Add(tabDiagBtn);

            tabBenchBtn = new Button(() => OnModuleSelected?.Invoke(WorkstationModule.Benchmark)) { text = "05 Bench" };
            tabBenchBtn.name = "tab-benchmark";
            tabBenchBtn.AddToClassList("tab-btn");
            tabs.Add(tabBenchBtn);

            dock.Add(tabs);

            ScrollView leftScroll = new ScrollView(ScrollViewMode.Vertical);
            leftScroll.style.flexGrow = 1f;
            leftScroll.style.minHeight = 0f;
            leftScroll.mouseWheelScrollSize = 42f;
            leftScroll.touchScrollBehavior = ScrollView.TouchScrollBehavior.Clamped;
            dock.Add(leftScroll);

            leftModuleOptionsContainer = new VisualElement();
            leftScroll.Add(leftModuleOptionsContainer);

            VisualElement sceneBox = new VisualElement();
            sceneBox.AddToClassList("scene-ctrl-box");

            Label sceneHeader = new Label("3D SAHNE KONTROLLERİ");
            sceneHeader.AddToClassList("section-eyebrow");
            sceneBox.Add(sceneHeader);

            Button resetCamBtn = new Button(() => OnResetCameraRequested?.Invoke()) { text = "Kamera Açısını Sıfırla" };
            resetCamBtn.name = "btn-reset-camera";
            resetCamBtn.AddToClassList("secondary-btn");
            sceneBox.Add(resetCamBtn);

            spinToggleBtn = new Button(() => OnToggleSpinRequested?.Invoke()) { text = "Mil Dönüş Önizlemesi: Açık" };
            spinToggleBtn.name = "btn-toggle-spin";
            spinToggleBtn.AddToClassList("secondary-btn");
            sceneBox.Add(spinToggleBtn);

            leftScroll.Add(sceneBox);
            return dock;
        }

        private VisualElement BuildCenter3DStage()
        {
            centerStage = new VisualElement();
            centerStage.AddToClassList("center-stage");
            centerStage.pickingMode = PickingMode.Position;

            VisualElement topHud = new VisualElement();
            topHud.AddToClassList("stage-hud-top");
            topHud.pickingMode = PickingMode.Ignore;

            Label hudCap = new Label("TEMSİLİ 3D DC MOTOR (synthetic-rig) · Sürükle: Döndür · Tekerlek: Yakınlaştır");
            hudCap.AddToClassList("stage-hud-caption");
            hudCap.pickingMode = PickingMode.Ignore;
            topHud.Add(hudCap);

            stageTrackingPill = new Label("BEKLENİYOR");
            stageTrackingPill.AddToClassList("stage-tracking-pill");
            stageTrackingPill.AddToClassList("tracking-pill-muted");
            stageTrackingPill.pickingMode = PickingMode.Ignore;
            topHud.Add(stageTrackingPill);

            centerStage.Add(topHud);

            spatialCalloutBox = new VisualElement();
            spatialCalloutBox.AddToClassList("spatial-callout");
            spatialCalloutBox.AddToClassList("spatial-callout-ok");
            spatialCalloutBox.pickingMode = PickingMode.Ignore;
            spatialCalloutBox.style.display = DisplayStyle.None;

            spatialCalloutLabel = new Label();
            spatialCalloutLabel.AddToClassList("spatial-callout-text");
            spatialCalloutLabel.pickingMode = PickingMode.Ignore;
            spatialCalloutBox.Add(spatialCalloutLabel);
            centerStage.Add(spatialCalloutBox);

            stageBottomNotice = new VisualElement();
            stageBottomNotice.AddToClassList("stage-bottom-notice");
            stageBottomNotice.pickingMode = PickingMode.Ignore;
            stageBottomNotice.style.display = DisplayStyle.None;

            stageBottomNoticeText = new Label("3D Parça Vurgusu ve Ok İşaretçisi Gizlendi (Takip kaybı, bilinmeyen parça veya reddedilen istek)");
            stageBottomNoticeText.AddToClassList("stage-bottom-notice-text");
            stageBottomNoticeText.pickingMode = PickingMode.Ignore;
            stageBottomNotice.Add(stageBottomNoticeText);
            centerStage.Add(stageBottomNotice);

            // Floating Quick-Action Toolbar directly on the 3D viewport
            VisualElement quickBar = new VisualElement();
            quickBar.AddToClassList("stage-quick-bar");
            quickBar.pickingMode = PickingMode.Ignore;

            Button qInfo = new Button(() =>
            {
                OnModuleSelected?.Invoke(WorkstationModule.Safety);
                OnSafetyScenarioSelected?.Invoke("information");
            }) { text = "✔ Bilgi Plakası" };
            qInfo.name = "quick-info-btn";
            qInfo.AddToClassList("stage-quick-btn");
            quickBar.Add(qInfo);

            Button qCrit = new Button(() =>
            {
                OnModuleSelected?.Invoke(WorkstationModule.Safety);
                OnSafetyScenarioSelected?.Invoke("critical");
            }) { text = "⚠ Kritik Klemens" };
            qCrit.name = "quick-critical-btn";
            qCrit.AddToClassList("stage-quick-btn");
            quickBar.Add(qCrit);

            Button qLost = new Button(() =>
            {
                OnModuleSelected?.Invoke(WorkstationModule.Safety);
                OnSafetyScenarioSelected?.Invoke("tracking");
            }) { text = "⌖ Takip Kaybı" };
            qLost.name = "quick-tracking-btn";
            qLost.AddToClassList("stage-quick-btn");
            quickBar.Add(qLost);

            Button qCam = new Button(() => OnResetCameraRequested?.Invoke()) { text = "↺ Açı Sıfırla" };
            qCam.name = "quick-reset-cam-btn";
            qCam.AddToClassList("stage-quick-btn");
            quickBar.Add(qCam);

            stageQuickSpinBtn = new Button(() => OnToggleSpinRequested?.Invoke()) { text = "⟳ Mil: Açık" };
            stageQuickSpinBtn.name = "quick-spin-btn";
            stageQuickSpinBtn.AddToClassList("stage-quick-btn");
            quickBar.Add(stageQuickSpinBtn);

            centerStage.Add(quickBar);

            // Pointer orbit & scroll zoom handlers (only start drag when clicking directly on background stage)
            centerStage.RegisterCallback<PointerDownEvent>(evt =>
            {
                if (evt.target != centerStage) return;
                if (evt.button == 0 || evt.button == 1)
                {
                    isOrbitDragging = true;
                    activePointerId = evt.pointerId;
                    lastPointerPos = evt.position;
                    centerStage.CapturePointer(evt.pointerId);
                    evt.StopPropagation();
                }
            });

            centerStage.RegisterCallback<PointerMoveEvent>(evt =>
            {
                if (!isOrbitDragging || evt.pointerId != activePointerId) return;
                Vector2 cur = evt.position;
                Vector2 delta = cur - lastPointerPos;
                lastPointerPos = cur;
                OnViewportOrbitDelta?.Invoke(delta);
                evt.StopPropagation();
            });

            centerStage.RegisterCallback<PointerUpEvent>(evt =>
            {
                if (isOrbitDragging && evt.pointerId == activePointerId)
                {
                    isOrbitDragging = false;
                    activePointerId = -1;
                    centerStage.ReleasePointer(evt.pointerId);
                    evt.StopPropagation();
                }
            });

            centerStage.RegisterCallback<PointerCaptureOutEvent>(_ =>
            {
                isOrbitDragging = false;
                activePointerId = -1;
            });

            centerStage.RegisterCallback<WheelEvent>(evt =>
            {
                OnViewportZoomDelta?.Invoke(evt.delta.y);
                evt.StopPropagation();
            });

            return centerStage;
        }

        private VisualElement BuildRightInspectorDock()
        {
            VisualElement dock = new VisualElement();
            dock.AddToClassList("right-dock");

            ScrollView rightScroll = new ScrollView(ScrollViewMode.Vertical);
            rightScroll.style.flexGrow = 1f;
            rightScroll.style.minHeight = 0f;
            rightScroll.mouseWheelScrollSize = 42f;
            rightScroll.touchScrollBehavior = ScrollView.TouchScrollBehavior.Clamped;
            dock.Add(rightScroll);

            rightModuleContent = new VisualElement();
            rightScroll.Add(rightModuleContent);

            // Pinned Independent Audit Export Card
            VisualElement exportCard = new VisualElement();
            exportCard.AddToClassList("card-box");
            exportCard.style.marginTop = 8f;

            Label expHeader = new Label("BAĞIMSIZ DENETİM PAKETİ (/v1/demo/report)");
            expHeader.AddToClassList("section-eyebrow");
            exportCard.Add(expHeader);

            Label expDesc = new Label("Her bölüm sunucuda bağımsız değerlendirilir; ortak ajan durumu imâ edilmez.");
            expDesc.AddToClassList("muted-note");
            exportCard.Add(expDesc);

            VisualElement pillsRow = new VisualElement();
            pillsRow.AddToClassList("export-pills-row");

            expPillSafety = CreateExportPill("safety=information");
            expPillSensor = CreateExportPill("sensor=current");
            expPillDiag = CreateExportPill("diagnostic=complete");
            pillsRow.Add(expPillSafety);
            pillsRow.Add(expPillSensor);
            pillsRow.Add(expPillDiag);
            exportCard.Add(pillsRow);

            exportBtn = new Button(() => OnExportRequested?.Invoke())
            {
                text = "⬇ Seçili Durumların JSON Raporunu Kaydet"
            };
            exportBtn.name = "btn-export-report";
            exportBtn.AddToClassList("primary-export-btn");
            exportCard.Add(exportBtn);

            exportStatusLabel = new Label();
            exportStatusLabel.AddToClassList("endpoint-tag");
            exportStatusLabel.style.marginTop = 5f;
            exportStatusLabel.style.display = DisplayStyle.None;
            exportCard.Add(exportStatusLabel);

            rightScroll.Add(exportCard);
            return dock;
        }

        private static Label CreateExportPill(string initialText)
        {
            Label pill = new Label(initialText);
            pill.AddToClassList("export-pill");
            return pill;
        }

        public void SyncCameraViewportAndSpatialCallout(
            Camera cam,
            HoloAssistMotorRig3D motorRig,
            WorkstationModule currentModule,
            bool safetyLoading)
        {
            if (cam == null || centerStage == null) return;

            if (cam.rect != new Rect(0f, 0f, 1f, 1f))
            {
                cam.rect = new Rect(0f, 0f, 1f, 1f);
            }

            Rect wb = centerStage.worldBound;
            string activePart = motorRig != null ? motorRig.ActivePartId : string.Empty;
            if (!string.IsNullOrEmpty(activePart) &&
                motorRig.TryGetCalloutWorldTop(out Vector3 worldTop))
            {
                bool isCrit = activePart == "demo-critical-part";
                UpdateTrackingPill(
                    isCrit ? "TRACKED · demo-critical-part" : "TRACKED · demo-label",
                    isCrit ? "tracking-pill-warn" : "tracking-pill-ok");

                stageBottomNotice.style.display = DisplayStyle.None;

                Vector3 camSpace = cam.WorldToViewportPoint(worldTop);
                if (camSpace.z > 0f && wb.width > 40f)
                {
                    Vector2 panelPt;
                    if (root != null && root.panel != null)
                    {
                        panelPt = RuntimePanelUtils.CameraTransformWorldToPanel(root.panel, worldTop, cam);
                    }
                    else
                    {
                        Vector3 screenPt = cam.WorldToScreenPoint(worldTop);
                        panelPt = new Vector2(screenPt.x, Screen.height - screenPt.y);
                    }

                    float localX = (panelPt.x - wb.x) - 108f;
                    float localY = (panelPt.y - wb.y) - 34f;
                    localX = Mathf.Clamp(localX, 10f, Mathf.Max(12f, wb.width - 230f));
                    localY = Mathf.Clamp(localY, 44f, Mathf.Max(46f, wb.height - 86f));

                    spatialCalloutBox.style.left = localX;
                    spatialCalloutBox.style.top = localY;
                    spatialCalloutBox.EnableInClassList("spatial-callout-ok", !isCrit);
                    spatialCalloutBox.EnableInClassList("spatial-callout-warn", isCrit);
                    spatialCalloutLabel.text = isCrit
                        ? "demo-critical-part · Kalıcı Onay Gerekli"
                        : "demo-label · Kaynak & Konum Doğrulandı";
                    spatialCalloutBox.style.display = DisplayStyle.Flex;
                }
                else
                {
                    spatialCalloutBox.style.display = DisplayStyle.None;
                }
            }
            else
            {
                spatialCalloutBox.style.display = DisplayStyle.None;
                UpdateTrackingPill("VURGU GİZLENDİ", "tracking-pill-muted");
                bool showSuppressionNotice =
                    (currentModule == WorkstationModule.Safety || currentModule == WorkstationModule.Vision) &&
                    !safetyLoading;
                stageBottomNotice.style.display = showSuppressionNotice
                    ? DisplayStyle.Flex
                    : DisplayStyle.None;
            }
        }

        private void UpdateTrackingPill(string text, string variantClass)
        {
            if (stageTrackingPill == null) return;
            stageTrackingPill.text = text;
            stageTrackingPill.EnableInClassList("tracking-pill-ok", variantClass == "tracking-pill-ok");
            stageTrackingPill.EnableInClassList("tracking-pill-warn", variantClass == "tracking-pill-warn");
            stageTrackingPill.EnableInClassList("tracking-pill-muted", variantClass == "tracking-pill-muted");
        }

        public void SetServerStatus(bool online, string healthText, string storageText, string activeBaseUrl)
        {
            if (healthPill != null)
            {
                healthPill.text = (online ? "● " : "○ ") + healthText + " · " + storageText;
                healthPill.EnableInClassList("health-pill-online", online);
                healthPill.EnableInClassList("health-pill-offline", !online);
            }
            if (port8001Btn != null)
            {
                port8001Btn.EnableInClassList("top-btn-active", activeBaseUrl != null && activeBaseUrl.Contains("8001"));
            }
            if (port8000Btn != null)
            {
                port8000Btn.EnableInClassList("top-btn-active", activeBaseUrl != null && activeBaseUrl.Contains("8000"));
            }
        }

        public void SetSpinButtonState(bool spinning)
        {
            if (spinToggleBtn != null)
            {
                spinToggleBtn.text = spinning
                    ? "Mil Dönüş Önizlemesi: Açık"
                    : "Mil Dönüş Önizlemesi: Duraklatıldı";
            }
            if (stageQuickSpinBtn != null)
            {
                stageQuickSpinBtn.text = spinning
                    ? "⟳ Mil: Açık"
                    : "⟳ Mil: Durdu";
            }
        }

        public void SetExportSelectionPills(string safetyKey, string sensorKey, string diagKey)
        {
            string safeSafety = (safetyKey == "information" ||
                                 safetyKey == "critical" ||
                                 safetyKey == "tracking" ||
                                 safetyKey == "unknown")
                ? safetyKey
                : "information";
            if (expPillSafety != null) expPillSafety.text = "safety=" + safeSafety;
            if (expPillSensor != null) expPillSensor.text = "sensor=" + sensorKey;
            if (expPillDiag != null) expPillDiag.text = "diagnostic=" + diagKey;
        }

        public void SetExportStatus(bool running, string message)
        {
            if (exportBtn != null) exportBtn.SetEnabled(!running);
            if (exportStatusLabel != null)
            {
                exportStatusLabel.text = message ?? string.Empty;
                exportStatusLabel.style.display = string.IsNullOrEmpty(message) ? DisplayStyle.None : DisplayStyle.Flex;
            }
        }

        public void RenderLeftNavigation(
            WorkstationModule activeModule,
            string selectedSafety,
            string selectedSensor,
            string selectedDiag,
            string selectedVision = "reference")
        {
            if (leftModuleOptionsContainer == null) return;

            if (tabVisionBtn != null)
            {
                tabVisionBtn.EnableInClassList("tab-btn-active", activeModule == WorkstationModule.Vision);
            }
            tabSafetyBtn.EnableInClassList("tab-btn-active", activeModule == WorkstationModule.Safety);
            tabSensorsBtn.EnableInClassList("tab-btn-active", activeModule == WorkstationModule.Sensors);
            tabDiagBtn.EnableInClassList("tab-btn-active", activeModule == WorkstationModule.Diagnostic);
            if (tabBenchBtn != null)
            {
                tabBenchBtn.EnableInClassList("tab-btn-active", activeModule == WorkstationModule.Benchmark);
            }

            leftModuleOptionsContainer.Clear();
            visionButtons.Clear();
            safetyButtons.Clear();
            sensorButtons.Clear();
            diagButtons.Clear();

            if (activeModule == WorkstationModule.Vision)
            {
                AddSectionIntro(leftModuleOptionsContainer, "EKİPMAN VE ETİKET TANIMA (H3)", "GET /v1/demo/vision/{scenario}");
                AddPickCard(leftModuleOptionsContainer, visionButtons, "reference", selectedVision,
                    "✔ Referans Etiket Eşleşmesi", "synthetic-rig · ORB+RANSAC matched",
                    k => OnVisionScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, visionButtons, "warped", selectedVision,
                    "⌖ Perspektif Açılı Sahne", "Homografi 4 köşe hizalama doğrulaması",
                    k => OnVisionScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, visionButtons, "unknown", selectedVision,
                    "⚠ Yabancı Ekipman / Zayıf Geometri", "low_confidence · kimlik atanmaz",
                    k => OnVisionScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, visionButtons, "low_feature", selectedVision,
                    "⊘ Özelliksiz / Boş Kare", "unknown · no_features güvenli red",
                    k => OnVisionScenarioSelected?.Invoke(k));
            }
            else if (activeModule == WorkstationModule.Safety)
            {
                AddSectionIntro(leftModuleOptionsContainer, "GÜVENLİK KAPISI VE 3D ANCHOR (H6–H9)", "POST /v1/demo/safety/evaluate");
                AddPickCard(leftModuleOptionsContainer, safetyButtons, "information", selectedSafety,
                    "✔ Kaynaklı Bilgi Kartı", "demo-label · 200 display_allowed",
                    k => OnSafetyScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, safetyButtons, "critical", selectedSafety,
                    "⚠ Kritik Müdahale Adımı", "demo-critical-part · 200 needs_approval",
                    k => OnSafetyScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, safetyButtons, "tracking", selectedSafety,
                    "⌖ Parça Takip Kaybı", "tracking: lost · 3D ok ve kart kalkar",
                    k => OnSafetyScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, safetyButtons, "unknown", selectedSafety,
                    "⊘ Bilinmeyen Parça", "unknown-part · 200 blocked",
                    k => OnSafetyScenarioSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, safetyButtons, "injection", selectedSafety,
                    "⚡ Yetkisiz Alan Enjeksiyonu", "approval: bypass · HTTP 422 testi",
                    k => OnSafetyScenarioSelected?.Invoke(k));

                Button walkthroughBtn = new Button(() => OnRunSafetyWalkthroughRequested?.Invoke())
                {
                    text = "▶ 5 Güvenlik Senaryosunu Sırayla Doğrula"
                };
                walkthroughBtn.name = "btn-safety-walkthrough";
                walkthroughBtn.AddToClassList("secondary-btn");
                walkthroughBtn.style.marginTop = 4f;
                leftModuleOptionsContainer.Add(walkthroughBtn);
            }
            else if (activeModule == WorkstationModule.Sensors)
            {
                AddSectionIntro(leftModuleOptionsContainer, "SENTETİK SENSÖR SERİLERİ (H5)", "GET /v1/demo/sensors/{sensor}");
                AddPickCard(leftModuleOptionsContainer, sensorButtons, "current", selectedSensor,
                    "Akım Serisi (A)", "6 örnek · MAD aykırı aday testi",
                    k => OnSensorSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, sensorButtons, "temperature", selectedSensor,
                    "Sıcaklık Serisi (°C)", "Sabit simulated zaman serisi",
                    k => OnSensorSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, sensorButtons, "vibration", selectedSensor,
                    "Titreşim Serisi (m/s²)", "Sabit simulated zaman serisi",
                    k => OnSensorSelected?.Invoke(k));
            }
            else if (activeModule == WorkstationModule.Diagnostic)
            {
                AddSectionIntro(leftModuleOptionsContainer, "KANIT VE ÇELİŞKİ MATRİSİ (H4–H6)", "GET /v1/demo/diagnostic/{mode}");
                AddPickCard(leftModuleOptionsContainer, diagButtons, "complete", selectedDiag,
                    "Tüm Test Kayıtları Mevcut", "Destekleyen ve karşıt alıntılar birlikte",
                    k => OnDiagnosticSelected?.Invoke(k));
                AddPickCard(leftModuleOptionsContainer, diagButtons, "missing_counter_evidence", selectedDiag,
                    "Karşıt Kayıt Eksik", "Olasılıklar otomatik gizlenir",
                    k => OnDiagnosticSelected?.Invoke(k));
            }
            else
            {
                AddSectionIntro(leftModuleOptionsContainer, "SENTETİK BENCHMARK PAKETİ (H10–H12)", "GET /v1/demo/evaluation");
                Button rerunBtn = new Button(() => OnBenchmarkRefreshRequested?.Invoke())
                {
                    text = "Benchmark Paketini Yeniden Doğrula ↻"
                };
                rerunBtn.name = "btn-rerun-benchmark";
                rerunBtn.AddToClassList("secondary-btn");
                leftModuleOptionsContainer.Add(rerunBtn);

                Label note = new Label("T05 Görüntü (ORB+RANSAC), T04+H11 RAG Önbellek, T06-T08 Tanı ve T09-T14 Güvenlik/Anchor kapılarını dondurulmuş sentetik verilerle doğrular.");
                note.AddToClassList("muted-note");
                leftModuleOptionsContainer.Add(note);
            }
        }

        private static void AddSectionIntro(VisualElement parent, string eyebrow, string endpoint)
        {
            Label eb = new Label(eyebrow);
            eb.AddToClassList("section-eyebrow");
            parent.Add(eb);

            Label ep = new Label(endpoint);
            ep.AddToClassList("endpoint-tag");
            parent.Add(ep);
        }

        private static void AddPickCard(
            VisualElement parent,
            Dictionary<string, Button> map,
            string key,
            string activeKey,
            string title,
            string subtitle,
            Action<string> onClick)
        {
            Button card = new Button(() => onClick?.Invoke(key))
            {
                text = string.Empty
            };
            card.name = "pick-" + key;
            card.AddToClassList("pick-btn");
            if (key == activeKey) card.AddToClassList("pick-btn-active");
            card.pickingMode = PickingMode.Position;

            Label t = new Label(title);
            t.AddToClassList("pick-title");
            t.pickingMode = PickingMode.Ignore;
            card.Add(t);

            Label s = new Label(subtitle);
            s.AddToClassList("pick-sub");
            s.pickingMode = PickingMode.Ignore;
            card.Add(s);

            map[key] = card;
            parent.Add(card);
        }

        public void RenderVisionInspector(
            bool loading,
            string errorText,
            VisionDemoPayload payload)
        {
            if (rightModuleContent == null) return;
            rightModuleContent.Clear();

            AddSectionIntro(
                rightModuleContent,
                "ORB + RANSAC REFERANS ETİKET TANIMA (HAFTA 3)",
                "Sezgisel eşleşme oranı kalibre edilmiş olasılık değildir");

            if (loading)
            {
                Label l = new Label("Sentetik görüntü çerçevesi ORB + RANSAC ile inceleniyor…");
                l.AddToClassList("muted-note");
                rightModuleContent.Add(l);
                return;
            }
            if (!string.IsNullOrEmpty(errorText))
            {
                VisualElement errBox = new VisualElement();
                errBox.AddToClassList("verdict-banner");
                errBox.AddToClassList("verdict-blocked");
                Label errLbl = new Label(errorText);
                errLbl.AddToClassList("verdict-body");
                errBox.Add(errLbl);
                rightModuleContent.Add(errBox);
                return;
            }
            if (payload == null) return;

            bool isMatched = payload.status == "matched";
            bool isLowConf = payload.status == "low_confidence";

            VisualElement banner = new VisualElement();
            banner.AddToClassList("verdict-banner");
            banner.AddToClassList(isMatched ? "verdict-ok" : isLowConf ? "verdict-warn" : "verdict-blocked");

            Label vTitle = new Label(isMatched
                ? "✔ Sentetik Referans Etiket Doğrulandı (synthetic-rig)"
                : isLowConf
                    ? "⚠ Zayıf Geometri · Düşük Güven Reddi"
                    : "⊘ Tanınmayan / Özelliksiz Kare · Kimlik Atanmadı");
            vTitle.AddToClassList("verdict-title");
            banner.Add(vTitle);

            Label vBody = new Label(isMatched
                ? "ORB özellik eşleşmesi ve RANSAC homografi projeksiyonu doğrulandı. 3D bilgi plakası (demo-label) sahnede işaretlendi."
                : "Güvenlik gereği belirsiz veya yabancı görüntüde ekipman kimliği (equipment_id: null) ve 3D parça işareti üretilmez.");
            vBody.AddToClassList("verdict-body");
            banner.Add(vBody);
            rightModuleContent.Add(banner);

            VisualElement kpiGrid = new VisualElement();
            kpiGrid.AddToClassList("kpi-grid");
            AddKpiCard(kpiGrid, "DURUM", payload.status);
            AddKpiCard(kpiGrid, "ORB EŞLEŞME", payload.good_matches.ToString(CultureInfo.InvariantCulture));
            AddKpiCard(kpiGrid, "RANSAC INLIER", payload.inliers.ToString(CultureInfo.InvariantCulture));
            AddKpiCard(kpiGrid, "SEZGİSEL ORAN", string.Format(CultureInfo.InvariantCulture, "{0:0.###} (kalibre değil)", payload.inlier_ratio));
            rightModuleContent.Add(kpiGrid);

            VisualElement metaCard = new VisualElement();
            metaCard.AddToClassList("card-box");
            AddKvRow(metaCard, "Senaryo", payload.scenario, false);
            AddKvRow(metaCard, "Ekipman Kimliği", string.IsNullOrEmpty(payload.equipment_id) ? "Atanmadı (null)" : payload.equipment_id, !isMatched);
            AddKvRow(metaCard, "Karar Nedeni", payload.reason, !isMatched);
            AddKvRow(metaCard, "Referans Türü", payload.reference_kind, false);
            AddKvRow(metaCard, "Köşe Sapması (Max)", FormatMetric(payload.corner_error_px, "px"), false);
            AddKvRow(metaCard, "Kalibre Olasılık", "HAYIR (calibrated_probabilities: false)", true);
            AddKvRow(metaCard, "YOLO Eğitimi", "Kapsam dışı (Etiketli gerçek veri seti yok)", true);
            AddKvRow(metaCard, "Fiziksel Eylem İzni", "KAPALI (guidance_allowed: false)", true);
            rightModuleContent.Add(metaCard);

            if (payload.projected_corners != null && payload.projected_corners.Count == 4)
            {
                VisualElement cornerCard = new VisualElement();
                cornerCard.AddToClassList("card-box");
                Label cHeader = new Label("HOMOGRAFİ PROJEKSİYON KÖŞELERİ (PX)");
                cHeader.AddToClassList("section-eyebrow");
                cornerCard.Add(cHeader);

                for (int i = 0; i < payload.projected_corners.Count; i++)
                {
                    VisionCorner2D pt = payload.projected_corners[i];
                    AddKvRow(
                        cornerCard,
                        $"Köşe #{i + 1}",
                        string.Format(CultureInfo.InvariantCulture, "x={0:0.##}, y={1:0.##}", pt.x, pt.y),
                        false);
                }
                rightModuleContent.Add(cornerCard);
            }
        }

        public void RenderSafetyInspector(
            bool httpOk,
            string httpBadgeText,
            string tone,
            string verdictTitle,
            string verdictBody,
            SafetyReport report,
            SpatialProjectionReport spatialReport,
            string reqJson,
            string resJson)
        {
            if (rightModuleContent == null) return;
            rightModuleContent.Clear();

            VisualElement headerRow = new VisualElement();
            headerRow.AddToClassList("inspector-header-row");

            Label title = new Label("DOĞRULANMIŞ İSTEMCİ SONUCU");
            title.AddToClassList("section-eyebrow");
            headerRow.Add(title);

            Label badge = new Label(httpBadgeText);
            badge.AddToClassList("http-badge");
            badge.AddToClassList(httpOk ? "http-badge-ok" : "http-badge-err");
            headerRow.Add(badge);
            rightModuleContent.Add(headerRow);

            VisualElement banner = new VisualElement();
            banner.AddToClassList("verdict-banner");
            string bannerCls = tone == "ok" ? "verdict-ok" :
                               tone == "warning" ? "verdict-warn" :
                               tone == "blocked" ? "verdict-blocked" : "verdict-neutral";
            banner.AddToClassList(bannerCls);

            Label vTitle = new Label(verdictTitle);
            vTitle.AddToClassList("verdict-title");
            banner.Add(vTitle);

            Label vBody = new Label(verdictBody);
            vBody.AddToClassList("verdict-body");
            banner.Add(vBody);
            rightModuleContent.Add(banner);

            if (report != null && report.steps != null && report.steps.Count > 0)
            {
                StepResponse step = report.steps[0];

                Label cardHeader = new Label("GÖSTERİM KARTI VE KAYNAK ZİNCİRİ");
                cardHeader.AddToClassList("section-eyebrow");
                rightModuleContent.Add(cardHeader);

                VisualElement quoteCard = new VisualElement();
                quoteCard.AddToClassList("card-box");
                if (report.status == "display_allowed" && !string.IsNullOrEmpty(step.display_text))
                {
                    Label q = new Label("\"" + step.display_text + "\"");
                    q.AddToClassList("quote-allowed");
                    quoteCard.Add(q);
                }
                else
                {
                    Label red = new Label("⊘ Atomik gizleme aktif: Adım metni ve kaynak alıntıları istemciye açılmadı.");
                    red.AddToClassList("quote-redacted");
                    quoteCard.Add(red);
                }
                rightModuleContent.Add(quoteCard);

                VisualElement metaCard = new VisualElement();
                metaCard.AddToClassList("card-box");
                AddKvRow(metaCard, "Parça Kimliği", step.part_id, false);
                AddKvRow(metaCard, "Risk Sınıfı", step.risk, false);
                AddKvRow(metaCard, "Neden Kodu", step.reason_code, false);
                AddKvRow(metaCard, "Veri Kökeni", report.source_kind, false);
                AddKvRow(metaCard, "Fiziksel Eylem İzni", "KAPALI (guidance_allowed: false)", true);

                if (step.citations != null && step.citations.Count > 0)
                {
                    Citation c = step.citations[0];
                    AddKvRow(metaCard, "Kaynak Belge", $"{c.document_id} (v{c.document_version})", false);
                    AddKvRow(metaCard, "Sayfa / Bölüm", $"Sayfa {c.page} · {c.section}", false);
                    AddKvRow(metaCard, "Kanıt Kimliği", c.evidence_id, false);
                }

                string shortDigest = !string.IsNullOrEmpty(report.context_digest) && report.context_digest.Length > 24
                    ? report.context_digest.Substring(0, 24) + "…"
                    : report.context_digest;
                AddKvRow(metaCard, "Context Digest", shortDigest, false);
                rightModuleContent.Add(metaCard);

                if (spatialReport != null && spatialReport.cards != null && spatialReport.cards.Count > 0)
                {
                    SpatialCardProjection sp = spatialReport.cards[0];
                    VisualElement spCard = new VisualElement();
                    spCard.AddToClassList("card-box");
                    AddKvRow(spCard, "3D Anchor Kimliği", string.IsNullOrEmpty(sp.anchor_id) ? "Yok (suppressed)" : sp.anchor_id, false);
                    AddKvRow(spCard, "Projeksiyon Modu", sp.render_mode, sp.render_mode != "card_and_highlight");
                    string poseStr = sp.pose != null
                        ? string.Format(CultureInfo.InvariantCulture, "({0:0.##}, {1:0.##}, {2:0.##})", sp.pose.x, sp.pose.y, sp.pose.z)
                        : "Gizlendi (pose: null)";
                    AddKvRow(spCard, "3D Sahne Konumu", poseStr, false);
                    AddKvRow(spCard, "Fiziksel AR Oturumu", "KAPALI (ar_session_active: false)", true);
                    rightModuleContent.Add(spCard);
                }
            }
            else if (!httpOk && httpBadgeText != null && httpBadgeText.Contains("422"))
            {
                VisualElement meta422 = new VisualElement();
                meta422.AddToClassList("card-box");
                AddKvRow(meta422, "Reddedilen Alan", "approval (\"client-bypass-attempt\")", true);
                AddKvRow(meta422, "Sunucu Hata Kodu", "invalid_request (HTTP 422)", false);
                AddKvRow(meta422, "Yansıma Koruması", "Gönderilen değer yanıta yazılmadı", false);
                AddKvRow(meta422, "Fiziksel Eylem İzni", "KAPALI (guidance_allowed: false)", true);
                rightModuleContent.Add(meta422);
            }

            // Expandable JSON Protocol Inspector
            VisualElement protoWrap = new VisualElement();
            Button toggleProtoBtn = null;
            VisualElement protoPanel = new VisualElement();
            protoPanel.AddToClassList("code-panel");
            protoPanel.style.display = protocolExpanded ? DisplayStyle.Flex : DisplayStyle.None;

            Label reqLbl = new Label("GÖNDERİLEN İSTEK (REQUEST JSON)");
            reqLbl.AddToClassList("code-label");
            protoPanel.Add(reqLbl);

            Label reqCode = new Label(reqJson ?? "{}");
            reqCode.AddToClassList("code-text");
            reqCode.style.marginBottom = 8f;
            protoPanel.Add(reqCode);

            Label resLbl = new Label("SUNUCU YANITI (RESPONSE JSON)");
            resLbl.AddToClassList("code-label");
            protoPanel.Add(resLbl);

            Label resCode = new Label(resJson ?? "{}");
            resCode.AddToClassList("code-text");
            protoPanel.Add(resCode);

            toggleProtoBtn = new Button(() =>
            {
                protocolExpanded = !protocolExpanded;
                protoPanel.style.display = protocolExpanded ? DisplayStyle.Flex : DisplayStyle.None;
                toggleProtoBtn.text = protocolExpanded
                    ? "▼ Canlı JSON Sözleşme Denetçisini Gizle"
                    : "▶ Canlı JSON Sözleşme Denetçisini Göster";
            })
            {
                text = protocolExpanded
                    ? "▼ Canlı JSON Sözleşme Denetçisini Gizle"
                    : "▶ Canlı JSON Sözleşme Denetçisini Göster"
            };
            toggleProtoBtn.AddToClassList("secondary-btn");

            protoWrap.Add(toggleProtoBtn);
            protoWrap.Add(protoPanel);
            rightModuleContent.Add(protoWrap);
        }

        public void RenderSensorInspector(
            bool loading,
            string errorText,
            SensorDemoPayload payload,
            Texture2D chartTexture)
        {
            if (rightModuleContent == null) return;
            rightModuleContent.Clear();

            AddSectionIntro(rightModuleContent, "SENTETİK ZAMAN SERİSİ ANALİZİ", "Köken: simulated · Canlı ölçüm değildir");

            if (loading)
            {
                Label l = new Label("Sentetik zaman serisi sunucudan yükleniyor…");
                l.AddToClassList("muted-note");
                rightModuleContent.Add(l);
                return;
            }
            if (!string.IsNullOrEmpty(errorText))
            {
                VisualElement errBox = new VisualElement();
                errBox.AddToClassList("verdict-banner");
                errBox.AddToClassList("verdict-blocked");
                Label errLbl = new Label(errorText);
                errLbl.AddToClassList("verdict-body");
                errBox.Add(errLbl);
                rightModuleContent.Add(errBox);
                return;
            }
            if (payload == null || payload.report == null || payload.report.statistics == null) return;

            SensorReport rep = payload.report;
            SensorStatistics st = rep.statistics;
            string unit = rep.unit == "degC" ? "°C" : rep.unit == "m/s2" ? "m/s²" : rep.unit;

            if (chartTexture != null)
            {
                VisualElement chartCard = new VisualElement();
                chartCard.AddToClassList("card-box");

                Image img = new Image
                {
                    image = chartTexture,
                    scaleMode = ScaleMode.ScaleToFit
                };
                img.AddToClassList("chart-image");
                chartCard.Add(img);

                Label legend = new Label("● Sentetik örnek (simulated)     ● MAD istatistiksel aykırı aday");
                legend.AddToClassList("muted-note");
                legend.style.marginBottom = 0f;
                chartCard.Add(legend);
                rightModuleContent.Add(chartCard);
            }

            VisualElement kpiGrid = new VisualElement();
            kpiGrid.AddToClassList("kpi-grid");
            AddKpiCard(kpiGrid, "ORTALAMA", FormatMetric(st.mean, unit));
            AddKpiCard(kpiGrid, "MEDYAN", FormatMetric(st.median, unit));
            AddKpiCard(kpiGrid, "MAKSİMUM", FormatMetric(st.maximum, unit));
            AddKpiCard(kpiGrid, "MİNİMUM", FormatMetric(st.minimum, unit));
            AddKpiCard(kpiGrid, "ZAMAN EĞİMİ", string.Format(CultureInfo.InvariantCulture, "{0:0.####} {1}", st.slope_per_second, st.slope_unit));
            AddKpiCard(kpiGrid, "SÜRE / ÖRNEK", string.Format(CultureInfo.InvariantCulture, "{0:0.#} sn · {1} kayıt", st.duration_seconds, rep.sample_count));
            rightModuleContent.Add(kpiGrid);

            HashSet<int> outlierIndices = new HashSet<int>();
            if (rep.outliers != null && rep.outliers.sample_indices != null)
            {
                foreach (int idx in rep.outliers.sample_indices) outlierIndices.Add(idx);
            }

            VisualElement madBanner = new VisualElement();
            madBanner.AddToClassList("verdict-banner");
            madBanner.AddToClassList(outlierIndices.Count > 0 ? "verdict-warn" : "verdict-ok");
            Label madTitle = new Label(outlierIndices.Count > 0
                ? $"⚠ İstatistiksel Aykırı Aday Saptandı ({outlierIndices.Count} örnek)"
                : "✔ İstatistiksel Aykırı Aday Saptanmadı");
            madTitle.AddToClassList("verdict-title");
            madBanner.Add(madTitle);

            Label madDesc = new Label(outlierIndices.Count > 0
                ? "MAD eşik kontrolü aykırı aday işaretledi; bu bir arıza teşhisi veya güvenlik kararı değildir."
                : "MAD eşik kontrolünde aykırı aday görülmedi; bu durum fiziksel güvenlik onayı anlamına gelmez.");
            madDesc.AddToClassList("verdict-body");
            madBanner.Add(madDesc);
            rightModuleContent.Add(madBanner);

            if (payload.series != null && payload.series.observations != null)
            {
                VisualElement sampleCard = new VisualElement();
                sampleCard.AddToClassList("card-box");

                Label tblHeader = new Label("UTC ÖRNEK DİZİSİ VE KÖKEN KAYDI");
                tblHeader.AddToClassList("section-eyebrow");
                sampleCard.Add(tblHeader);

                for (int i = 0; i < payload.series.observations.Count; i++)
                {
                    SensorObservation obs = payload.series.observations[i];
                    bool isOut = outlierIndices.Contains(i);

                    VisualElement row = new VisualElement();
                    row.AddToClassList("sample-row");

                    string shortUtc = !string.IsNullOrEmpty(obs.timestamp_utc) && obs.timestamp_utc.Length >= 19
                        ? obs.timestamp_utc.Substring(11, 8) + "Z"
                        : obs.timestamp_utc;

                    Label left = new Label($"#{i + 1} · {shortUtc} · {obs.provenance}");
                    left.AddToClassList("sample-cell");
                    row.Add(left);

                    string valText = string.Format(CultureInfo.InvariantCulture, "{0:0.###} {1}{2}",
                        obs.value, unit, isOut ? "  [MAD ADAYI]" : "");
                    Label right = new Label(valText);
                    right.AddToClassList(isOut ? "sample-outlier" : "sample-cell");
                    row.Add(right);

                    sampleCard.Add(row);
                }

                string shortSha = !string.IsNullOrEmpty(payload.fixture_checksum) && payload.fixture_checksum.Length > 20
                    ? payload.fixture_checksum.Substring(0, 20) + "…"
                    : payload.fixture_checksum;
                AddKvRow(sampleCard, "Sensör / SHA-256", $"{rep.sensor_id} · {shortSha}", false);
                rightModuleContent.Add(sampleCard);
            }
        }

        public void RenderDiagnosticInspector(
            bool loading,
            string errorText,
            DiagnosticReport report)
        {
            if (rightModuleContent == null) return;
            rightModuleContent.Clear();

            AddSectionIntro(rightModuleContent,
                "KAYNAK BAĞLAMA VE ÇELİŞKİ MATRİSİ",
                "Sıralamasız test olasılıkları · Kalibre edilmiş olasılık veya teşhis üretmez");

            if (loading)
            {
                Label l = new Label("Kaynak ve karşıt kanıt bağları denetleniyor…");
                l.AddToClassList("muted-note");
                rightModuleContent.Add(l);
                return;
            }
            if (!string.IsNullOrEmpty(errorText))
            {
                VisualElement errBox = new VisualElement();
                errBox.AddToClassList("verdict-banner");
                errBox.AddToClassList("verdict-blocked");
                Label errLbl = new Label(errorText);
                errLbl.AddToClassList("verdict-body");
                errBox.Add(errLbl);
                rightModuleContent.Add(errBox);
                return;
            }
            if (report == null) return;

            if (report.status != "hypotheses_available")
            {
                VisualElement warnBanner = new VisualElement();
                warnBanner.AddToClassList("verdict-banner");
                warnBanner.AddToClassList("verdict-warn");

                Label wt = new Label("Karşıt Kanıt Eksik · Tüm Olasılıklar Gizlendi");
                wt.AddToClassList("verdict-title");
                warnBanner.Add(wt);

                Label wb = new Label("Bilinen karşıt kayıt doğrulama kümesinde bulunamadığında destekleyen kayıt tek başına gösterilmez.");
                wb.AddToClassList("verdict-body");
                warnBanner.Add(wb);
                rightModuleContent.Add(warnBanner);

                if (report.missing_information != null && report.missing_information.Count > 0)
                {
                    VisualElement missCard = new VisualElement();
                    missCard.AddToClassList("card-box");
                    AddKvRow(missCard, "Durum Kodu", report.reason_code, true);
                    foreach (string miss in report.missing_information)
                    {
                        AddKvRow(missCard, "Eksik Kanıt", miss, true);
                    }
                    rightModuleContent.Add(missCard);
                }
                return;
            }

            foreach (DiagnosticHypothesis hyp in report.hypotheses)
            {
                VisualElement hypCard = new VisualElement();
                hypCard.AddToClassList("card-box");

                int supCount = hyp.supporting_evidence_ids != null ? hyp.supporting_evidence_ids.Count : 0;
                int conCount = hyp.contradicting_evidence_ids != null ? hyp.contradicting_evidence_ids.Count : 0;
                string uncLabel = hyp.uncertainty == "conflicting_evidence"
                    ? "[ÇELİŞKİLİ KANIT KORUNDU]"
                    : "[DOĞRULANMADI]";

                Label hTitle = new Label($"{uncLabel}  {hyp.code}");
                hTitle.AddToClassList("verdict-title");
                hypCard.Add(hTitle);

                Label hExp = new Label(hyp.explanation);
                hExp.AddToClassList("muted-note");
                hypCard.Add(hExp);

                AddKvRow(hypCard, "Kanıt Dengesi", $"+{supCount} destekleyen / −{conCount} karşıt kayıt", conCount > 0);

                foreach (DiagnosticAssertionMatch m in report.assertion_matches)
                {
                    if (m.rule_code != hyp.code) continue;
                    bool isSupport = m.relation == "supports";

                    VisualElement evBox = new VisualElement();
                    evBox.AddToClassList(isSupport ? "ev-support-box" : "ev-contradict-box");

                    Label evQuote = new Label((isSupport ? "＋ DESTEKLEYEN: " : "− KARŞIT: ") + m.quote);
                    evQuote.AddToClassList("verdict-body");
                    evBox.Add(evQuote);

                    Label evMeta = new Label($"{m.document_id} (v{m.document_version}) · Sayfa {m.page} · {m.section} · {m.evidence_id}");
                    evMeta.AddToClassList("endpoint-tag");
                    evMeta.style.marginTop = 2f;
                    evMeta.style.marginBottom = 0f;
                    evBox.Add(evMeta);

                    hypCard.Add(evBox);
                }

                rightModuleContent.Add(hypCard);
            }
        }

        public void RenderBenchmarkInspector(bool loading, string error, SyntheticBenchmarkReport report)
        {
            if (rightModuleContent == null) return;
            rightModuleContent.Clear();

            Label hdr = new Label("TEKRARLANABİLİR SENTETİK BENCHMARK (T15)");
            hdr.AddToClassList("section-eyebrow");
            rightModuleContent.Add(hdr);

            if (loading)
            {
                Label l = new Label("Sentetik doğrulama paketi çalıştırılıyor…");
                l.AddToClassList("muted-note");
                rightModuleContent.Add(l);
                return;
            }

            if (!string.IsNullOrEmpty(error) || report == null)
            {
                VisualElement errBox = new VisualElement();
                errBox.AddToClassList("verdict-banner");
                errBox.AddToClassList("verdict-blocked");
                Label et = new Label(string.IsNullOrEmpty(error) ? "Benchmark raporu alınamadı." : error);
                et.AddToClassList("verdict-body");
                errBox.Add(et);
                rightModuleContent.Add(errBox);
                return;
            }

            VisualElement banner = new VisualElement();
            banner.AddToClassList("verdict-banner");
            banner.AddToClassList(report.all_synthetic_gates_passed ? "verdict-ok" : "verdict-blocked");

            Label bTitle = new Label(report.all_synthetic_gates_passed
                ? "Tüm Sentetik Kapılar Doğrulandı"
                : "Sentetik Benchmark İhlali");
            bTitle.AddToClassList("verdict-title");
            banner.Add(bTitle);

            Label bSub = new Label(string.Format(
                CultureInfo.InvariantCulture,
                "{0} · Süre: {1:0.#} ms · physical_device_validated: false",
                report.suite_id,
                report.total_duration_ms));
            bSub.AddToClassList("verdict-body");
            banner.Add(bSub);
            rightModuleContent.Add(banner);

            VisualElement kpiGrid = new VisualElement();
            kpiGrid.AddToClassList("kpi-grid");
            AddKpiCard(kpiGrid, "ORB F1 (SENTETİK)", FormatMetric(report.vision.f1, ""));
            AddKpiCard(kpiGrid, "RAG KONUM TAMLIĞI", string.Format(CultureInfo.InvariantCulture, "%{0:0}", report.rag.citation_locator_rate * 100.0));
            AddKpiCard(kpiGrid, "RAG ÖNBELLEK", $"{report.rag.cache_hits} hit / {report.rag.cache_misses} miss");
            AddKpiCard(kpiGrid, "GÜVENLİK İHLALİ", $"{report.safety_spatial.safety_violations} / {report.safety_spatial.checks_total}");
            rightModuleContent.Add(kpiGrid);

            VisualElement detailCard = new VisualElement();
            detailCard.AddToClassList("card-box");
            AddKvRow(detailCard, "Perspektif Köşe Sapması", FormatMetric(report.vision.warped_max_corner_error_px, "px"), false);
            AddKvRow(detailCard, "Soğuk / Sıcak Sorgu", string.Format(CultureInfo.InvariantCulture, "{0:0.##} ms → {1:0.##} ms", report.rag.cold_query_ms, report.rag.warm_query_ms), false);
            AddKvRow(detailCard, "Ekipman Sızıntısı", $"{report.rag.cross_equipment_leakage_count} kayıt", false);
            AddKvRow(detailCard, "Karşıt Kanıt & Susma", (report.diagnostic.contradiction_preserved && report.diagnostic.missing_counter_evidence_abstained) ? "Doğrulandı" : "İhlal", false);
            AddKvRow(detailCard, "Replay & Digest Tamper", (report.safety_spatial.replay_token_rejected && report.safety_spatial.digest_tamper_rejected) ? "Reddedildi (SQLite)" : "İhlal", false);
            AddKvRow(detailCard, "Fiziksel Eylem & Cihaz", "KAPALI (guidance_allowed: false)", true);
            rightModuleContent.Add(detailCard);

            if (report.open_hardware_gates != null && report.open_hardware_gates.Count > 0)
            {
                VisualElement gateCard = new VisualElement();
                gateCard.AddToClassList("card-box");
                foreach (OpenHardwareGate gate in report.open_hardware_gates)
                {
                    AddKvRow(gateCard, gate.gate_id, "Açık donanım kapısı", true);
                }
                rightModuleContent.Add(gateCard);
            }
        }

        private static void AddKvRow(VisualElement parent, string key, string value, bool warnTone)
        {
            VisualElement row = new VisualElement();
            row.AddToClassList("kv-row");

            Label k = new Label(key);
            k.AddToClassList("kv-key");
            row.Add(k);

            Label v = new Label(string.IsNullOrEmpty(value) ? "—" : value);
            v.AddToClassList(warnTone ? "kv-val-warn" : "kv-val");
            row.Add(v);

            parent.Add(row);
        }

        private static void AddKpiCard(VisualElement grid, string label, string value)
        {
            VisualElement card = new VisualElement();
            card.AddToClassList("kpi-card");

            Label l = new Label(label);
            l.AddToClassList("kpi-label");
            card.Add(l);

            Label v = new Label(value);
            v.AddToClassList("kpi-value");
            card.Add(v);

            grid.Add(card);
        }

        private static string FormatMetric(double value, string unit)
        {
            return string.Format(CultureInfo.InvariantCulture, "{0:0.###} {1}", value, unit);
        }

        public void Dispose()
        {
            if (root != null) root.Clear();
            DestroySafe(runtimePanelSettings);
            runtimePanelSettings = null;
            DestroySafe(fallbackTheme);
            fallbackTheme = null;
        }

        private static void DestroySafe(UnityEngine.Object obj)
        {
            if (obj == null) return;
            if (Application.isPlaying)
            {
                UnityEngine.Object.Destroy(obj);
            }
            else
            {
                UnityEngine.Object.DestroyImmediate(obj);
            }
        }
    }
}
