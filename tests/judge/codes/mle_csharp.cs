using System.Collections.Generic;

var chunks = new List<byte[]>();
for (int i = 0; i < 66; ++i) {
    var chunk = new byte[16 * 1024 * 1024];
    for (int j = 0; j < chunk.Length; j += 4096) {
        chunk[j] = (byte)((i + j) & 255);
    }
    chunks.Add(chunk);
}
