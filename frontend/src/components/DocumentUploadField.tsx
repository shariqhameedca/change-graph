import { useRef } from "react";
import { useExtractDocumentText } from "../hooks/useApi";

/** A file picker that reads a .txt/.md/.pdf regulation document and hands
 * the extracted plain text back to the caller. PDF extraction happens on
 * the backend (pypdf); text files are decoded there too, for one
 * consistent code path regardless of file type. */
export function DocumentUploadField({ onExtracted }: { onExtracted: (text: string, filename: string) => void }) {
  const extract = useExtractDocumentText();
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    extract.mutate(file, {
      onSuccess: (result) => onExtracted(result.text, result.filename),
    });
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="field">
      <label>Upload a document (.txt, .md, or .pdf)</label>
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md,.pdf,text/plain,application/pdf"
        onChange={handleFileChange}
        disabled={extract.isPending}
      />
      {extract.isPending && <span className="text-muted" style={{ fontSize: 12 }}>Extracting text...</span>}
      {extract.isError && (
        <span className="error-block" style={{ fontSize: 12, padding: "6px 10px" }}>
          {(extract.error as Error).message}
        </span>
      )}
      {extract.isSuccess && !extract.isPending && (
        <span className="text-secondary" style={{ fontSize: 12 }}>
          Loaded {extract.data.character_count.toLocaleString()} characters from {extract.data.filename}. Review it below before saving.
        </span>
      )}
    </div>
  );
}
