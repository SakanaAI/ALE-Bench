def main : IO Unit := do
  let mut chunks : Array (Array UInt64) := #[]
  for i in [0:10] do
    let chunk := Array.mkArray (16 * 1024 * 1024) (UInt64.ofNat i)
    chunks := chunks.push chunk
  if chunks.size == 0 then
    throw <| IO.userError "allocation failed"
