using System;
using System.Collections.Generic;

public static class Program
{
    public static void Main()
    {
        var chunks = new List<byte[]>();
        for (int i = 0; i < 70; ++i)
        {
            var chunk = new byte[16 * 1024 * 1024];
            for (int j = 0; j < chunk.Length; j += 4096)
            {
                chunk[j] = (byte)((i + j) & 255);
            }
            chunks.Add(chunk);
        }

        if (chunks.Count != 70)
        {
            throw new Exception("allocation failed");
        }
    }
}
