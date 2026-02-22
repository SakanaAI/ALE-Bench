using System;
using AtCoder;
using MathNet.Numerics.LinearAlgebra;
using Microsoft.ML;
using Microsoft.ML.Trainers.LightGbm;
using System.Diagnostics;

public static class Program
{
    public static void Main()
    {
        var dsu = new Dsu(4);
        dsu.Merge(0, 1);
        if (!dsu.Same(0, 1))
        {
            throw new Exception("ac-library-csharp Dsu check failed");
        }

        var vec = Vector<double>.Build.DenseOfArray(new[] { 1.0, 2.0, 3.0 });
        var norm = vec.L2Norm();
        if (Math.Abs(norm - Math.Sqrt(14.0)) > 1e-9)
        {
            throw new Exception("MathNet.Numerics check failed");
        }

        var ml = new MLContext(seed: 1);
        var options = new LightGbmRegressionTrainer.Options { NumberOfLeaves = 4 };
        if (options.NumberOfLeaves != 4)
        {
            throw new Exception("Microsoft.ML.LightGbm options check failed");
        }

        var heavySecondsRaw = Environment.GetEnvironmentVariable("HEAVY_SECONDS") ?? "2";
        if (!int.TryParse(heavySecondsRaw, out var heavySeconds) || heavySeconds < 1)
        {
            throw new Exception($"invalid HEAVY_SECONDS: {heavySecondsRaw}");
        }

        var sw = Stopwatch.StartNew();
        long acc = 1;
        while (sw.Elapsed.TotalSeconds < heavySeconds)
        {
            for (int i = 1; i <= 100000; ++i)
            {
                acc = (acc * 1103515245 + i + 12345) % 1000000007;
            }
        }

        Console.WriteLine($"CSHARP_OK {ml.GetType().Name}");
        Console.WriteLine($"CSHARP_HEAVY_OK {acc}");
    }
}
