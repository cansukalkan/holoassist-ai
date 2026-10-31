#if UNITY_EDITOR
using System;
using System.Reflection;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class HoloAssistEditorBootstrap
{
    private static GUIStyle bannerBoxStyle;
    private static GUIStyle titleStyle;
    private static GUIStyle subtitleStyle;
    private static GUIStyle playBtnStyle;
    private static GUIStyle secondaryBtnStyle;

    static HoloAssistEditorBootstrap()
    {
        SceneView.duringSceneGui -= OnSceneGUI;
        SceneView.duringSceneGui += OnSceneGUI;

        EditorApplication.playModeStateChanged -= OnPlayModeStateChanged;
        EditorApplication.playModeStateChanged += OnPlayModeStateChanged;

        EditorApplication.delayCall += InitializeEditorWorkspace;
    }

    private static void InitializeEditorWorkspace()
    {
        UpgradeLegacyPortInMemory();
        NormalizeAllGameViews();
        SceneView.RepaintAll();
    }

    private static void OnPlayModeStateChanged(PlayModeStateChange state)
    {
        if (state == PlayModeStateChange.EnteredPlayMode)
        {
            EditorApplication.delayCall += () =>
            {
                NormalizeAllGameViews();
                FocusGameViewWindow();
            };
        }
        else if (state == PlayModeStateChange.EnteredEditMode)
        {
            EditorApplication.delayCall += () =>
            {
                NormalizeAllGameViews();
                SceneView.RepaintAll();
            };
        }
    }

    private static void UpgradeLegacyPortInMemory()
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode) return;

        HoloAssistApiClient client = UnityEngine.Object.FindFirstObjectByType<HoloAssistApiClient>();
        if (client == null) return;

        FieldInfo urlField = typeof(HoloAssistApiClient).GetField(
            "baseUrl",
            BindingFlags.Instance | BindingFlags.NonPublic);
        if (urlField != null)
        {
            string val = urlField.GetValue(client) as string;
            if (string.IsNullOrWhiteSpace(val) || val.Contains(":8000"))
            {
                urlField.SetValue(client, "http://127.0.0.1:8001");
            }
        }
    }

    [MenuItem("HoloAssist/▶ 3D Denetim İstasyonunu Başlat (Play Mode)", priority = 10)]
    public static void StartWorkstationPlayMode()
    {
        NormalizeAllGameViews();
        FocusGameViewWindow();
        if (!EditorApplication.isPlaying)
        {
            EditorApplication.isPlaying = true;
        }
    }

    [MenuItem("HoloAssist/Game Penceresi Ölçeğini Sıfırla (Tam Ekran 1x)", priority = 25)]
    public static void ResetGameViewScaleMenu()
    {
        NormalizeAllGameViews();
        FocusGameViewWindow();
    }

    public static void FocusGameViewWindow()
    {
        Type gameViewType = typeof(Editor).Assembly.GetType("UnityEditor.GameView");
        if (gameViewType == null) return;

        UnityEngine.Object[] views = Resources.FindObjectsOfTypeAll(gameViewType);
        if (views != null && views.Length > 0 && views[0] is EditorWindow existing)
        {
            existing.Focus();
            existing.Repaint();
        }
        else
        {
            EditorWindow opened = EditorWindow.GetWindow(gameViewType);
            if (opened != null)
            {
                opened.Focus();
                NormalizeAllGameViews();
            }
        }
    }

    public static void NormalizeAllGameViews()
    {
        Type gameViewType = typeof(Editor).Assembly.GetType("UnityEditor.GameView");
        if (gameViewType == null) return;

        BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        PropertyInfo lowResProp = gameViewType.GetProperty("lowResolutionForAspectRatios", flags);
        FieldInfo lowResArrayField = gameViewType.GetField("m_LowResolutionForAspectRatios", flags);
        PropertyInfo minScaleProp = gameViewType.GetProperty("minScale", flags);
        MethodInfo snapZoomMethod = gameViewType.GetMethod("SnapZoom", flags, null, new[] { typeof(float) }, null);
        MethodInfo updateZoomMethod = gameViewType.GetMethod("UpdateZoomAreaAndParent", flags);
        FieldInfo defaultScaleField = gameViewType.GetField("m_defaultScale", flags);
        FieldInfo zoomAreaField = gameViewType.GetField("m_ZoomArea", flags);

        UnityEngine.Object[] views = Resources.FindObjectsOfTypeAll(gameViewType);
        if (views == null) return;

        foreach (UnityEngine.Object obj in views)
        {
            EditorWindow gv = obj as EditorWindow;
            if (gv == null) continue;

            try
            {
                if (lowResArrayField != null && lowResArrayField.GetValue(gv) is bool[] lowResArr)
                {
                    for (int i = 0; i < lowResArr.Length; i++)
                    {
                        lowResArr[i] = false;
                    }
                }

                if (lowResProp != null && lowResProp.CanWrite)
                {
                    lowResProp.SetValue(gv, false, null);
                }

                float targetScale = 1.0f;
                if (minScaleProp != null && minScaleProp.CanRead)
                {
                    object minVal = minScaleProp.GetValue(gv, null);
                    if (minVal is float f && f > 0.05f && f <= 2.0f)
                    {
                        targetScale = f;
                    }
                }

                if (defaultScaleField != null)
                {
                    defaultScaleField.SetValue(gv, targetScale);
                }

                if (snapZoomMethod != null)
                {
                    snapZoomMethod.Invoke(gv, new object[] { targetScale });
                }

                if (zoomAreaField != null)
                {
                    object zoomArea = zoomAreaField.GetValue(gv);
                    if (zoomArea != null)
                    {
                        Type zaType = zoomArea.GetType();
                        FieldInfo scaleField = zaType.GetField("m_Scale", flags);
                        FieldInfo transField = zaType.GetField("m_Translation", flags);
                        if (scaleField != null)
                        {
                            scaleField.SetValue(zoomArea, new Vector2(targetScale, targetScale));
                        }
                        if (transField != null)
                        {
                            transField.SetValue(zoomArea, Vector2.zero);
                        }
                    }
                }

                if (updateZoomMethod != null)
                {
                    updateZoomMethod.Invoke(gv, null);
                }

                gv.Repaint();
            }
            catch
            {
                // Ignore internal layout differences across Editor patch builds
            }
        }
    }

    private static void EnsureStyles()
    {
        if (bannerBoxStyle != null) return;

        Texture2D bgTex = new Texture2D(1, 1);
        bgTex.hideFlags = HideFlags.HideAndDontSave;
        bgTex.SetPixel(0, 0, new Color(0.03f, 0.09f, 0.13f, 0.94f));
        bgTex.Apply();

        bannerBoxStyle = new GUIStyle(GUI.skin.box)
        {
            padding = new RectOffset(14, 14, 10, 10)
        };
        bannerBoxStyle.normal.background = bgTex;

        titleStyle = new GUIStyle(EditorStyles.boldLabel)
        {
            fontSize = 13,
            wordWrap = true
        };
        titleStyle.normal.textColor = new Color(0.43f, 0.91f, 0.72f);

        subtitleStyle = new GUIStyle(EditorStyles.label)
        {
            fontSize = 11,
            wordWrap = true
        };
        subtitleStyle.normal.textColor = new Color(0.84f, 0.92f, 0.97f);

        Texture2D btnTex = new Texture2D(1, 1);
        btnTex.hideFlags = HideFlags.HideAndDontSave;
        btnTex.SetPixel(0, 0, new Color(0.05f, 0.58f, 0.53f, 1f));
        btnTex.Apply();

        playBtnStyle = new GUIStyle(GUI.skin.button)
        {
            fontSize = 12,
            fontStyle = FontStyle.Bold,
            fixedHeight = 30
        };
        playBtnStyle.normal.background = btnTex;
        playBtnStyle.normal.textColor = Color.white;
        playBtnStyle.hover.background = btnTex;
        playBtnStyle.hover.textColor = new Color(0.9f, 1f, 0.96f);

        secondaryBtnStyle = new GUIStyle(GUI.skin.button)
        {
            fontSize = 11,
            fontStyle = FontStyle.Bold,
            fixedHeight = 30
        };
    }

    private static void OnSceneGUI(SceneView sceneView)
    {
        if (EditorApplication.isPlaying) return;

        EnsureStyles();
        Handles.BeginGUI();

        float width = Mathf.Clamp(sceneView.position.width - 28f, 320f, 760f);
        Rect panelRect = new Rect(14f, 12f, width, 92f);

        GUILayout.BeginArea(panelRect, bannerBoxStyle);
        GUILayout.Label("HoloAssist AI · 3D Teknik Denetim İstasyonu (Düzenleme Modu Önizlemesi)", titleStyle);
        GUILayout.Label("Tüm 5 modül sekmesi (01 Tanıma, 02 Güvenlik, 03 Sensör, 04 Kanıt, 05 Bench) ve tıklanabilir arayüz Play Mode içinde çalışır:", subtitleStyle);
        GUILayout.Space(4f);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("▶ 3D Denetim İstasyonunu Başlat (Play Mode + Game Sekmesi)", playBtnStyle, GUILayout.ExpandWidth(true)))
        {
            StartWorkstationPlayMode();
        }
        if (GUILayout.Button("Game Ölçeğini Sıfırla (1x)", secondaryBtnStyle, GUILayout.Width(175f)))
        {
            ResetGameViewScaleMenu();
        }
        GUILayout.EndHorizontal();
        GUILayout.EndArea();

        Handles.EndGUI();
    }
}
#endif

