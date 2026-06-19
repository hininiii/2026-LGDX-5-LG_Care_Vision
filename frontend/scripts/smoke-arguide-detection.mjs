import { build } from "esbuild";
import { mkdir, readFile, rm } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = process.cwd();
const helperSource = path.join(root, "src", "app", "pages", "arGuideDetection.ts");
const arGuideSource = path.join(root, "src", "app", "pages", "ARGuide.tsx");
const chatSource = path.join(root, "src", "app", "pages", "Chat.tsx");
const selfCareSource = path.join(root, "src", "app", "pages", "SelfCare.tsx");
const outDir = path.join(root, "runtime_logs", "ar_guide_smoke");
const bundledHelper = path.join(outDir, "arGuideDetection.bundle.mjs");

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

await mkdir(outDir, { recursive: true });
await build({
  entryPoints: [helperSource],
  bundle: true,
  format: "esm",
  platform: "node",
  outfile: bundledHelper,
  logLevel: "silent",
});

const helper = await import(pathToFileURL(bundledHelper).href + `?t=${Date.now()}`);
const {
  smoothBox,
  getCaptureSizeFromDimensions,
  getObjectCoverTransform,
} = helper;

const first = { x: 0, y: 0, width: 100, height: 50, confidence: 0.2, class_name: "filter" };
const second = { x: 100, y: 80, width: 200, height: 90, confidence: 0.9, class_name: "filter" };
const smoothed = smoothBox(first, second, 0.35);
assert(Math.abs(smoothed.x - 35) < 0.0001, "smoothBox x should use EMA alpha");
assert(Math.abs(smoothed.y - 28) < 0.0001, "smoothBox y should use EMA alpha");
assert(Math.abs(smoothed.width - 135) < 0.0001, "smoothBox width should use EMA alpha");
assert(Math.abs(smoothed.height - 64) < 0.0001, "smoothBox height should use EMA alpha");
assert(smoothed.confidence === 0.9, "smoothBox should keep latest confidence");

const capture = getCaptureSizeFromDimensions(640, 480);
assert(capture.width === 416, "capture width should stay 416");
assert(capture.height === 312, "capture height should preserve 4:3 source ratio");

const cover = getObjectCoverTransform(390, 600, 416, 312);
assert(cover.offsetX < 0, "object-cover transform should crop horizontal overflow in tall viewport");
assert(cover.offsetY === 0, "object-cover transform should not crop vertical axis in tall viewport");
assert(Math.abs(cover.scaleX - cover.scaleY) < 0.0001, "object-cover scale should be uniform");

const arGuide = await readFile(arGuideSource, "utf8");
const chat = await readFile(chatSource, "utf8");
const selfCare = await readFile(selfCareSource, "utf8");
const staticContracts = [
  ["setInterval", "const interval = window.setInterval"],
  ["700ms frame interval", "}, 700);"],
  ["filter detect endpoint", "/v1/ar/filter-detect"],
  ["image_data_url payload", "image_data_url: imageDataUrl"],
  ["step confidence helper", "getConfidenceThresholdForStep"],
  ["aircon default threshold", "AIRCON_DETECTION_CONFIDENCE_THRESHOLD = 0.35"],
  ["filter default threshold", 'targetClasses.includes("filter")) return DEFAULT_DETECTION_CONFIDENCE_THRESHOLD'],
  ["confidence threshold", "confidence_threshold: detectionConfidenceThreshold"],
  ["step target classes", "target_classes: currentStep.targetClasses"],
  ["step context classes", "require_context_classes: currentStep.contextClasses"],
  ["procedure model profile helper", "getModelProfileForProcedure"],
  ["no cooling uses self AS model", 'procedureType === "no_cooling_self_check" ? "self_as_no_cooling" : "self_care"'],
  ["model profile payload", "model_profile: detectionModelProfile"],
  ["procedure type payload", "procedure_type: procedureType"],
  ["query procedure fallback", "queryParams.get(\"procedure_type\")"],
  ["direct guide options fetch", "/v1/guides/options"],
  ["display step mapping", "guideStepsFromDisplaySteps"],
  ["relative audio URL resolver", "resolveAudioUrl"],
  ["audio URL uses backend origin", "new URL(API_BASE_URL, window.location.origin).origin"],
  ["direct self AS fallback", "guideStepsByProcedure[procedureType]"],
  ["outlet label", 'outlet: "토출구"'],
  ["self AS outlet direct step", 'targetClasses: ["outlet"]'],
  ["mock fallback disabled", "mock_fallback: false"],
  ["jpeg quality", "toDataURL(\"image/jpeg\", DETECTION_JPEG_QUALITY)"],
  ["detection hold", "DETECTION_HOLD_MS = 900"],
  ["canvas overlay ref", "overlayRef"],
  ["smoothing call", "smoothBox(smoothedBoxRef.current, detection)"],
];
for (const [name, needle] of staticContracts) {
  assert(arGuide.includes(needle), `ARGuide contract missing: ${name}`);
}

const stepTargetContracts = [
  ["Chat no_cooling procedure", chat, "no_cooling_self_check"],
  ["Chat step targets", chat, "AR_GUIDE_STEP_TARGETS"],
  ["Chat client AR procedure registry", chat, "CLIENT_AR_GUIDE_PROCEDURES"],
  ["Chat client AR availability guard", chat, "canOpenArGuide"],
  ["Chat direct AR procedure query", chat, "procedure_type=${encodeURIComponent(procedureType)}"],
  ["Chat display steps priority", chat, "guideOptions?.display_steps"],
  ["Chat display step source text", chat, "sourceText: displaySteps[index]?.source_text"],
  ["Chat aircon target", chat, 'targetClasses: ["aircon"]'],
  ["Chat filter context target", chat, 'targetClasses: ["filter"], contextClasses: ["aircon"]'],
  ["Chat outlet context target", chat, 'targetClasses: ["outlet"], contextClasses: ["aircon"]'],
  ["SelfCare step targets", selfCare, "AR_GUIDE_STEP_TARGETS"],
  ["SelfCare filter context target", selfCare, 'targetClasses: ["filter"], contextClasses: ["aircon"]'],
];
for (const [name, source, needle] of stepTargetContracts) {
  assert(source.includes(needle), `Step target contract missing: ${name}`);
}

await rm(bundledHelper, { force: true });
console.log(
  JSON.stringify(
    {
      ok: true,
      checks: {
        smoothing: smoothed,
        capture,
        cover,
        static_contracts: staticContracts.length,
        step_target_contracts: stepTargetContracts.length,
      },
    },
    null,
    2,
  ),
);
