using System.Collections.Generic;
using UnityEngine;

namespace HoloAssist.Client
{
    public class HoloAssistMotorRig3D
    {
        private GameObject rigRoot;
        private GameObject rimLightObj;
        private GameObject spatialMarkerGroup;
        private Transform spatialArrowBobGroup;
        private Transform rotorShaftGroup;
        private Transform labelAnchor;
        private Transform criticalAnchor;
        private LineRenderer calloutLine;

        private readonly List<Renderer> labelRenderers = new List<Renderer>();
        private readonly List<Color> labelBaseColors = new List<Color>();
        private readonly List<Renderer> criticalRenderers = new List<Renderer>();
        private readonly List<Color> criticalBaseColors = new List<Color>();
        private readonly List<Renderer> markerRenderers = new List<Renderer>();
        private readonly List<Material> createdMaterials = new List<Material>();

        private Material baseTemplateMaterial;
        private string activePartId = string.Empty;
        private Color activeHighlightColor = new Color(0.20f, 0.83f, 0.60f);
        private float markerAnimPhase;

        // Orbit camera state
        private float orbitYaw = -34f;
        private float orbitPitch = 21f;
        private float orbitDistance = 3.42f;
        private readonly Vector3 orbitTarget = new Vector3(0f, 0.18f, 0f);

        public bool SpinShaftPreview { get; set; } = true;
        public string ActivePartId => activePartId;
        public bool IsCalloutLineVisible => calloutLine != null && calloutLine.enabled;
        public bool IsSpatialMarkerVisible => spatialMarkerGroup != null && spatialMarkerGroup.activeSelf;

        public void InitializeSceneAndRig(Camera targetCamera, bool dontSaveInScene = false)
        {
            if (rigRoot != null) return;

            CleanupOrphanedSceneObjects();
            ConfigureStudioEnvironment(targetCamera, dontSaveInScene);

            rigRoot = new GameObject("HoloAssist_SyntheticMotorRig_3D");
            rigRoot.transform.position = Vector3.zero;

            // Template material extracted from a temporary primitive so shader always matches pipeline
            GameObject temp = GameObject.CreatePrimitive(PrimitiveType.Cube);
            baseTemplateMaterial = new Material(temp.GetComponent<Renderer>().sharedMaterial);
            SafeDestroy(temp);

            BuildWorkbenchAndBase();
            BuildStatorAndNameplate();
            BuildCriticalCommutatorAssembly();
            BuildFrontRotorAndShaft();
            BuildCalloutLine();
            BuildSpatialGuidanceMarker();

            if (dontSaveInScene)
            {
                ApplyDontSaveRecursive(rigRoot);
            }

            UpdateCameraTransform(targetCamera);
        }

        private static void CleanupOrphanedSceneObjects()
        {
            GameObject oldRig = GameObject.Find("HoloAssist_SyntheticMotorRig_3D");
            if (oldRig != null)
            {
                SafeDestroy(oldRig);
            }

            GameObject oldRim = GameObject.Find("Studio_RimLight");
            if (oldRim != null)
            {
                SafeDestroy(oldRim);
            }
        }

        private static void ApplyDontSaveRecursive(GameObject rootObj)
        {
            if (rootObj == null) return;
            HideFlags flags = HideFlags.DontSaveInEditor | HideFlags.DontSaveInBuild;
            rootObj.hideFlags = flags;
            foreach (Transform child in rootObj.GetComponentsInChildren<Transform>(true))
            {
                child.gameObject.hideFlags = flags;
            }
        }

        private void ConfigureStudioEnvironment(Camera cam, bool dontSaveInScene)
        {
            if (cam != null)
            {
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.039f, 0.086f, 0.122f, 1f);
                cam.fieldOfView = 35f;
                cam.nearClipPlane = 0.1f;
                cam.farClipPlane = 50f;
            }

            RenderSettings.ambientLight = new Color(0.28f, 0.36f, 0.42f);

            Light[] lights = Object.FindObjectsByType<Light>(FindObjectsSortMode.None);
            if (lights != null && lights.Length > 0)
            {
                lights[0].transform.rotation = Quaternion.Euler(44f, -38f, 0f);
                lights[0].color = new Color(0.95f, 0.98f, 1.0f);
                lights[0].intensity = 1.15f;
            }

            rimLightObj = new GameObject("Studio_RimLight");
            if (dontSaveInScene)
            {
                rimLightObj.hideFlags = HideFlags.DontSaveInEditor | HideFlags.DontSaveInBuild;
            }
            Light rim = rimLightObj.AddComponent<Light>();
            rim.type = LightType.Directional;
            rim.transform.rotation = Quaternion.Euler(26f, 145f, 0f);
            rim.color = new Color(0.35f, 0.78f, 0.92f);
            rim.intensity = 0.65f;
        }

        private void BuildWorkbenchAndBase()
        {
            Color slatePedestal = new Color(0.07f, 0.13f, 0.18f);
            Color gridLineColor = new Color(0.13f, 0.24f, 0.31f);
            Color baseMetal = new Color(0.15f, 0.23f, 0.29f);
            Color brass = new Color(0.55f, 0.63f, 0.68f);

            // Studio workbench slab
            CreatePart(PrimitiveType.Cube, "Workbench_Slab", rigRoot.transform,
                new Vector3(0f, -0.30f, 0f), new Vector3(3.2f, 0.08f, 2.0f), Quaternion.identity, slatePedestal);

            // Subtle technical grid lines on workbench
            for (int i = -5; i <= 5; i++)
            {
                CreatePart(PrimitiveType.Cube, "Grid_X_" + i, rigRoot.transform,
                    new Vector3(i * 0.26f, -0.258f, 0f), new Vector3(0.008f, 0.003f, 1.85f), Quaternion.identity, gridLineColor);
            }
            for (int j = -3; j <= 3; j++)
            {
                CreatePart(PrimitiveType.Cube, "Grid_Z_" + j, rigRoot.transform,
                    new Vector3(0f, -0.258f, j * 0.26f), new Vector3(2.95f, 0.003f, 0.008f), Quaternion.identity, gridLineColor);
            }

            // Motor rig machined baseplate
            CreatePart(PrimitiveType.Cube, "Rig_Baseplate", rigRoot.transform,
                new Vector3(0f, -0.20f, 0f), new Vector3(1.75f, 0.09f, 0.92f), Quaternion.identity, baseMetal);

            // Cradle Saddle Mounts
            CreatePart(PrimitiveType.Cube, "Saddle_Rear", rigRoot.transform,
                new Vector3(-0.32f, -0.04f, 0f), new Vector3(0.16f, 0.24f, 0.56f), Quaternion.identity, baseMetal);
            CreatePart(PrimitiveType.Cube, "Saddle_Front", rigRoot.transform,
                new Vector3(0.32f, -0.04f, 0f), new Vector3(0.16f, 0.24f, 0.56f), Quaternion.identity, baseMetal);

            // Corner bolts
            float[] bx = { -0.76f, 0.76f };
            float[] bz = { -0.36f, 0.36f };
            foreach (float x in bx)
            {
                foreach (float z in bz)
                {
                    CreatePart(PrimitiveType.Cylinder, "Bolt", rigRoot.transform,
                        new Vector3(x, -0.145f, z), new Vector3(0.06f, 0.02f, 0.06f), Quaternion.identity, brass);
                }
            }
        }

        private void BuildStatorAndNameplate()
        {
            Color statorSteel = new Color(0.24f, 0.35f, 0.43f);
            Color finColor = new Color(0.20f, 0.30f, 0.37f);
            Quaternion horizontalZ = Quaternion.Euler(0f, 0f, 90f);

            // Main cylindrical stator shell
            CreatePart(PrimitiveType.Cylinder, "Stator_MainBody", rigRoot.transform,
                new Vector3(0f, 0.24f, 0f), new Vector3(0.68f, 0.46f, 0.68f), horizontalZ, statorSteel);

            // Cooling ribs along stator
            for (int i = -2; i <= 2; i++)
            {
                CreatePart(PrimitiveType.Cylinder, "Cooling_Rib_" + i, rigRoot.transform,
                    new Vector3(i * 0.15f, 0.24f, 0f), new Vector3(0.715f, 0.018f, 0.715f), horizontalZ, finColor);
            }

            // Verified Part: `demo-label` (Top Stator Nameplate Assembly)
            GameObject labelGroup = new GameObject("Part_demo-label");
            labelGroup.transform.SetParent(rigRoot.transform, false);

            Color plateFrameColor = new Color(0.12f, 0.24f, 0.30f);
            Color plateFaceColor = new Color(0.18f, 0.42f, 0.46f);
            Color plateTextStrip = new Color(0.68f, 0.86f, 0.88f);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cube, "Nameplate_Frame", labelGroup.transform,
                    new Vector3(0f, 0.59f, 0f), new Vector3(0.44f, 0.035f, 0.28f), Quaternion.identity, plateFrameColor),
                labelRenderers, labelBaseColors);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cube, "Nameplate_Surface", labelGroup.transform,
                    new Vector3(0f, 0.61f, 0f), new Vector3(0.39f, 0.015f, 0.23f), Quaternion.identity, plateFaceColor),
                labelRenderers, labelBaseColors);

            for (int line = -1; line <= 1; line++)
            {
                RegisterPartRenderer(
                    CreatePart(PrimitiveType.Cube, "Etched_Line_" + line, labelGroup.transform,
                        new Vector3(-0.02f, 0.621f, line * 0.055f), new Vector3(0.28f - (line + 1) * 0.03f, 0.006f, 0.018f),
                        Quaternion.identity, plateTextStrip),
                    labelRenderers, labelBaseColors);
            }

            GameObject anchorObj = new GameObject("Anchor_demo-label");
            anchorObj.transform.SetParent(labelGroup.transform, false);
            anchorObj.transform.localPosition = new Vector3(0f, 0.64f, 0f);
            labelAnchor = anchorObj.transform;
        }

        private void BuildCriticalCommutatorAssembly()
        {
            // Verified Part: `demo-critical-part` (Rear Commutator / Brush End-Bell & Power Terminals)
            GameObject critGroup = new GameObject("Part_demo-critical-part");
            critGroup.transform.SetParent(rigRoot.transform, false);

            Quaternion horizontalZ = Quaternion.Euler(0f, 0f, 90f);
            Color endBellDark = new Color(0.16f, 0.22f, 0.28f);
            Color brushHolderCol = new Color(0.26f, 0.31f, 0.36f);
            Color posCopper = new Color(0.82f, 0.46f, 0.16f);
            Color negBlue = new Color(0.22f, 0.54f, 0.78f);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cylinder, "Commutator_EndBell", critGroup.transform,
                    new Vector3(-0.56f, 0.24f, 0f), new Vector3(0.62f, 0.11f, 0.62f), horizontalZ, endBellDark),
                criticalRenderers, criticalBaseColors);

            // Top & Side Brush Inspection Caps
            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cylinder, "BrushCap_Top", critGroup.transform,
                    new Vector3(-0.56f, 0.57f, 0f), new Vector3(0.12f, 0.045f, 0.12f), Quaternion.identity, brushHolderCol),
                criticalRenderers, criticalBaseColors);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cylinder, "BrushCap_FrontSide", critGroup.transform,
                    new Vector3(-0.56f, 0.24f, -0.33f), new Vector3(0.12f, 0.045f, 0.12f), Quaternion.Euler(90f, 0f, 0f), brushHolderCol),
                criticalRenderers, criticalBaseColors);

            // Terminal Block & DC Binding Posts
            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cube, "Terminal_InsulatorBlock", critGroup.transform,
                    new Vector3(-0.70f, 0.24f, 0f), new Vector3(0.09f, 0.26f, 0.32f), Quaternion.identity, endBellDark),
                criticalRenderers, criticalBaseColors);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cylinder, "Terminal_Post_Positive", critGroup.transform,
                    new Vector3(-0.78f, 0.30f, -0.09f), new Vector3(0.065f, 0.055f, 0.065f), horizontalZ, posCopper),
                criticalRenderers, criticalBaseColors);

            RegisterPartRenderer(
                CreatePart(PrimitiveType.Cylinder, "Terminal_Post_Negative", critGroup.transform,
                    new Vector3(-0.78f, 0.18f, 0.09f), new Vector3(0.065f, 0.055f, 0.065f), horizontalZ, negBlue),
                criticalRenderers, criticalBaseColors);

            GameObject anchorObj = new GameObject("Anchor_demo-critical-part");
            anchorObj.transform.SetParent(critGroup.transform, false);
            anchorObj.transform.localPosition = new Vector3(-0.60f, 0.62f, 0f);
            criticalAnchor = anchorObj.transform;
        }

        private void BuildFrontRotorAndShaft()
        {
            Quaternion horizontalZ = Quaternion.Euler(0f, 0f, 90f);
            Color noseCone = new Color(0.22f, 0.33f, 0.41f);
            Color polishedShaft = new Color(0.76f, 0.83f, 0.87f);
            Color discCol = new Color(0.32f, 0.45f, 0.53f);

            // Front Bearing End-Bell
            CreatePart(PrimitiveType.Cylinder, "Front_EndBell", rigRoot.transform,
                new Vector3(0.54f, 0.24f, 0f), new Vector3(0.60f, 0.09f, 0.60f), horizontalZ, noseCone);
            CreatePart(PrimitiveType.Cylinder, "Bearing_Boss", rigRoot.transform,
                new Vector3(0.66f, 0.24f, 0f), new Vector3(0.26f, 0.05f, 0.26f), horizontalZ, noseCone);

            // Rotating Shaft + Encoder Disc Preview Group
            GameObject shaftGroup = new GameObject("Rotor_Shaft_Assembly");
            shaftGroup.transform.SetParent(rigRoot.transform, false);
            shaftGroup.transform.localPosition = new Vector3(0.88f, 0.24f, 0f);
            rotorShaftGroup = shaftGroup.transform;

            CreatePart(PrimitiveType.Cylinder, "Drive_Shaft", rotorShaftGroup,
                Vector3.zero, new Vector3(0.11f, 0.26f, 0.11f), horizontalZ, polishedShaft);

            CreatePart(PrimitiveType.Cylinder, "Encoder_Disc", rotorShaftGroup,
                new Vector3(0.06f, 0f, 0f), new Vector3(0.34f, 0.012f, 0.34f), horizontalZ, discCol);

            // Keyway Indicator Bar so rotation is visually legible
            CreatePart(PrimitiveType.Cube, "Keyway_Marker", rotorShaftGroup,
                new Vector3(0.14f, 0.06f, 0f), new Vector3(0.18f, 0.022f, 0.022f), Quaternion.identity,
                new Color(0.20f, 0.76f, 0.62f));
        }

        private void BuildCalloutLine()
        {
            GameObject lineObj = new GameObject("Spatial_Callout_Stem");
            lineObj.transform.SetParent(rigRoot.transform, false);
            calloutLine = lineObj.AddComponent<LineRenderer>();
            calloutLine.positionCount = 2;
            calloutLine.startWidth = 0.014f;
            calloutLine.endWidth = 0.014f;
            calloutLine.useWorldSpace = true;

            Shader lineShader = Shader.Find("Sprites/Default");
            Material lineMat = lineShader != null ? new Material(lineShader) : new Material(baseTemplateMaterial);
            createdMaterials.Add(lineMat);
            calloutLine.material = lineMat;
            calloutLine.enabled = false;
        }

        private void BuildSpatialGuidanceMarker()
        {
            // Representative 3D anchor reticle + downward directional pointer (Week 8-9 synthetic scope)
            spatialMarkerGroup = new GameObject("Spatial_Guidance_Marker_3D");
            spatialMarkerGroup.transform.SetParent(rigRoot.transform, false);
            markerRenderers.Clear();

            Color defaultMarkerCol = new Color(0.16f, 0.84f, 0.60f, 1f);

            // 4 cardinal reticle ticks on horizontal plane around anchor
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Reticle_North", spatialMarkerGroup.transform,
                new Vector3(0f, 0.015f, 0.15f), new Vector3(0.08f, 0.012f, 0.022f), Quaternion.identity, defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Reticle_South", spatialMarkerGroup.transform,
                new Vector3(0f, 0.015f, -0.15f), new Vector3(0.08f, 0.012f, 0.022f), Quaternion.identity, defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Reticle_East", spatialMarkerGroup.transform,
                new Vector3(0.15f, 0.015f, 0f), new Vector3(0.022f, 0.012f, 0.08f), Quaternion.identity, defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Reticle_West", spatialMarkerGroup.transform,
                new Vector3(-0.15f, 0.015f, 0f), new Vector3(0.022f, 0.012f, 0.08f), Quaternion.identity, defaultMarkerCol));

            // Bobbing 3D directional arrow pointing down at the verified anchor
            GameObject arrowGroup = new GameObject("Directional_Arrow_3D");
            arrowGroup.transform.SetParent(spatialMarkerGroup.transform, false);
            arrowGroup.transform.localPosition = new Vector3(0f, 0.15f, 0f);
            spatialArrowBobGroup = arrowGroup.transform;

            markerRenderers.Add(CreatePart(PrimitiveType.Cylinder, "Arrow_Shaft", spatialArrowBobGroup,
                new Vector3(0f, 0.08f, 0f), new Vector3(0.026f, 0.065f, 0.026f), Quaternion.identity, defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Arrow_Wing_L", spatialArrowBobGroup,
                new Vector3(-0.032f, 0.028f, 0f), new Vector3(0.085f, 0.018f, 0.022f), Quaternion.Euler(0f, 0f, -42f), defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Cube, "Arrow_Wing_R", spatialArrowBobGroup,
                new Vector3(0.032f, 0.028f, 0f), new Vector3(0.085f, 0.018f, 0.022f), Quaternion.Euler(0f, 0f, 42f), defaultMarkerCol));
            markerRenderers.Add(CreatePart(PrimitiveType.Sphere, "Anchor_Pin_Dot", spatialMarkerGroup.transform,
                new Vector3(0f, 0.015f, 0f), new Vector3(0.048f, 0.048f, 0.048f), Quaternion.identity, defaultMarkerCol));

            spatialMarkerGroup.SetActive(false);
        }

        private Renderer CreatePart(
            PrimitiveType type,
            string name,
            Transform parent,
            Vector3 localPos,
            Vector3 localScale,
            Quaternion localRot,
            Color color)
        {
            GameObject go = GameObject.CreatePrimitive(type);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPos;
            go.transform.localRotation = localRot;
            go.transform.localScale = localScale;

            Collider col = go.GetComponent<Collider>();
            if (col != null) SafeDestroy(col);

            Renderer rend = go.GetComponent<Renderer>();
            Material mat = new Material(baseTemplateMaterial);
            ApplyMaterialColor(mat, color);
            rend.sharedMaterial = mat;
            createdMaterials.Add(mat);
            return rend;
        }

        private static void ApplyMaterialColor(Material mat, Color color)
        {
            mat.color = color;
            if (mat.HasProperty("_BaseColor"))
            {
                mat.SetColor("_BaseColor", color);
            }
        }

        private static void RegisterPartRenderer(Renderer r, List<Renderer> list, List<Color> baseColors)
        {
            list.Add(r);
            baseColors.Add(r.sharedMaterial.color);
        }

        public void SetHighlightedPart(string verifiedPartId, bool isWarningTone)
        {
            string candidate = verifiedPartId ?? string.Empty;
            if (candidate != "demo-label" && candidate != "demo-critical-part")
            {
                candidate = string.Empty;
            }
            activePartId = candidate;

            // Reset all parts first (guarantees tracking loss / unknown hides stale highlights)
            for (int i = 0; i < labelRenderers.Count; i++)
            {
                ApplyMaterialColor(labelRenderers[i].sharedMaterial, labelBaseColors[i]);
            }
            for (int i = 0; i < criticalRenderers.Count; i++)
            {
                ApplyMaterialColor(criticalRenderers[i].sharedMaterial, criticalBaseColors[i]);
            }

            if (string.IsNullOrEmpty(activePartId))
            {
                if (calloutLine != null) calloutLine.enabled = false;
                if (spatialMarkerGroup != null) spatialMarkerGroup.SetActive(false);
                return;
            }

            activeHighlightColor = isWarningTone
                ? new Color(0.96f, 0.62f, 0.08f, 1f)
                : new Color(0.16f, 0.84f, 0.60f, 1f);

            List<Renderer> targetList = activePartId == "demo-label" ? labelRenderers : criticalRenderers;
            List<Color> targetOriginals = activePartId == "demo-label" ? labelBaseColors : criticalBaseColors;

            for (int i = 0; i < targetList.Count; i++)
            {
                Color blended = Color.Lerp(targetOriginals[i], activeHighlightColor, 0.68f);
                ApplyMaterialColor(targetList[i].sharedMaterial, blended);
            }

            Transform anchor = GetActiveAnchor();
            if (anchor != null)
            {
                if (calloutLine != null)
                {
                    calloutLine.enabled = true;
                    calloutLine.startColor = activeHighlightColor;
                    calloutLine.endColor = activeHighlightColor;
                    calloutLine.SetPosition(0, anchor.position);
                    calloutLine.SetPosition(1, anchor.position + new Vector3(0f, 0.38f, 0f));
                }

                if (spatialMarkerGroup != null)
                {
                    spatialMarkerGroup.transform.position = anchor.position;
                    for (int i = 0; i < markerRenderers.Count; i++)
                    {
                        if (markerRenderers[i] != null)
                        {
                            ApplyMaterialColor(markerRenderers[i].sharedMaterial, activeHighlightColor);
                        }
                    }
                    spatialMarkerGroup.SetActive(true);
                }
            }
        }

        private Transform GetActiveAnchor()
        {
            if (activePartId == "demo-label") return labelAnchor;
            if (activePartId == "demo-critical-part") return criticalAnchor;
            return null;
        }

        public bool TryGetCalloutWorldTop(out Vector3 worldTop)
        {
            worldTop = Vector3.zero;
            Transform anchor = GetActiveAnchor();
            if (anchor == null || string.IsNullOrEmpty(activePartId))
            {
                return false;
            }
            worldTop = anchor.position + new Vector3(0f, 0.42f, 0f);
            return true;
        }

        public void TickAnimation(float deltaTime)
        {
            if (SpinShaftPreview && rotorShaftGroup != null)
            {
                rotorShaftGroup.Rotate(Vector3.right, 55f * deltaTime, Space.Self);
            }

            if (spatialMarkerGroup != null && spatialMarkerGroup.activeSelf && spatialArrowBobGroup != null)
            {
                markerAnimPhase += deltaTime * 3.4f;
                float bob = Mathf.Sin(markerAnimPhase) * 0.025f;
                spatialArrowBobGroup.localPosition = new Vector3(0f, 0.15f + bob, 0f);
            }
        }

        public void ApplyOrbitDelta(Vector2 pointerDelta, Camera cam)
        {
            if (cam == null) return;
            orbitYaw += pointerDelta.x * 0.38f;
            orbitPitch = Mathf.Clamp(orbitPitch + pointerDelta.y * 0.30f, 5f, 68f);
            UpdateCameraTransform(cam);
        }

        public void ApplyZoomDelta(float scrollDeltaY, Camera cam)
        {
            if (cam == null) return;
            orbitDistance = Mathf.Clamp(orbitDistance + scrollDeltaY * 0.14f, 2.35f, 5.4f);
            UpdateCameraTransform(cam);
        }

        public void ResetOrbit(Camera cam)
        {
            orbitYaw = -34f;
            orbitPitch = 21f;
            orbitDistance = 3.42f;
            UpdateCameraTransform(cam);
        }

        public void UpdateCameraTransform(Camera cam)
        {
            if (cam == null) return;
            Quaternion rot = Quaternion.Euler(orbitPitch, orbitYaw, 0f);
            Vector3 stageFrameShift = rot * new Vector3(0.10f, -0.01f, 0f);
            Vector3 lookPoint = orbitTarget + stageFrameShift;
            Vector3 offset = rot * new Vector3(0f, 0f, -orbitDistance);
            cam.transform.position = lookPoint + offset;
            cam.transform.LookAt(lookPoint);
        }

        public void Dispose()
        {
            activePartId = string.Empty;
            labelRenderers.Clear();
            labelBaseColors.Clear();
            criticalRenderers.Clear();
            criticalBaseColors.Clear();
            markerRenderers.Clear();

            foreach (Material mat in createdMaterials)
            {
                SafeDestroy(mat);
            }
            createdMaterials.Clear();
            SafeDestroy(baseTemplateMaterial);
            baseTemplateMaterial = null;
            SafeDestroy(rimLightObj);
            rimLightObj = null;
            SafeDestroy(rigRoot);
            rigRoot = null;
            spatialMarkerGroup = null;
            spatialArrowBobGroup = null;
            calloutLine = null;
            labelAnchor = null;
            criticalAnchor = null;
            rotorShaftGroup = null;
        }

        private static void SafeDestroy(Object obj)
        {
            if (obj == null) return;
            if (Application.isPlaying)
            {
                Object.Destroy(obj);
            }
            else
            {
                Object.DestroyImmediate(obj);
            }
        }
    }
}
