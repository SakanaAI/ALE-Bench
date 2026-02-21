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

  IO.println s!"LEAN_OK {d}"
