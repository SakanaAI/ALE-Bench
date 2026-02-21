const chunks: Buffer[] = [];
for (let i = 0; i < 70; ++i) {
  const chunk = Buffer.alloc(16 * 1024 * 1024, i & 255);
  chunks.push(chunk);
}

if (chunks.length !== 70) {
  throw new Error('allocation failed');
}
