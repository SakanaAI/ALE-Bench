import Mathlib
import Parser
import Regex.Regex.Utilities
import Regex.Regex.Elab

def main : IO Unit := do
  IO.println s!"Hello, sqrt 9 = {Nat.sqrt 9}"
  let re := Regex.parse! r##"bool|boolean"##
  IO.println s!"{re.find "boolean"}"
