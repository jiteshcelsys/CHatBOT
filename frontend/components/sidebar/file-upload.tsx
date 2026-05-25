"use client";
import { useRef, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import apiClient from "@/services/api/client";

interface IngestionResponse {
  ingestion_id: string;
  filename: string;
  status: string;
  message: string;
}

interface IngestionStatus {
  ingestion_id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  total_chunks: number;
  new_chunks: number;
  duplicate_chunks: number;
  error?: string;
}

interface ActiveJob {
  ingestion_id: string;
  filename: string;
  status: IngestionStatus["status"];
  total_chunks: number;
  new_chunks: number;
  error?: string;
}

const ACCEPTED = ".pdf,.txt,.docx,.md,.markdown";

function StatusBadge({ status }: { status: ActiveJob["status"] }) {
  const map = {
    pending:    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    processing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    completed:  "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed:     "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };
  const label = {
    pending: "Pending…",
    processing: "Processing…",
    completed: "Ready",
    failed: "Failed",
  };
  return (
    <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded-full", map[status])}>
      {label[status]}
    </span>
  );
}

export function FileUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [collection, setCollection] = useState("documents");
  const [jobs, setJobs] = useState<ActiveJob[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll all non-terminal jobs every 2s
  useEffect(() => {
    const pending = jobs.filter((j) => j.status === "pending" || j.status === "processing");
    if (pending.length === 0) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }

    if (pollRef.current) return; // already polling

    pollRef.current = setInterval(async () => {
      setJobs((prev) => {
        const active = prev.filter((j) => j.status === "pending" || j.status === "processing");
        if (active.length === 0) { clearInterval(pollRef.current!); pollRef.current = null; }
        return prev;
      });

      const updates = await Promise.all(
        pending.map(async (job) => {
          try {
            const { data } = await apiClient.get<{ data: IngestionStatus }>(
              `/ingest/status/${job.ingestion_id}`
            );
            return data.data;
          } catch { return null; }
        })
      );

      setJobs((prev) =>
        prev.map((job) => {
          const update = updates.find((u) => u?.ingestion_id === job.ingestion_id);
          if (!update) return job;
          return {
            ...job,
            status: update.status,
            total_chunks: update.total_chunks,
            new_chunks: update.new_chunks,
            error: update.error,
          };
        })
      );
    }, 2000);

    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [jobs]);

  const uploadFile = async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    form.append("collection", collection);
    form.append("chunk_size", "1000");
    form.append("chunk_overlap", "200");

    try {
      const { data } = await apiClient.post<{ data: IngestionResponse }>(
        "/ingest/",
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setJobs((prev) => [
        {
          ingestion_id: data.data.ingestion_id,
          filename: file.name,
          status: "pending",
          total_chunks: 0,
          new_chunks: 0,
        },
        ...prev,
      ]);
    } catch (e: unknown) {
      setJobs((prev) => [
        {
          ingestion_id: crypto.randomUUID(),
          filename: file.name,
          status: "failed",
          total_chunks: 0,
          new_chunks: 0,
          error: e instanceof Error ? e.message : "Upload failed",
        },
        ...prev,
      ]);
    }
  };

  const handleFiles = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setUploading(true);
    await Promise.all(list.map(uploadFile));
    setUploading(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeJob = (id: string) =>
    setJobs((prev) => prev.filter((j) => j.ingestion_id !== id));

  return (
    <div className="px-3 py-2 space-y-2">
      <input
        value={collection}
        onChange={(e) => setCollection(e.target.value)}
        placeholder="Collection name"
        className="w-full text-xs px-2 py-1 rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-ring"
      />

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors text-xs select-none",
          dragging
            ? "border-violet-500 bg-violet-50 dark:bg-violet-950/20"
            : "border-muted-foreground/30 hover:border-violet-400 hover:bg-muted/50"
        )}
      >
        {uploading ? (
          <p className="text-muted-foreground animate-pulse">Uploading…</p>
        ) : (
          <>
            <p className="text-muted-foreground">Drop files or click to upload</p>
            <p className="text-muted-foreground/50 mt-0.5">PDF · TXT · DOCX · Markdown</p>
          </>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />

      {/* Job status list */}
      {jobs.length > 0 && (
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {jobs.map((job) => (
            <div key={job.ingestion_id} className="rounded-lg border bg-background px-2.5 py-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium truncate flex-1">{job.filename}</p>
                <div className="flex items-center gap-1 shrink-0">
                  <StatusBadge status={job.status} />
                  {(job.status === "completed" || job.status === "failed") && (
                    <button
                      onClick={() => removeJob(job.ingestion_id)}
                      className="text-muted-foreground hover:text-foreground ml-1"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>

              {(job.status === "pending" || job.status === "processing") && (
                <div className="mt-1.5 h-1 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-violet-500 rounded-full animate-pulse w-1/2" />
                </div>
              )}

              {job.status === "completed" && job.new_chunks > 0 && (
                <p className="text-muted-foreground mt-1">
                  ✓ {job.new_chunks} chunks indexed into <span className="font-medium">{collection}</span>
                </p>
              )}

              {job.status === "failed" && (
                <p className="text-red-500 mt-1">{job.error ?? "Unknown error"}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
