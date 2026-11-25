// Diagnostic: measure Unity Recorder throughput for several output configs while the bot plays.
// Run via Unity MCP eval in Play Mode AFTER diag_bot_only.cs has the Gameplay scene running.
// Result accumulates in SessionState "vsekit_matrix".
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Recorder;
using UnityEditor.Recorder.Encoder;
using UnityEditor.Recorder.Input;
using UnityEngine;

string KIT = System.Environment.GetEnvironmentVariable("VSEKIT_ROOT", System.EnvironmentVariableTarget.User)
             ?? System.IO.Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.MyDocuments), "VSEKit");
string DIR = System.IO.Path.Combine(KIT, "media", "gameplay", "diag");
System.IO.Directory.CreateDirectory(DIR);
var tests = new List<(string name, int w, int h, string kind, int frames)>
{
    ("D_jpg_1080x1920", 1080, 1920, "jpg", 900),
    ("E_png_1080x1920", 1080, 1920, "png", 600),
};
SessionState.SetString("vsekit_matrix", "");
int idx = -1, f0 = 0; float r0 = 0; RecorderController ctrl = null;

RecorderController Make((string name, int w, int h, string kind, int frames) t)
{
    var s = ScriptableObject.CreateInstance<RecorderControllerSettings>();
    RecorderSettings rs;
    var input = new GameViewInputSettings { OutputWidth = t.w, OutputHeight = t.h };
    if (t.kind == "mp4")
    {
        var m = ScriptableObject.CreateInstance<MovieRecorderSettings>();
        m.EncoderSettings = new CoreEncoderSettings { Codec = CoreEncoderSettings.OutputCodec.MP4, EncodingQuality = CoreEncoderSettings.VideoEncodingQuality.High };
        m.ImageInputSettings = input;
        m.AudioInputSettings.PreserveAudio = false;
        m.OutputFile = System.IO.Path.Combine(DIR, t.name);
        rs = m;
    }
    else
    {
        var im = ScriptableObject.CreateInstance<ImageRecorderSettings>();
        im.OutputFormat = t.kind == "jpg" ? ImageRecorderSettings.ImageRecorderOutputFormat.JPEG : ImageRecorderSettings.ImageRecorderOutputFormat.PNG;
        im.imageInputSettings = input;
        im.OutputFile = DIR + "\\" + t.name + "\\f_" + DefaultWildcard.Frame;   // Path.Combine rejects '<Frame>'
        rs = im;
    }
    rs.name = t.name; rs.Enabled = true;
    s.AddRecorderSettings(rs); s.SetRecordModeToManual();
    s.FrameRate = 60; s.FrameRatePlayback = FrameRatePlayback.Constant; s.CapFrameRate = false;
    var c = new RecorderController(s); c.PrepareRecording(); c.StartRecording();
    return c;
}

EditorApplication.CallbackFunction tick = null;
tick = () =>
{
    if (!EditorApplication.isPlaying) { EditorApplication.update -= tick; return; }
    var gm = Object.FindAnyObjectByType<ProjectB.Core.GameManager>();
    if (gm != null && gm.IsPaused) gm.ResumeGame();
    if (ctrl != null && Time.frameCount - f0 >= tests[idx].frames)
    {
        ctrl.StopRecording();
        float dt = Time.realtimeSinceStartup - r0;
        int n = Time.frameCount - f0;
        SessionState.SetString("vsekit_matrix", SessionState.GetString("vsekit_matrix", "") + $"{tests[idx].name}: {n} frames / {dt:F1}s = {n / dt:F1} fps\n");
        ctrl = null;
    }
    if (ctrl == null)
    {
        idx++;
        if (idx >= tests.Count) { SessionState.SetString("vsekit_matrix", SessionState.GetString("vsekit_matrix", "") + "DONE\n"); EditorApplication.update -= tick; return; }
        ctrl = Make(tests[idx]);
        f0 = Time.frameCount; r0 = Time.realtimeSinceStartup;
    }
};
EditorApplication.update += tick;
return "matrix started";
