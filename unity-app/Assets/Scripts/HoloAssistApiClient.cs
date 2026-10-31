using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Networking;
using HoloAssist.Client;

[ExecuteAlways]
public class HoloAssistApiClient : MonoBehaviour
{
    [Header("API Yapılandırması")]
    [SerializeField] private string baseUrl = "http://127.0.0.1:8001";

    private WorkstationModule currentModule = WorkstationModule.Safety;
    private string selectedVisionKey = "reference";
    private string selectedSafetyKey = "information";
    private string selectedSensorKey = "current";
    private string selectedDiagKey = "complete";

    // Live server health & readiness
    private bool serverOnline;
    private string serverHealthText = "Kontrol ediliyor…";
    private string storageStatusText = "Kontrol ediliyor…";

    // Generation counters to prevent stale async responses overwriting newer selections
    private int visionGeneration;
    private int safetyGeneration;
    private int sensorGeneration;
    private int diagGeneration;
    private int benchGeneration;

    // Vision state (Week 3)
    private bool visionLoading;
    private string visionError = string.Empty;
    private VisionDemoPayload currentVisionPayload;

    // Safety & Spatial state (Weeks 6, 8, 9)
    private bool safetyLoading;
    private string safetyHttpBadge = "Bekleniyor…";
    private bool safetyHttpOk;
    private string safetyVerdictTitle = "Değerlendirme bekleniyor";
    private string safetyVerdictBody = "";
    private string safetyTone = "neutral";
    private SafetyReport currentSafetyReport;
    private SpatialProjectionReport currentSpatialReport;
    private string lastReqJson = "{}";
    private string lastResJson = "{}";
    private Coroutine walkthroughCoroutine;

    // Sensor state (Week 5)
    private bool sensorLoading;
    private string sensorError = string.Empty;
    private SensorDemoPayload currentSensorPayload;

    // Diagnostic state (Weeks 4-6)
    private bool diagLoading;
    private string diagError = string.Empty;
    private DiagnosticReport currentDiagReport;

    // Benchmark state (Weeks 10-12)
    private bool benchLoading;
    private string benchError = string.Empty;
    private SyntheticBenchmarkReport currentBenchReport;

    // Export state
    private bool exportRunning;
    private string exportStatusMessage = string.Empty;

    // Modular 3D Rig, Chart Renderer & UI Toolkit View
    private readonly HoloAssistMotorRig3D motorRig = new HoloAssistMotorRig3D();
    private readonly HoloAssistChartRenderer chartRenderer = new HoloAssistChartRenderer();
    private readonly HoloAssistUiToolkitView uiView = new HoloAssistUiToolkitView();
    private Camera sceneCamera;
    private GameObject runtimeEventSystemObject;
    private bool runtimeUiInitialized;

    private void OnEnable()
    {
        ResolveSceneCamera();
        if (!Application.isPlaying)
        {
            motorRig.InitializeSceneAndRig(sceneCamera, dontSaveInScene: true);
            motorRig.SetHighlightedPart("demo-label", false);
        }
    }

    private void Awake()
    {
        if (!Application.isPlaying) return;

        Application.runInBackground = true;
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            baseUrl = "http://127.0.0.1:8001";
        }
        EnsureRuntimeEventSystem();
    }

    private void ResolveSceneCamera()
    {
        if (sceneCamera == null)
        {
            sceneCamera = Camera.main;
        }
        if (sceneCamera == null)
        {
            sceneCamera = FindFirstObjectByType<Camera>();
        }
        if (sceneCamera != null)
        {
            sceneCamera.rect = new Rect(0f, 0f, 1f, 1f);
        }
    }

    private void EnsureRuntimeEventSystem()
    {
        if (!Application.isPlaying) return;
        if (EventSystem.current != null || FindFirstObjectByType<EventSystem>() != null)
        {
            return;
        }

        runtimeEventSystemObject = new GameObject("HoloAssist_EventSystem");
        runtimeEventSystemObject.AddComponent<EventSystem>();
        runtimeEventSystemObject.AddComponent<StandaloneInputModule>();
    }

    private void Start()
    {
        if (!Application.isPlaying) return;

        EnsureRuntimeEventSystem();
        ResolveSceneCamera();

        motorRig.Dispose();
        motorRig.InitializeSceneAndRig(sceneCamera, dontSaveInScene: false);

        uiView.Initialize(gameObject);
        runtimeUiInitialized = true;
        BindUiViewEvents();
        RefreshViewState();

        StartCoroutine(BootstrapConnectionCoroutine());
    }

    private void BindUiViewEvents()
    {
        uiView.OnPortSelected += url =>
        {
            StopActiveWalkthrough();
            baseUrl = url;
            RefreshViewState();
            RefreshAllActiveData();
        };

        uiView.OnRefreshRequested += () =>
        {
            StopActiveWalkthrough();
            RefreshAllActiveData();
        };

        uiView.OnOpenWebPlatform += () => Application.OpenURL("http://127.0.0.1:8001/demo");

        uiView.OnModuleSelected += SelectModule;

        uiView.OnVisionScenarioSelected += key =>
        {
            StopActiveWalkthrough();
            LoadVision(key);
        };

        uiView.OnSafetyScenarioSelected += key =>
        {
            StopActiveWalkthrough();
            SelectSafetyScenario(key);
        };

        uiView.OnRunSafetyWalkthroughRequested += StartSafetyWalkthrough;

        uiView.OnSensorSelected += key =>
        {
            StopActiveWalkthrough();
            LoadSensor(key);
        };

        uiView.OnDiagnosticSelected += key =>
        {
            StopActiveWalkthrough();
            LoadDiagnostic(key);
        };

        uiView.OnBenchmarkRefreshRequested += () =>
        {
            StopActiveWalkthrough();
            LoadBenchmark();
        };

        uiView.OnResetCameraRequested += () => motorRig.ResetOrbit(sceneCamera);
        uiView.OnToggleSpinRequested += ToggleShaftSpin;

        uiView.OnViewportOrbitDelta += delta => motorRig.ApplyOrbitDelta(delta, sceneCamera);
        uiView.OnViewportZoomDelta += scrollY => motorRig.ApplyZoomDelta(scrollY, sceneCamera);
        uiView.OnExportRequested += TriggerAuditExport;
    }

    private void SelectModule(WorkstationModule mod)
    {
        currentModule = mod;
        RefreshViewState();
        if (mod == WorkstationModule.Vision)
        {
            if (currentVisionPayload == null && !visionLoading)
            {
                LoadVision(selectedVisionKey);
            }
            else if (currentVisionPayload != null)
            {
                ApplyVisionHighlight(currentVisionPayload);
            }
        }
        else if (mod == WorkstationModule.Safety)
        {
            if (currentSafetyReport != null)
            {
                string reqTracking = selectedSafetyKey == "tracking" ? "lost" : "tracked";
                ApplySafetyReportToState(currentSafetyReport, reqTracking);
            }
            else if (!safetyLoading)
            {
                SelectSafetyScenario(selectedSafetyKey);
            }
        }
        else if (mod == WorkstationModule.Sensors && currentSensorPayload == null && !sensorLoading)
        {
            LoadSensor(selectedSensorKey);
        }
        else if (mod == WorkstationModule.Diagnostic && currentDiagReport == null && !diagLoading)
        {
            LoadDiagnostic(selectedDiagKey);
        }
        else if (mod == WorkstationModule.Benchmark && currentBenchReport == null && !benchLoading)
        {
            LoadBenchmark();
        }
    }

    private void ToggleShaftSpin()
    {
        motorRig.SpinShaftPreview = !motorRig.SpinShaftPreview;
        uiView.SetSpinButtonState(motorRig.SpinShaftPreview);
    }

    private void Update()
    {
        if (!Application.isPlaying) return;

        HandleKeyboardShortcuts();
        motorRig.TickAnimation(Time.deltaTime);
        if (runtimeUiInitialized)
        {
            bool busy = currentModule == WorkstationModule.Vision ? visionLoading : safetyLoading;
            uiView.SyncCameraViewportAndSpatialCallout(sceneCamera, motorRig, currentModule, busy);
        }
    }

    private void HandleKeyboardShortcuts()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1)) SelectModule(WorkstationModule.Vision);
        else if (Input.GetKeyDown(KeyCode.Alpha2)) SelectModule(WorkstationModule.Safety);
        else if (Input.GetKeyDown(KeyCode.Alpha3)) SelectModule(WorkstationModule.Sensors);
        else if (Input.GetKeyDown(KeyCode.Alpha4)) SelectModule(WorkstationModule.Diagnostic);
        else if (Input.GetKeyDown(KeyCode.Alpha5)) SelectModule(WorkstationModule.Benchmark);
        else if (Input.GetKeyDown(KeyCode.R)) motorRig.ResetOrbit(sceneCamera);
        else if (Input.GetKeyDown(KeyCode.Space)) ToggleShaftSpin();
    }

    private void OnDisable()
    {
        if (!Application.isPlaying)
        {
            motorRig.Dispose();
        }
    }

    private void OnDestroy()
    {
        if (sceneCamera != null)
        {
            sceneCamera.rect = new Rect(0f, 0f, 1f, 1f);
        }
        if (runtimeUiInitialized)
        {
            uiView.Dispose();
            runtimeUiInitialized = false;
        }
        motorRig.Dispose();
        chartRenderer.Dispose();
        if (runtimeEventSystemObject != null)
        {
            if (Application.isPlaying)
            {
                Destroy(runtimeEventSystemObject);
            }
            else
            {
                DestroyImmediate(runtimeEventSystemObject);
            }
            runtimeEventSystemObject = null;
        }
    }

    private void RefreshViewState()
    {
        if (!runtimeUiInitialized) return;

        uiView.SetServerStatus(serverOnline, serverHealthText, storageStatusText, baseUrl);
        uiView.SetSpinButtonState(motorRig.SpinShaftPreview);
        uiView.SetExportSelectionPills(selectedSafetyKey, selectedSensorKey, selectedDiagKey);
        uiView.SetExportStatus(exportRunning, exportStatusMessage);
        uiView.RenderLeftNavigation(currentModule, selectedSafetyKey, selectedSensorKey, selectedDiagKey, selectedVisionKey);

        if (currentModule == WorkstationModule.Vision)
        {
            uiView.RenderVisionInspector(visionLoading, visionError, currentVisionPayload);
        }
        else if (currentModule == WorkstationModule.Safety)
        {
            uiView.RenderSafetyInspector(
                safetyHttpOk,
                safetyHttpBadge,
                safetyTone,
                safetyVerdictTitle,
                safetyVerdictBody,
                currentSafetyReport,
                currentSpatialReport,
                lastReqJson,
                lastResJson);
        }
        else if (currentModule == WorkstationModule.Sensors)
        {
            uiView.RenderSensorInspector(
                sensorLoading,
                sensorError,
                currentSensorPayload,
                chartRenderer.CurrentTexture);
        }
        else if (currentModule == WorkstationModule.Diagnostic)
        {
            uiView.RenderDiagnosticInspector(
                diagLoading,
                diagError,
                currentDiagReport);
        }
        else
        {
            uiView.RenderBenchmarkInspector(
                benchLoading,
                benchError,
                currentBenchReport);
        }
    }

    private IEnumerator BootstrapConnectionCoroutine()
    {
        using (UnityWebRequest probe = UnityWebRequest.Get("http://127.0.0.1:8001/ready"))
        {
            probe.timeout = 2;
            yield return probe.SendWebRequest();
            if (probe.result == UnityWebRequest.Result.Success && probe.responseCode == 200)
            {
                baseUrl = "http://127.0.0.1:8001";
                uiView.SetServerStatus(true, "API Çevrimiçi (v1.0 · sentetik)", storageStatusText, baseUrl);
            }
        }

        RefreshAllActiveData();
    }

    public void RefreshAllActiveData()
    {
        StartCoroutine(CheckHealthAndReadinessCoroutine());
        SelectSafetyScenario(selectedSafetyKey);
        if (currentModule == WorkstationModule.Vision)
        {
            LoadVision(selectedVisionKey);
        }
        else if (currentModule == WorkstationModule.Sensors)
        {
            LoadSensor(selectedSensorKey);
        }
        else if (currentModule == WorkstationModule.Diagnostic)
        {
            LoadDiagnostic(selectedDiagKey);
        }
        else if (currentModule == WorkstationModule.Benchmark)
        {
            LoadBenchmark();
        }
    }

    private IEnumerator CheckHealthAndReadinessCoroutine()
    {
        using (UnityWebRequest hReq = UnityWebRequest.Get(baseUrl + "/health"))
        {
            hReq.timeout = 5;
            yield return hReq.SendWebRequest();
            if (hReq.result == UnityWebRequest.Result.Success)
            {
                HealthResponse h = JsonUtility.FromJson<HealthResponse>(hReq.downloadHandler.text);
                if (h != null && h.schema_version == "1.0" && !h.guidance_allowed)
                {
                    serverOnline = true;
                    serverHealthText = "API Çevrimiçi (v1.0 · sentetik)";
                }
                else
                {
                    serverOnline = false;
                    serverHealthText = "Şema uyuşmazlığı";
                }
            }
            else
            {
                serverOnline = false;
                serverHealthText = "API erişilemiyor";
            }
        }

        using (UnityWebRequest rReq = UnityWebRequest.Get(baseUrl + "/ready"))
        {
            rReq.timeout = 5;
            yield return rReq.SendWebRequest();
            if (rReq.result == UnityWebRequest.Result.Success)
            {
                ReadinessResponse r = JsonUtility.FromJson<ReadinessResponse>(rReq.downloadHandler.text);
                if (r != null && r.schema_version == "1.0")
                {
                    storageStatusText = r.storage == "reachable" ? "Depo: Erişilebilir" : "Depo: Salt Değerlendirme";
                }
            }
            else
            {
                storageStatusText = "Depo: 503 / Kapalı";
            }
        }

        uiView.SetServerStatus(serverOnline, serverHealthText, storageStatusText, baseUrl);
    }

    // --- Module 01: Equipment & Reference Recognition (Week 3) ---
    public void LoadVision(string visionScenario)
    {
        selectedVisionKey = visionScenario;
        int gen = ++visionGeneration;
        visionLoading = true;
        visionError = string.Empty;
        currentVisionPayload = null;
        motorRig.SetHighlightedPart(string.Empty, false);
        RefreshViewState();
        StartCoroutine(FetchVisionCoroutine(visionScenario, gen));
    }

    private IEnumerator FetchVisionCoroutine(string visionScenario, int gen)
    {
        using (UnityWebRequest req = UnityWebRequest.Get(baseUrl + "/v1/demo/vision/" + visionScenario))
        {
            req.timeout = 10;
            yield return req.SendWebRequest();
            if (gen != visionGeneration) yield break;
            visionLoading = false;

            if (req.result != UnityWebRequest.Result.Success)
            {
                visionError = "Görüntü tanıma demosu alınamadı; ekipman kimliği ve 3D vurgu gizlendi.";
                motorRig.SetHighlightedPart(string.Empty, false);
                RefreshViewState();
                yield break;
            }

            VisionDemoPayload payload = JsonUtility.FromJson<VisionDemoPayload>(req.downloadHandler.text);
            if (!HoloAssistContractValidator.ValidateVisionPayload(payload, visionScenario, out string err))
            {
                visionError = "Görüntü sözleşme doğrulaması reddedildi: " + err;
                motorRig.SetHighlightedPart(string.Empty, false);
                RefreshViewState();
                yield break;
            }

            currentVisionPayload = payload;
            if (currentModule == WorkstationModule.Vision)
            {
                ApplyVisionHighlight(payload);
            }
            RefreshViewState();
        }
    }

    private void ApplyVisionHighlight(VisionDemoPayload payload)
    {
        if (payload != null && payload.status == "matched" && payload.equipment_id == "synthetic-rig")
        {
            motorRig.SetHighlightedPart("demo-label", false);
        }
        else
        {
            motorRig.SetHighlightedPart(string.Empty, false);
        }
    }

    // --- Module 02: Safety Gate & 3D Spatial Projection (Weeks 6, 8, 9) ---
    private void StopActiveWalkthrough()
    {
        if (walkthroughCoroutine != null)
        {
            StopCoroutine(walkthroughCoroutine);
            walkthroughCoroutine = null;
        }
    }

    private void StartSafetyWalkthrough()
    {
        StopActiveWalkthrough();
        currentModule = WorkstationModule.Safety;
        walkthroughCoroutine = StartCoroutine(RunSafetyWalkthroughCoroutine());
    }

    private IEnumerator RunSafetyWalkthroughCoroutine()
    {
        string[] sequence = { "information", "critical", "tracking", "unknown", "injection", "information" };
        for (int i = 0; i < sequence.Length; i++)
        {
            SelectSafetyScenario(sequence[i]);
            if (i < sequence.Length - 1)
            {
                yield return new WaitForSeconds(1.65f);
            }
        }
        walkthroughCoroutine = null;
    }

    public void SelectSafetyScenario(string scenarioKey)
    {
        selectedSafetyKey = scenarioKey;
        int gen = ++safetyGeneration;
        safetyLoading = true;
        currentSafetyReport = null;
        currentSpatialReport = null;
        safetyHttpBadge = "İstek gönderiliyor…";
        safetyVerdictTitle = "Güvenlik kapısı değerlendiriliyor…";
        safetyVerdictBody = "Sunucu kaynak ve katalog kontrolünü çalıştırıyor.";
        safetyTone = "neutral";

        if (currentModule == WorkstationModule.Safety)
        {
            motorRig.SetHighlightedPart(string.Empty, false);
        }

        if (scenarioKey == "injection")
        {
            string rawInjectionJson =
                "{\n" +
                "  \"schema_version\": \"1.0\",\n" +
                "  \"review_id\": \"unity-demo-injection\",\n" +
                "  \"analysis_request_id\": \"synthetic-analysis-demo-1\",\n" +
                "  \"tracking_status\": \"tracked\",\n" +
                "  \"approval\": \"client-bypass-attempt\",\n" +
                "  \"steps\": [\n" +
                "    {\n" +
                "      \"step_id\": \"step-1\",\n" +
                "      \"instruction_id\": \"demo-critical\",\n" +
                "      \"part_id\": \"demo-critical-part\"\n" +
                "    }\n" +
                "  ]\n" +
                "}";
            RefreshViewState();
            StartCoroutine(PostSafetyRawCoroutine(rawInjectionJson, "tracked", true, gen));
            return;
        }

        string instruction = "demo-information";
        string part = "demo-label";
        string tracking = "tracked";

        if (scenarioKey == "critical")
        {
            instruction = "demo-critical";
            part = "demo-critical-part";
        }
        else if (scenarioKey == "tracking")
        {
            tracking = "lost";
        }
        else if (scenarioKey == "unknown")
        {
            part = "unknown-part";
        }

        SafetyRequest req = new SafetyRequest
        {
            schema_version = "1.0",
            review_id = "unity-demo-" + scenarioKey,
            analysis_request_id = "synthetic-analysis-demo-1",
            tracking_status = tracking,
            steps = new List<StepRequest>
            {
                new StepRequest
                {
                    step_id = "step-1",
                    instruction_id = instruction,
                    part_id = part
                }
            }
        };

        string prettyReq = JsonUtility.ToJson(req, true);
        RefreshViewState();
        StartCoroutine(PostSafetyRawCoroutine(prettyReq, tracking, false, gen));
    }

    private IEnumerator PostSafetyRawCoroutine(string jsonPayload, string requestedTracking, bool expect422, int gen)
    {
        lastReqJson = jsonPayload;
        lastResJson = "// Yanıt bekleniyor…";
        Stopwatch sw = Stopwatch.StartNew();

        using (UnityWebRequest req = new UnityWebRequest(baseUrl + "/v1/demo/safety/evaluate", "POST"))
        {
            byte[] raw = Encoding.UTF8.GetBytes(jsonPayload);
            req.uploadHandler = new UploadHandlerRaw(raw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            req.timeout = 10;

            yield return req.SendWebRequest();
            sw.Stop();
            if (gen != safetyGeneration) yield break;

            safetyLoading = false;
            string bodyText = req.downloadHandler != null ? req.downloadHandler.text : string.Empty;
            lastResJson = bodyText;

            if (expect422 && req.responseCode == 422)
            {
                ApiErrorResponse apiErr = JsonUtility.FromJson<ApiErrorResponse>(bodyText);
                bool sanitized = !bodyText.Contains("client-bypass-attempt");
                if (apiErr != null && apiErr.schema_version == "1.0" && apiErr.code == "invalid_request" && sanitized)
                {
                    safetyHttpOk = false;
                    safetyHttpBadge = $"HTTP 422 · {sw.ElapsedMilliseconds} ms";
                    safetyTone = "blocked";
                    safetyVerdictTitle = "Yetkisiz İstemci Alanı Reddedildi (422)";
                    safetyVerdictBody = "İstemcinin gönderdiği 'approval' alanı extra='forbid' kuralıyla reddedildi; gönderilen değer yanıta yansıtılmadı.";
                    if (currentModule == WorkstationModule.Safety) motorRig.SetHighlightedPart(string.Empty, false);
                    RefreshViewState();
                    yield break;
                }
            }

            if (req.result != UnityWebRequest.Result.Success)
            {
                safetyHttpOk = false;
                safetyHttpBadge = $"Hata ({req.responseCode})";
                safetyTone = "blocked";
                safetyVerdictTitle = "API Yanıtı Alınamadı";
                safetyVerdictBody = "Sunucu bağlantısını kontrol edin. Güvenlik gereği önceki kart ve 3D parça vurgusu kaldırıldı.";
                if (currentModule == WorkstationModule.Safety) motorRig.SetHighlightedPart(string.Empty, false);
                RefreshViewState();
                yield break;
            }

            SafetyReport report = JsonUtility.FromJson<SafetyReport>(bodyText);
            if (!HoloAssistContractValidator.ValidateSafetyReport(report, out string valErr))
            {
                safetyHttpOk = false;
                safetyHttpBadge = "Sözleşme Reddi";
                safetyTone = "blocked";
                safetyVerdictTitle = "İstemci Şema Doğrulaması Başarısız";
                safetyVerdictBody = "Sunucu yanıtı sözleşme kurallarını karşılamadı (" + valErr + "). Gösterim engellendi.";
                if (currentModule == WorkstationModule.Safety) motorRig.SetHighlightedPart(string.Empty, false);
                RefreshViewState();
                yield break;
            }

            currentSafetyReport = report;
            safetyHttpOk = true;
            safetyHttpBadge = $"HTTP 200 · {sw.ElapsedMilliseconds} ms";

            if (!expect422)
            {
                using (UnityWebRequest spReq = UnityWebRequest.Get(baseUrl + "/v1/demo/spatial/" + selectedSafetyKey))
                {
                    spReq.timeout = 6;
                    yield return spReq.SendWebRequest();
                    if (gen != safetyGeneration) yield break;
                    if (spReq.result == UnityWebRequest.Result.Success)
                    {
                        SpatialProjectionReport sp = JsonUtility.FromJson<SpatialProjectionReport>(spReq.downloadHandler.text);
                        if (HoloAssistContractValidator.ValidateSpatialReport(sp, out _))
                        {
                            currentSpatialReport = sp;
                        }
                    }
                }
            }

            ApplySafetyReportToState(report, requestedTracking);
            RefreshViewState();
        }
    }

    private void ApplySafetyReportToState(SafetyReport report, string requestedTracking)
    {
        if (report.status == "display_allowed")
        {
            safetyTone = "ok";
            safetyVerdictTitle = "Bilgi Kartı Gösterilebilir (Sentetik)";
            safetyVerdictBody = "Kaynak alıntısı, sayfa/bölüm ve 3D parça kimliği doğrulandı. Fiziksel müdahale izni kapalıdır.";
        }
        else if (report.status == "needs_approval")
        {
            safetyTone = "warning";
            safetyVerdictTitle = "Kalıcı İnsan Onayı Gerekli";
            safetyVerdictBody = "Kritik adım metni ve alıntıları gizlendi. Yalnızca backend yetkili inceleyici kaydıyla değerlendirilebilir.";
        }
        else if (report.status == "needs_information")
        {
            safetyTone = "warning";
            safetyVerdictTitle = "Takip Kaybı · Kart ve 3D Ok Gizlendi";
            safetyVerdictBody = "Parça takibi 'lost' olduğu için eski bilgi kartı ve 3D parça işareti güvenlik gereği kaldırıldı.";
        }
        else
        {
            safetyTone = "blocked";
            safetyVerdictTitle = "Gösterim Engellendi";
            safetyVerdictBody = "Parça veya talimat kimliği doğrulanmış katalogla eşleşmedi; metin gösterilmiyor.";
        }

        if (currentModule == WorkstationModule.Safety)
        {
            string verifiedPart = HoloAssistContractValidator.ResolveVerified3DPart(report, requestedTracking);
            bool isWarning = report.status != "display_allowed";
            motorRig.SetHighlightedPart(verifiedPart, isWarning);
        }
    }

    // --- Module 03: Sensor Telemetry (Week 5) ---
    public void LoadSensor(string sensorKey)
    {
        selectedSensorKey = sensorKey;
        int gen = ++sensorGeneration;
        sensorLoading = true;
        sensorError = string.Empty;
        currentSensorPayload = null;
        RefreshViewState();
        StartCoroutine(FetchSensorCoroutine(sensorKey, gen));
    }

    private IEnumerator FetchSensorCoroutine(string sensorKey, int gen)
    {
        using (UnityWebRequest req = UnityWebRequest.Get(baseUrl + "/v1/demo/sensors/" + sensorKey))
        {
            req.timeout = 10;
            yield return req.SendWebRequest();
            if (gen != sensorGeneration) yield break;
            sensorLoading = false;

            if (req.result != UnityWebRequest.Result.Success)
            {
                sensorError = "Sensör demosu alınamadı. Önceki grafik gizlendi.";
                RefreshViewState();
                yield break;
            }

            SensorDemoPayload payload = JsonUtility.FromJson<SensorDemoPayload>(req.downloadHandler.text);
            if (!HoloAssistContractValidator.ValidateSensorPayload(payload, sensorKey, out string err))
            {
                sensorError = "Sensör sözleşme doğrulaması reddedildi: " + err;
                RefreshViewState();
                yield break;
            }

            currentSensorPayload = payload;
            if (payload.report.status == "summary_available")
            {
                chartRenderer.RenderSeries(payload);
            }
            RefreshViewState();
        }
    }

    // --- Module 04: Diagnostic Evidence Matrix (Weeks 4-6) ---
    public void LoadDiagnostic(string diagKey)
    {
        selectedDiagKey = diagKey;
        int gen = ++diagGeneration;
        diagLoading = true;
        diagError = string.Empty;
        currentDiagReport = null;
        RefreshViewState();
        StartCoroutine(FetchDiagnosticCoroutine(diagKey, gen));
    }

    private IEnumerator FetchDiagnosticCoroutine(string diagKey, int gen)
    {
        using (UnityWebRequest req = UnityWebRequest.Get(baseUrl + "/v1/demo/diagnostic/" + diagKey))
        {
            req.timeout = 10;
            yield return req.SendWebRequest();
            if (gen != diagGeneration) yield break;
            diagLoading = false;

            if (req.result != UnityWebRequest.Result.Success)
            {
                diagError = "Kaynaklı olasılık raporu alınamadı; önceki içerik gizlendi.";
                RefreshViewState();
                yield break;
            }

            DiagnosticReport report = JsonUtility.FromJson<DiagnosticReport>(req.downloadHandler.text);
            if (!HoloAssistContractValidator.ValidateDiagnosticReport(report, out string err))
            {
                diagError = "Olasılık şema doğrulaması reddedildi: " + err;
                RefreshViewState();
                yield break;
            }

            currentDiagReport = report;
            RefreshViewState();
        }
    }

    // --- Module 05: Reproducible Synthetic Benchmark (Weeks 10-12) ---
    public void LoadBenchmark()
    {
        int gen = ++benchGeneration;
        benchLoading = true;
        benchError = string.Empty;
        currentBenchReport = null;
        RefreshViewState();
        StartCoroutine(FetchBenchmarkCoroutine(gen));
    }

    private IEnumerator FetchBenchmarkCoroutine(int gen)
    {
        using (UnityWebRequest req = UnityWebRequest.Get(baseUrl + "/v1/demo/evaluation"))
        {
            req.timeout = 15;
            yield return req.SendWebRequest();
            if (gen != benchGeneration) yield break;
            benchLoading = false;

            if (req.result != UnityWebRequest.Result.Success)
            {
                benchError = "Sentetik benchmark raporu alınamadı; önceki metrikler gizlendi.";
                RefreshViewState();
                yield break;
            }

            SyntheticBenchmarkReport report = JsonUtility.FromJson<SyntheticBenchmarkReport>(req.downloadHandler.text);
            if (!HoloAssistContractValidator.ValidateBenchmarkReport(report, out string err))
            {
                benchError = "Benchmark sözleşme doğrulaması reddedildi: " + err;
                RefreshViewState();
                yield break;
            }

            currentBenchReport = report;
            RefreshViewState();
        }
    }

    // --- Independent Audit Export ---
    private void TriggerAuditExport()
    {
        if (exportRunning) return;
        string safeSafety = (selectedSafetyKey == "information" ||
                             selectedSafetyKey == "critical" ||
                             selectedSafetyKey == "tracking" ||
                             selectedSafetyKey == "unknown")
            ? selectedSafetyKey
            : "information";
        StartCoroutine(DownloadAuditReportCoroutine(safeSafety, selectedSensorKey, selectedDiagKey));
    }

    private IEnumerator DownloadAuditReportCoroutine(string safetyKey, string sensorKey, string diagKey)
    {
        exportRunning = true;
        exportStatusMessage = "Sunucuda yeniden değerlendiriliyor…";
        uiView.SetExportStatus(exportRunning, exportStatusMessage);
        string url = $"{baseUrl}/v1/demo/report?safety={safetyKey}&sensor={sensorKey}&diagnostic={diagKey}";

        using (UnityWebRequest req = UnityWebRequest.Get(url))
        {
            req.timeout = 12;
            yield return req.SendWebRequest();
            exportRunning = false;

            if (req.result != UnityWebRequest.Result.Success)
            {
                exportStatusMessage = "Rapor alınamadı; dosya oluşturulmadı.";
                uiView.SetExportStatus(exportRunning, exportStatusMessage);
                yield break;
            }

            string json = req.downloadHandler.text;
            DemoExportEnvelope env = JsonUtility.FromJson<DemoExportEnvelope>(json);
            if (env == null || env.schema_version != "1.0" || env.scope != "synthetic_demo" || !env.independent_sections || env.guidance_allowed)
            {
                exportStatusMessage = "Dışa aktarım şeması geçersiz; kaydedilmedi.";
                uiView.SetExportStatus(exportRunning, exportStatusMessage);
                yield break;
            }

            string fileName = $"holoassist-demo-{env.export_id}.json";
            string targetPath = Path.Combine(Application.persistentDataPath, fileName);
            File.WriteAllText(targetPath, json, Encoding.UTF8);
            exportStatusMessage = "Kaydedildi: " + fileName;
            uiView.SetExportStatus(exportRunning, exportStatusMessage);
        }
    }
}
