const ALPHABET = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';

export function jobId(): string {
  const bytes = new Uint8Array(18);
  crypto.getRandomValues(bytes);
  let out = '';
  for (const b of bytes) {
    out += ALPHABET[b % ALPHABET.length];
  }
  return out;
}
