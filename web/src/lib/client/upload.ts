export type UploadResult = { jobId: string };

export async function uploadVideo(file: File, signal?: AbortSignal): Promise<UploadResult> {
  const response = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'content-type': file.type || 'video/mp4' },
    body: file,
    signal
  });
  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(text || `upload failed with status ${response.status}`);
  }
  return response.json();
}
