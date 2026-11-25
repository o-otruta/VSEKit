"""Shot / scene-cut detection with PySceneDetect (run with VENV_PY)."""
import json
import os


def detect(path, threshold=27.0, min_scene_len_s=0.4, cache=True):
    """Returns list of {'start','end'} in seconds for every shot in the video."""
    out = path + f".scenes_{threshold:g}.json"
    if cache and os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(path):
        return json.load(open(out))
    from scenedetect import open_video, SceneManager, ContentDetector
    v = open_video(path)
    fps = v.frame_rate
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold, min_scene_len=max(1, int(min_scene_len_s * fps))))
    sm.detect_scenes(v, show_progress=False)
    res = [{"start": a.get_seconds(), "end": b.get_seconds()} for a, b in sm.get_scene_list()]
    if not res:
        res = [{"start": 0.0, "end": v.duration.get_seconds()}]
    json.dump(res, open(out, "w"))
    return res


def stats(scenes):
    lens = [s["end"] - s["start"] for s in scenes]
    total = scenes[-1]["end"] - scenes[0]["start"]
    return {"shots": len(scenes), "avg_shot_s": sum(lens) / len(lens),
            "median_shot_s": sorted(lens)[len(lens) // 2], "cuts_per_min": (len(scenes) - 1) / (total / 60)}
