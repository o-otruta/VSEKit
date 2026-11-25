// Diagnostic: run the same BalanceBot job as record_bot_gameplay.cs but WITHOUT Unity Recorder.
// Run via Unity MCP eval while in Play Mode. Stop with: BalanceBotRunner.StopActiveBatch(); isPlaying = false.
using UnityEditor;
using UnityEngine;
using ProjectB.Core.BalanceBot;

if (!EditorApplication.isPlaying) return "Enter Play Mode first.";
var src = AssetDatabase.LoadAssetAtPath<BalanceBotConfig>("Assets/_ScriptableObjects/BalanceBot/DefaultBalanceBotConfig.asset");
var cfg = src != null ? Object.Instantiate(src) : BalanceBotConfig.CreateRuntimeDefault();
cfg.hideFlags = HideFlags.DontSave;
cfg.heroIds = new System.Collections.Generic.List<string> { "knight" };
cfg.strategies = new System.Collections.Generic.List<BalanceBotStrategyKind> { BalanceBotStrategyKind.GreedyDamage };
cfg.runsPerCombination = 1;
cfg.useFixedStepSimulation = true;
cfg.simulationFps = 60;
cfg.maxRunMinutes = 60f;
var prof = AssetDatabase.LoadAssetAtPath<BalanceBotMetaProfile>("Assets/_ScriptableObjects/BalanceBot/Profile_Full.asset");
cfg.metaProfiles = new System.Collections.Generic.List<BalanceBotMetaProfile>();
if (prof != null) cfg.metaProfiles.Add(prof);
BalanceBotRunner.StartBatch(cfg, null);
return "bot started (no recorder)";
