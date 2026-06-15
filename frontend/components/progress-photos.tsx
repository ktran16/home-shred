"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button, Card, Input, Label } from "@/components/ui";
import { api, type ProgressPhotoOut } from "@/lib/api";

// Progress photos gallery (SPEC §19.8 W3). Upload is a native multipart POST (openapi-fetch
// isn't used for file bodies); images are served from the backend via the /api proxy.
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ProgressPhotosCard() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [date, setDate] = useState(() => todayIso());
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const photos = useQuery({
    queryKey: ["progress-photos"],
    queryFn: async () => (await api.GET("/api/progress/photos")).data ?? [],
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["progress-photos"] });

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a photo first");
      const form = new FormData();
      form.append("file", file);
      form.append("date", date);
      if (note.trim()) form.append("note", note.trim());
      const res = await fetch("/api/progress/photos", { method: "POST", body: form });
      if (!res.ok) {
        throw new Error(
          res.status === 415
            ? "Use a JPEG, PNG, or WebP image"
            : res.status === 413
              ? "Image too large (max 10 MB)"
              : "Upload failed",
        );
      }
    },
    onSuccess: () => {
      setFile(null);
      setNote("");
      if (fileRef.current) fileRef.current.value = "";
      invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: async (id: number) => {
      const { error } = await api.DELETE("/api/progress/photos/{photo_id}", {
        params: { path: { photo_id: id } },
      });
      if (error) throw new Error("Could not delete photo");
    },
    onSuccess: invalidate,
  });

  const list: ProgressPhotoOut[] = photos.data ?? [];

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold">Progress photos</h2>
        <p className="text-sm text-zinc-500">
          Private, stored on your server. Newest first — compare over time.
        </p>
      </div>

      <div className="flex flex-col gap-2 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-950">
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
          aria-label="Choose progress photo"
        />
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_2fr]">
          <div>
            <Label>Date</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <Label>Note (optional)</Label>
            <Input
              placeholder="e.g. front, week 4"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
        </div>
        <Button onClick={() => upload.mutate()} disabled={upload.isPending || !file}>
          {upload.isPending ? "Uploading…" : "Upload photo"}
        </Button>
        {upload.isError && <p className="text-sm text-red-600">{upload.error.message}</p>}
      </div>

      {photos.isLoading ? (
        <p className="text-sm text-zinc-500">Loading photos…</p>
      ) : photos.isError ? (
        <p className="text-sm text-red-600">Could not load photos.</p>
      ) : list.length === 0 ? (
        <p className="text-sm text-zinc-500">No photos yet — upload one to start tracking.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {list.map((photo) => (
            <figure
              key={photo.id}
              className="group relative overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.image_url}
                alt={photo.note ?? `Progress photo ${photo.date}`}
                className="aspect-square w-full object-cover"
                loading="lazy"
              />
              <figcaption className="flex items-center justify-between gap-1 px-2 py-1 text-[11px]">
                <span className="truncate">
                  {photo.date}
                  {photo.note ? ` · ${photo.note}` : ""}
                </span>
                <button
                  onClick={() => remove.mutate(photo.id)}
                  aria-label={`Delete photo ${photo.date}`}
                  className="shrink-0 text-zinc-400 hover:text-red-600"
                >
                  ×
                </button>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </Card>
  );
}
