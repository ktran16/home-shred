"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { trackedAngle, type Landmark, type TrackConfig } from "@/lib/pose";
import { initialRepState, updateRep, type RepState } from "@/lib/rep-counter";

// MediaPipe Tasks Vision is loaded from a CDN at runtime (on-device, in the browser)
// so no heavy model is bundled and the CPU-only host never touches video (SPEC §17.5
// B2a). The lite pose model is ~3 MB and runs on a phone.
const VISION_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

type PoseLandmarker = {
  detectForVideo: (video: HTMLVideoElement, timestamp: number) => { landmarks: Landmark[][] };
  close: () => void;
};

type VisionModule = {
  FilesetResolver: { forVisionTasks: (wasmBase: string) => Promise<unknown> };
  PoseLandmarker: {
    createFromOptions: (fileset: unknown, options: unknown) => Promise<PoseLandmarker>;
  };
};

// Keep the bundler out of a remote ESM URL entirely; this is a pure runtime import.
const runtimeImport = new Function("u", "return import(u)") as (u: string) => Promise<unknown>;

async function loadPoseLandmarker(): Promise<PoseLandmarker> {
  const vision = (await runtimeImport(`${VISION_CDN}/vision_bundle.mjs`)) as VisionModule;
  const fileset = await vision.FilesetResolver.forVisionTasks(`${VISION_CDN}/wasm`);
  return vision.PoseLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
    runningMode: "VIDEO",
    numPoses: 1,
  });
}

type Status = "loading" | "running" | "error" | "unsupported";

export function PoseRepCounter({
  config,
  onRep,
  onClose,
}: {
  config: TrackConfig;
  onRep: (totalReps: number) => void;
  onClose: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const repStateRef = useRef<RepState>(initialRepState());
  const [supported] = useState(
    () => typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia,
  );
  const [status, setStatus] = useState<Status>(supported ? "loading" : "unsupported");
  const [reps, setReps] = useState(0);
  const [angle, setAngle] = useState<number | null>(null);
  const [lastFullRange, setLastFullRange] = useState<boolean | null>(null);

  useEffect(() => {
    if (!supported) return;
    let stream: MediaStream | null = null;
    let landmarker: PoseLandmarker | null = null;
    let raf = 0;
    let cancelled = false;

    const start = async () => {
      try {
        landmarker = await loadPoseLandmarker();
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user" },
          audio: false,
        });
        if (cancelled) return;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = stream;
        await video.play();
        setStatus("running");

        const loop = () => {
          if (cancelled || !landmarker || !video) return;
          const result = landmarker.detectForVideo(video, performance.now());
          const landmarks = result.landmarks?.[0] as Landmark[] | undefined;
          const measured = landmarks ? trackedAngle(landmarks, config) : null;
          setAngle(measured);
          const update = updateRep(repStateRef.current, measured, config);
          repStateRef.current = update.state;
          if (update.completedRep) {
            setReps(update.state.reps);
            setLastFullRange(update.fullRange);
            onRep(update.state.reps);
          }
          raf = requestAnimationFrame(loop);
        };
        raf = requestAnimationFrame(loop);
      } catch {
        if (!cancelled) setStatus("error");
      }
    };

    start();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((track) => track.stop());
      landmarker?.close();
    };
  }, [config, onRep, supported]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Camera rep counter · {config.label}
        </div>
        <Button
          type="button"
          variant="secondary"
          className="h-8 min-h-0 px-3 text-xs"
          onClick={onClose}
        >
          Close
        </Button>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-[160px_1fr] sm:items-center">
        <video
          ref={videoRef}
          playsInline
          muted
          className="aspect-[3/4] w-full rounded-lg bg-zinc-100 object-cover dark:bg-zinc-950"
        />
        <div className="flex flex-col gap-1">
          {status === "loading" && <p className="text-sm text-zinc-500">Loading pose model…</p>}
          {status === "unsupported" && (
            <p className="text-sm text-amber-600">Camera not available on this device.</p>
          )}
          {status === "error" && (
            <p className="text-sm text-amber-600">
              Couldn’t start the camera or model. Allow camera access, or count manually.
            </p>
          )}
          {status === "running" && (
            <>
              <div className="text-4xl font-bold tabular-nums">{reps}</div>
              <div className="text-xs text-zinc-500">
                {angle != null ? `${config.label} angle ${Math.round(angle)}°` : "Get in frame…"}
              </div>
              {lastFullRange != null && (
                <div
                  className={`text-xs font-medium ${
                    lastFullRange ? "text-emerald-600" : "text-amber-600"
                  }`}
                >
                  {lastFullRange ? "Full depth ✓" : "Partial range — go deeper"}
                </div>
              )}
              <p className="mt-1 text-[11px] text-zinc-400">
                Counted reps fill the set automatically. Adjust if needed.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
