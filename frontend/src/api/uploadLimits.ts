export const MAX_UPLOAD_FILE_BYTES = 100 * 1024 * 1024;
export const MAX_UPLOAD_FILE_LABEL = "100 MB";

export function assertFilesWithinUploadLimit(files: Array<Pick<File, "name" | "size">>) {
  const oversized = files.find((file) => file.size > MAX_UPLOAD_FILE_BYTES);
  if (!oversized) {
    return;
  }
  const fileName = oversized.name || "所选文件";
  throw new Error(`${fileName} 超过 ${MAX_UPLOAD_FILE_LABEL} 上传限制，请选择更小的文本文件。`);
}
