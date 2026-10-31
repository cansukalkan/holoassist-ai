using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace HoloAssist.Client
{
    public class HoloAssistChartRenderer
    {
        private Texture2D chartTexture;
        private const int Width = 480;
        private const int Height = 176;

        public Texture2D CurrentTexture => chartTexture;

        public void RenderSeries(SensorDemoPayload payload)
        {
            if (payload == null || payload.series == null || payload.series.observations == null || payload.series.observations.Count == 0)
            {
                return;
            }

            if (chartTexture == null)
            {
                chartTexture = new Texture2D(Width, Height, TextureFormat.RGBA32, false)
                {
                    wrapMode = TextureWrapMode.Clamp,
                    filterMode = FilterMode.Bilinear
                };
            }

            Color bg = new Color(0.045f, 0.105f, 0.145f, 1f);
            Color gridCol = new Color(0.14f, 0.25f, 0.32f, 1f);
            Color borderCol = new Color(0.20f, 0.36f, 0.45f, 1f);
            Color lineCol = new Color(0.08f, 0.72f, 0.58f, 1f);
            Color pointCol = new Color(0.25f, 0.88f, 0.68f, 1f);
            Color outlierCol = new Color(0.96f, 0.62f, 0.10f, 1f);

            Color[] pixels = new Color[Width * Height];
            for (int i = 0; i < pixels.Length; i++) pixels[i] = bg;

            // Border
            for (int x = 0; x < Width; x++)
            {
                pixels[x] = borderCol;
                pixels[(Height - 1) * Width + x] = borderCol;
            }
            for (int y = 0; y < Height; y++)
            {
                pixels[y * Width] = borderCol;
                pixels[y * Width + (Width - 1)] = borderCol;
            }

            int padLeft = 22;
            int padRight = 22;
            int padBottom = 20;
            int padTop = 20;
            int plotW = Width - padLeft - padRight;
            int plotH = Height - padBottom - padTop;

            // Horizontal dashed grid lines
            for (int g = 0; g < 4; g++)
            {
                int gy = padBottom + (plotH * g) / 3;
                for (int x = padLeft; x < Width - padRight; x++)
                {
                    if ((x / 4) % 2 == 0)
                    {
                        pixels[gy * Width + x] = gridCol;
                    }
                }
            }

            List<SensorObservation> samples = payload.series.observations;
            int count = samples.Count;
            double[] elapsed = new double[count];
            double minV = double.MaxValue;
            double maxV = double.MinValue;

            DateTimeOffset t0 = ParseUtc(samples[0].timestamp_utc);
            for (int i = 0; i < count; i++)
            {
                DateTimeOffset ti = ParseUtc(samples[i].timestamp_utc);
                elapsed[i] = Math.Max(0.0, (ti - t0).TotalSeconds);
                if (samples[i].value < minV) minV = samples[i].value;
                if (samples[i].value > maxV) maxV = samples[i].value;
            }

            double margin = (maxV - minV) * 0.16;
            if (margin <= 1e-6) margin = Math.Max(Math.Abs(maxV) * 0.05, 0.01);
            double low = minV - margin;
            double high = maxV + margin;
            double totalTime = Math.Max(elapsed[count - 1], 1.0);

            Vector2[] pts = new Vector2[count];
            for (int i = 0; i < count; i++)
            {
                float nx = count == 1 ? 0.5f : (float)(elapsed[i] / totalTime);
                float ny = (float)((samples[i].value - low) / (high - low));
                pts[i] = new Vector2(padLeft + nx * plotW, padBottom + ny * plotH);
            }

            // Thick line segments
            for (int i = 0; i < count - 1; i++)
            {
                DrawThickLine(pixels, pts[i], pts[i + 1], 2.2f, lineCol);
            }

            // Sample circles & MAD outlier highlights
            HashSet<int> outliers = new HashSet<int>();
            if (payload.report != null && payload.report.outliers != null && payload.report.outliers.sample_indices != null)
            {
                foreach (int idx in payload.report.outliers.sample_indices) outliers.Add(idx);
            }

            for (int i = 0; i < count; i++)
            {
                bool isOutlier = outliers.Contains(i);
                if (isOutlier)
                {
                    DrawDisc(pixels, pts[i], 7.0f, outlierCol);
                    DrawDisc(pixels, pts[i], 3.5f, Color.white);
                }
                else
                {
                    DrawDisc(pixels, pts[i], 4.8f, pointCol);
                }
            }

            chartTexture.SetPixels(pixels);
            chartTexture.Apply();
        }

        private static DateTimeOffset ParseUtc(string iso)
        {
            if (DateTimeOffset.TryParse(iso, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out DateTimeOffset dt))
            {
                return dt;
            }
            return DateTimeOffset.UtcNow;
        }

        private static void DrawThickLine(Color[] buf, Vector2 a, Vector2 b, float radius, Color col)
        {
            int steps = Mathf.CeilToInt(Vector2.Distance(a, b) * 2f) + 1;
            for (int s = 0; s <= steps; s++)
            {
                Vector2 p = Vector2.Lerp(a, b, s / (float)steps);
                DrawDisc(buf, p, radius, col);
            }
        }

        private static void DrawDisc(Color[] buf, Vector2 center, float radius, Color col)
        {
            int minX = Mathf.Max(1, Mathf.FloorToInt(center.x - radius - 1));
            int maxX = Mathf.Min(Width - 2, Mathf.CeilToInt(center.x + radius + 1));
            int minY = Mathf.Max(1, Mathf.FloorToInt(center.y - radius - 1));
            int maxY = Mathf.Min(Height - 2, Mathf.CeilToInt(center.y + radius + 1));

            for (int y = minY; y <= maxY; y++)
            {
                for (int x = minX; x <= maxX; x++)
                {
                    float dist = Vector2.Distance(new Vector2(x, y), center);
                    if (dist <= radius)
                    {
                        float alpha = Mathf.Clamp01(radius - dist + 0.5f);
                        int idx = y * Width + x;
                        buf[idx] = Color.Lerp(buf[idx], col, alpha);
                    }
                }
            }
        }

        public void Dispose()
        {
            if (chartTexture != null)
            {
                if (Application.isPlaying)
                {
                    UnityEngine.Object.Destroy(chartTexture);
                }
                else
                {
                    UnityEngine.Object.DestroyImmediate(chartTexture);
                }
                chartTexture = null;
            }
        }
    }
}
