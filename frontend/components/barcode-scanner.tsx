"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { Button, Card, Input } from "@/components/ui";
import { api, type FoodLogIn } from "@/lib/api";
import { foodTitle, isValidBarcode, macrosForGrams } from "@/lib/food";

// Native on-device barcode scanning (SPEC §17.5 B2b). No ML model, no extra deps;
// the macro lookup hits Open Food Facts via our backend (opt-in / external).
type DetectedBarcode = { rawValue: string };
type BarcodeDetectorLike = { detect: (source: HTMLVideoElement) => Promise<DetectedBarcode[]> };
type BarcodeDetectorCtor = new (options?: { formats?: string[] }) => BarcodeDetectorLike;

function getBarcodeDetector(): BarcodeDetectorCtor | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector ?? null;
}

export function BarcodeScanner({
  onLog,
  logging = false,
}: {
  onLog?: (entry: FoodLogIn) => void;
  logging?: boolean;
}) {
  const [code, setCode] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [grams, setGrams] = useState("100");
  const [scanError, setScanError] = useState<string | null>(null);

  const lookup = useQuery({
    queryKey: ["barcode", submitted],
    enabled: isValidBarcode(submitted),
    retry: false,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/nutrition/barcode/{code}", {
        params: { path: { code: submitted.trim() } },
      });
      if (response.status === 404) return null;
      if (!data) throw new Error("Lookup failed");
      return data;
    },
  });

  const submit = (value: string) => {
    setCode(value);
    setSubmitted(value.trim());
  };

  const food = lookup.data ?? null;
  const gramsNum = Number(grams) || 0;
  const macros = food ? macrosForGrams(food, gramsNum) : null;
  const canLog =
    !!food &&
    gramsNum > 0 &&
    macros?.kcal != null &&
    macros.protein != null &&
    macros.carbs != null &&
    macros.fat != null;

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold">Scan a food barcode</h2>
        <p className="text-sm text-zinc-500">
          Look up macros from Open Food Facts (external lookup, on-device scan).
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          inputMode="numeric"
          placeholder="Barcode digits"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <Button
          className="shrink-0"
          disabled={!isValidBarcode(code)}
          onClick={() => submit(code)}
        >
          Look up
        </Button>
      </div>

      <CameraScan onDetected={submit} onError={setScanError} />
      {scanError && <p className="text-xs text-amber-600">{scanError}</p>}

      {isValidBarcode(submitted) && (
        <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
          {lookup.isLoading ? (
            <p className="text-sm text-zinc-500">Looking up {submitted}…</p>
          ) : lookup.isError ? (
            <p className="text-sm text-amber-600">Lookup failed. Try again later.</p>
          ) : food == null ? (
            <p className="text-sm text-zinc-500">No product found for {submitted}.</p>
          ) : (
            <div className="flex flex-col gap-2">
              <div className="font-medium">{foodTitle(food)}</div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-zinc-500">Amount</span>
                <Input
                  type="number"
                  inputMode="numeric"
                  className="h-9 w-24"
                  value={grams}
                  onChange={(e) => setGrams(e.target.value)}
                />
                <span className="text-sm text-zinc-500">g</span>
              </div>
              <div className="grid grid-cols-4 gap-2 text-center">
                <Macro label="kcal" value={macros?.kcal} />
                <Macro label="P" value={macros?.protein} unit="g" />
                <Macro label="C" value={macros?.carbs} unit="g" />
                <Macro label="F" value={macros?.fat} unit="g" />
              </div>
              {onLog && (
                <Button
                  disabled={!canLog || logging}
                  onClick={() => {
                    if (!food || !canLog) return;
                    onLog({
                      name: foodTitle(food),
                      grams: Math.round(gramsNum * 10) / 10,
                      kcal: macros.kcal!,
                      protein_g: macros.protein!,
                      carbs_g: macros.carbs!,
                      fat_g: macros.fat!,
                      source: "barcode",
                      barcode: food.code,
                    });
                  }}
                >
                  {logging ? "Adding..." : "Add to log"}
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function Macro({ label, value, unit = "" }: { label: string; value: number | null | undefined; unit?: string }) {
  return (
    <div className="rounded-lg bg-white p-2 dark:bg-zinc-900">
      <div className="text-lg font-bold tabular-nums">{value == null ? "—" : `${value}${unit}`}</div>
      <div className="text-[10px] text-zinc-500">{label}</div>
    </div>
  );
}

function CameraScan({
  onDetected,
  onError,
}: {
  onDetected: (code: string) => void;
  onError: (message: string | null) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [scanning, setScanning] = useState(false);
  const supported = getBarcodeDetector() != null;

  useEffect(() => {
    if (!scanning) return;
    const Detector = getBarcodeDetector();
    if (!Detector || !navigator.mediaDevices?.getUserMedia) return;

    let stream: MediaStream | null = null;
    let raf = 0;
    let cancelled = false;
    const detector = new Detector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });

    const start = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        const video = videoRef.current;
        if (!video || cancelled) return;
        video.srcObject = stream;
        await video.play();
        const loop = async () => {
          if (cancelled || !video) return;
          try {
            const codes = await detector.detect(video);
            const value = codes[0]?.rawValue;
            if (value && isValidBarcode(value)) {
              onDetected(value);
              setScanning(false);
              return;
            }
          } catch {
            // transient detect errors are ignored; keep scanning.
          }
          raf = requestAnimationFrame(loop);
        };
        raf = requestAnimationFrame(loop);
      } catch {
        onError("Couldn’t start the camera. Enter the barcode manually.");
        setScanning(false);
      }
    };
    start();

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [scanning, onDetected, onError]);

  if (!supported) {
    return <p className="text-xs text-zinc-400">Camera scanning unavailable — enter digits above.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="secondary"
        onClick={() => {
          onError(null);
          setScanning((s) => !s);
        }}
      >
        {scanning ? "Stop camera" : "Scan with camera"}
      </Button>
      {scanning && (
        <video
          ref={videoRef}
          playsInline
          muted
          className="aspect-video w-full rounded-lg bg-zinc-100 object-cover dark:bg-zinc-950"
        />
      )}
    </div>
  );
}
