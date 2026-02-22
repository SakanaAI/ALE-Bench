import Control.Monad (forM)
import qualified Data.ByteString as BS

main :: IO ()
main = do
  chunks <- forM [1 .. 70 :: Int] $ \i -> do
    let chunk = BS.replicate (16 * 1024 * 1024) (fromIntegral i)
    if BS.length chunk == 16 * 1024 * 1024
      then pure chunk
      else fail "allocation failed"

  if length chunks /= 70
    then fail "allocation failed"
    else pure ()
