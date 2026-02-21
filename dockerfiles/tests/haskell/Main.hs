{-# LANGUAGE BangPatterns #-}
{-# LANGUAGE OverloadedStrings #-}
{-# OPTIONS_GHC -Wno-unused-imports -Wno-type-defaults -Wno-unused-do-bind -Wno-unused-matches #-}

import qualified Data.Array as Array
import qualified Data.ByteString.Char8 as BS
import qualified Data.IntMap.Strict as IntMap
import qualified Data.Map.Strict as Map
import qualified Data.Sequence as Seq
import qualified Data.Set as Set
import qualified Data.Text as T
import qualified Data.Text.IO as TIO
import qualified Data.Vector as V
import qualified Data.Vector.Algorithms.Intro as VAlgo
import qualified Data.Vector.Mutable as VM
import qualified Data.Vector.Unboxed as VU

import Control.DeepSeq (deepseq, NFData)
import Control.Lens (over, _1, view, (^.))
import Control.Monad.State.Strict (execState, modify)
import Data.Bifunctor (bimap)
import Data.Foldable (toList)
import Data.Graph.Inductive.Graph (mkGraph)
import Data.Graph.Inductive.PatriciaTree (Gr)
import Data.Graph.Inductive.Query.BFS (bfs)
import Data.Hashable (hash)
import Data.IORef (newIORef, readIORef, modifyIORef')
import Data.List (sort, intercalate)
import Data.List.Extra (trim, nubOrd)
import Data.List.Split (splitOn)
import Data.Scientific (scientific, toRealFloat)
import Data.WideWord.Int128 (Int128)
import Data.WideWord.Word128 (Word128)
import Data.Word (Word64)
import Numeric.LinearAlgebra (Matrix, ident, tr, (><))
import System.IO (hFlush, stdout)
import Data.Void (Void)
import Data.Time.Clock.POSIX (getPOSIXTime)
import System.Environment (lookupEnv)
import Text.Megaparsec (Parsec, parse, some)
import Text.Megaparsec.Char (digitChar)
import Text.Regex.TDFA ((=~))
import Text.Read (readMaybe)

import qualified AtCoder.Dsu as DSU

main :: IO ()
main = do
  -- containers (Data.Map, Data.Set, Data.Sequence, Data.IntMap)
  let m = Map.fromList [("a", 1), ("b", 2), ("c", 3)] :: Map.Map String Int
  assert "containers Map" (Map.lookup "b" m == Just 2)

  let s = Set.fromList [3, 1, 4, 1, 5]
  assert "containers Set" (Set.size s == 4)

  let sq = Seq.fromList [1, 2, 3] :: Seq.Seq Int
  assert "containers Seq" (Seq.length sq == 3)

  let im = IntMap.fromList [(1, "a"), (2, "b")]
  assert "containers IntMap" (IntMap.lookup 1 im == Just "a")

  -- array
  let arr = Array.listArray (0, 3) [10, 20, 30, 40] :: Array.Array Int Int
  assert "array" (arr Array.! 2 == 30)

  -- vector
  let vec = V.fromList [1, 2, 3, 4, 5] :: V.Vector Int
  assert "vector" (V.sum vec == 15)

  -- vector-algorithms
  sorted <- do
    mv <- V.thaw (V.fromList [5, 3, 1, 4, 2] :: V.Vector Int)
    VAlgo.sort mv
    V.freeze mv
  assert "vector-algorithms" (sorted == V.fromList [1, 2, 3, 4, 5])

  -- unboxing-vector (via vector-unboxed)
  let uvec = VU.fromList [1.0, 2.0, 3.0, 4.0] :: VU.Vector Double
  assert "vector-unboxed" (abs (VU.sum uvec - 10.0) < 1e-9)

  -- text
  let t = T.pack "Hello, Haskell!"
  assert "text" (T.length t == 15)

  -- bytestring
  let bs = BS.pack "AtCoder"
  assert "bytestring" (BS.length bs == 7)

  -- deepseq
  let xs = [1, 2, 3] :: [Int]
  xs `deepseq` assert "deepseq" True

  -- split
  let parts = splitOn "," "a,b,c,d"
  assert "split" (parts == ["a", "b", "c", "d"])

  -- extra
  let trimmed = trim "  hello  "
  assert "extra" (trimmed == "hello")
  let unique = nubOrd [3, 1, 2, 1, 3]
  assert "extra nubOrd" (sort unique == [1, 2, 3])

  -- hashable
  let h = hash ("test" :: String)
  assert "hashable" (h == h)

  -- lens
  let pair = (1, "hello") :: (Int, String)
  let pair' = over _1 (+1) pair
  assert "lens" (pair' ^. _1 == 2)

  -- bifunctors
  let bp = bimap (+1) (*2) (3, 4) :: (Int, Int)
  assert "bifunctors" (bp == (4, 8))

  -- mtl (State monad)
  let st = execState (do modify (+1); modify (*3)) (10 :: Int)
  assert "mtl" (st == 33)

  -- scientific
  let sci = scientific 314 (-2)
  assert "scientific" (abs (toRealFloat sci - 3.14 :: Double) < 1e-9)

  -- fgl (graph library)
  let g :: Gr String Int
      g = mkGraph [(1, "A"), (2, "B"), (3, "C")] [(1, 2, 1), (2, 3, 1)]
      reached = bfs 1 g
  assert "fgl" (sort reached == [1, 2, 3])

  -- megaparsec
  let parsed = parse (some digitChar :: Parsec Void String String) "" "12345"
  assert "megaparsec" (parsed == Right "12345")

  -- regex-tdfa
  let matched = ("hello123world" :: String) =~ ("([0-9]+)" :: String) :: String
  assert "regex-tdfa" (matched == "123")

  -- hmatrix
  let mat = ident 3 :: Numeric.LinearAlgebra.Matrix Double
  assert "hmatrix" (mat == tr mat)

  -- wide-word
  let w128 = 42 :: Word128
  let i128 = -100 :: Int128
  assert "wide-word" (w128 > 0 && i128 < 0)

  -- ac-library-hs
  dsu <- DSU.new 5
  DSU.merge dsu 0 1
  DSU.merge dsu 1 2
  same01 <- DSU.same dsu 0 2
  same03 <- DSU.same dsu 0 3
  assert "ac-library-hs" (same01 && not same03)

  -- IORef (primitive IO)
  ref <- newIORef (0 :: Int)
  modifyIORef' ref (+42)
  val <- readIORef ref
  assert "IORef" (val == 42)

  heavySeconds <- readHeavySeconds
  heavyAcc <- runHeavyWork heavySeconds

  putStrLn "HASKELL_OK"
  putStrLn ("HASKELL_HEAVY_OK " ++ show heavyAcc)
  hFlush stdout

assert :: String -> Bool -> IO ()
assert label True  = return ()
assert label False = error $ label ++ " check failed"

readHeavySeconds :: IO Int
readHeavySeconds = do
  env <- lookupEnv "HEAVY_SECONDS"
  case env of
    Nothing -> return 2
    Just s ->
      case readMaybe s of
        Just n | n >= 1 -> return n
        _ -> error "invalid HEAVY_SECONDS"

runHeavyWork :: Int -> IO Int
runHeavyWork heavySeconds = do
  start <- getPOSIXTime
  let deadline = start + fromIntegral heavySeconds
      spin :: Int -> Int -> Int
      spin !acc 0 = acc
      spin !acc n = spin ((acc * 1103515245 + n + 12345) `mod` 1000000007) (n - 1)
      loop :: Int -> IO Int
      loop !acc = do
        now <- getPOSIXTime
        if now >= deadline
          then return acc
          else loop $! spin acc 100000
  loop 1
