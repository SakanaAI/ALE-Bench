let () =
  let chunks = Array.init 70 (fun i -> Bytes.make (16 * 1024 * 1024) (Char.chr (i land 255))) in
  if Array.length chunks <> 70 then failwith "allocation failed"
