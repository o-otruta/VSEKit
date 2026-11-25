// Run via Unity MCP `eval` while ALREADY in Play Mode.
// Starts a 1-run BalanceBot batch and records the Game View with Unity Recorder once the
// Gameplay scene is live: skips WARMUP seconds of game time, records RECORD seconds as a JPEG
// sequence into OUT\, then stops the recorder, stops the bot and exits Play Mode (bot restores
// the player's save). Then: python -c "from vsekit import media; media.assemble_sequence(OUT, OUT + '.mp4', 60)"
using System;
using UnityEditor;
using UnityEditor.Recorder;
using UnityEditor.Recorder.Input;
using UnityEditor.Recorder.Encoder;
using UnityEngine;
using UnityEngine.SceneManagement;
using ProjectB.Core.BalanceBot;

string KIT = Environment.GetEnvironmentVariable("VSEKIT_ROOT", EnvironmentVariableTarget.User)
             ?? System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "VSEKit");
string OUT = System.IO.Path.Combine(KIT, "media", "gameplay", "bot_knight_full");
const int W = 1080, H = 1920, FPS = 60;
const float WARMUP = 25f, RECORD = 60f;
const string HERO = "knight";
const string PROFILE = "Assets/_ScriptableObjects/BalanceBot/Profile_Full.asset";

if (!EditorApplication.isPlaying) return "Enter Play Mode first.";

var src = AssetDatabase.LoadAssetAtPath<BalanceBotConfig>("Assets/_ScriptableObjects/BalanceBot/DefaultBalanceBotConfig.asset");
var cfg = src != null ? UnityEngine.Object.Instantiate(src) : BalanceBotConfig.CreateRuntimeDefault();
cfg.hideFlags = HideFlags.DontSave;
cfg.heroIds = new System.Collections.Generic.List<string> { HERO };
cfg.strategies = new System.Collections.Generic.List<BalanceBotStrategyKind> { BalanceBotStrategyKind.GreedyDamage };
cfg.runsPerCombination = 1;
cfg.useFixedStepSimulation = true;
cfg.simulationFps = FPS;
cfg.maxRunMinutes = 60f;   // bot's guard is wall-clock; an unfocused editor runs ~1 fps, so keep it generous
var prof = AssetDatabase.LoadAssetAtPath<BalanceBotMetaProfile>(PROFILE);
cfg.metaProfiles = new System.Collections.Generic.List<BalanceBotMetaProfile>();
if (prof != null) cfg.metaProfiles.Add(prof);
BalanceBotRunner.StartBatch(cfg, null);

RecorderController ctrl = null;
float gameplayStart = -1f, recStart = -1f;
EditorApplication.CallbackFunction tick = null;
tick = () =>
{
    try
    {
        if (!EditorApplication.isPlaying) { EditorApplication.update -= tick; return; }
        // GameManager auto-pauses on focus loss (Sprint 15.1); the bot doesn't resume -> do it here.
        var gm = UnityEngine.Object.FindAnyObjectByType<ProjectB.Core.GameManager>();
        if (gm != null && gm.IsPaused && BalanceBotRunner.IsBatchRunning) gm.ResumeGame();
        bool inGameplay = SceneManager.GetActiveScene().name == "Gameplay";
        if (gameplayStart < 0f && inGameplay) gameplayStart = Time.time;
        if (ctrl == null && gameplayStart >= 0f && Time.time - gameplayStart >= WARMUP)
        {
            // JPEG sequence, NOT the MP4 movie recorder: Unity's Media Foundation MP4 encoder
            // (WindowsVideoMedia.WriteSample) stalls ~1 s per frame after the first ~100-200 frames
            // when fed faster than real time. JPEG sustains ~28 fps at 1080x1920; assemble with
            // vsekit.media.assemble_sequence (ffmpeg NVENC) afterwards.
            var s = ScriptableObject.CreateInstance<RecorderControllerSettings>();
            var m = ScriptableObject.CreateInstance<ImageRecorderSettings>();
            m.name = "BotGameplay";
            m.Enabled = true;
            m.OutputFormat = ImageRecorderSettings.ImageRecorderOutputFormat.JPEG;
            m.JpegQuality = 95;
            m.imageInputSettings = new GameViewInputSettings { OutputWidth = W, OutputHeight = H };
            System.IO.Directory.CreateDirectory(OUT);
            m.OutputFile = OUT + "\\f_" + DefaultWildcard.Frame;   // Path.Combine rejects '<Frame>'
            s.AddRecorderSettings(m);
            s.SetRecordModeToManual();
            s.FrameRate = FPS;
            s.FrameRatePlayback = FrameRatePlayback.Constant;
            s.CapFrameRate = false;
            ctrl = new RecorderController(s);
            ctrl.PrepareRecording();
            ctrl.StartRecording();
            recStart = Time.time;
            Debug.Log("[VSEKit] Recording started");
        }
        bool runEnded = gameplayStart >= 0f && !BalanceBotRunner.IsBatchRunning;
        if (ctrl != null && (Time.time - recStart >= RECORD || runEnded))
        {
            ctrl.StopRecording();
            Debug.Log($"[VSEKit] Recording stopped after {Time.time - recStart:F1}s game time -> {OUT}\\f_*.jpg");
            EditorApplication.update -= tick;
            BalanceBotRunner.StopActiveBatch();
            EditorApplication.isPlaying = false;
        }
    }
    catch (Exception e)
    {
        Debug.LogException(e);
        EditorApplication.update -= tick;
    }
};
EditorApplication.update += tick;
return $"Bot started ({HERO}, profile={(prof != null ? prof.name : "fallback")}); recorder armed: warmup {WARMUP}s, record {RECORD}s.";
