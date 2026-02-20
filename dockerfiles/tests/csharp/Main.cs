using System;
using AtCoder;
using MathNet.Numerics.LinearAlgebra;
using Microsoft.ML;
using Microsoft.ML.Trainers.LightGbm;

public static class Program
{
    public static void Main()
    {
        var dsu = new DSU(4);
        dsu.Merge(0, 1);
        if (!dsu.Same(0, 1))
        {
            throw new Exception("ac-library-csharp DSU check failed");
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

        Console.WriteLine($"CSHARP_OK {ml.GetType().Name}");
    }
}
