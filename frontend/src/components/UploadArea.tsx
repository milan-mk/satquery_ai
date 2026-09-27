import { useRef, useState } from "react";
import { UploadCloud, X } from "lucide-react";

interface Props {
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}

export default function UploadArea({ files, onChange, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = [...files, ...Array.from(list)].slice(0, 2);
    onChange(next);
  }

  function removeAt(i: number) {
    onChange(files.filter((_, idx) => idx !== i));
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? "border-cyan-400 bg-cyan-950/30" : "border-slate-700 bg-slate-900/50"
        } ${disabled ? "cursor-not-allowed opacity-50" : "hover:border-slate-500"}`}
      >
        <UploadCloud className="h-8 w-8 text-slate-400" />
        <p className="text-sm text-slate-300">
          Drop 1–2 images (GeoTIFF/TIFF/PNG/JPEG), or click to browse
        </p>
        <p className="text-xs text-slate-500">Single image, or a pair for change/cross-modal analysis</p>
        <input
          ref={inputRef}
          type="file"
          accept=".tif,.tiff,.png,.jpg,.jpeg"
          multiple
          hidden
          disabled={disabled}
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-3 space-y-1">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="flex items-center justify-between rounded bg-slate-800 px-3 py-2 text-sm text-slate-200"
            >
              <span className="truncate">{f.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeAt(i);
                }}
                className="text-slate-400 hover:text-red-400"
                aria-label={`Remove ${f.name}`}
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
