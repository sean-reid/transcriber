export function readVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';
    const cleanup = () => {
      URL.revokeObjectURL(url);
      video.src = '';
    };
    video.onloadedmetadata = () => {
      const seconds = video.duration;
      cleanup();
      if (!Number.isFinite(seconds)) {
        reject(new Error('unreadable video'));
        return;
      }
      resolve(seconds);
    };
    video.onerror = () => {
      cleanup();
      reject(new Error('could not read video metadata'));
    };
    video.src = url;
  });
}
