import Mathlib
import Parser
import Regex.Regex.Utilities
import Regex.Regex.Elab

open Parser in
def testParser : Bool :=
  let p : SimpleParser Substring Char Char := Char.ASCII.alpha
  match p.run "hello" with
  | .ok _ _ => true
  | .error _ _ => false

def spin (acc : UInt64) : Nat → UInt64
  | 0 => acc
  | n + 1 =>
      let next :=
        (acc * (UInt64.ofNat 1103515245) + UInt64.ofNat n + UInt64.ofNat 12345) %
          UInt64.ofNat 1000000007
      spin next n

def readHeavySeconds : IO Nat := do
  match (← IO.getEnv "HEAVY_SECONDS") with
  | none => pure 2
  | some raw =>
      match raw.toNat? with
      | some n =>
          if n >= 1 then
            pure n
          else
            throw <| IO.userError s!"invalid HEAVY_SECONDS: {raw}"
      | none => throw <| IO.userError s!"invalid HEAVY_SECONDS: {raw}"

def main : IO Unit := do
  -- mathlib
  let d := Nat.sqrt 81
  if d != 9 then
    throw <| IO.userError "mathlib sqrt check failed"

  -- lean-regex
  let re := Regex.parse! r##"ab+c"##
  if re.find "abbbc" == none then
    throw <| IO.userError "lean-regex check failed"

  -- parser
  if !testParser then
    throw <| IO.userError "parser check failed"

  let heavySeconds ← readHeavySeconds
  let iterations := heavySeconds * 2000000
  let heavyAcc := spin 1 iterations

  IO.println s!"LEAN_OK {d}"
  IO.println s!"LEAN_HEAVY_OK {heavyAcc}"
