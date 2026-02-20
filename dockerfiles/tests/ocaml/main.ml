open Core

let () =
  let sum_core = List.fold [1; 2; 3; 4] ~init:0 ~f:( + ) in
  if sum_core <> 10 then failwith "core check failed";

  let z = Z.(add (of_int 40) (of_int 2)) in
  if Z.to_int z <> 42 then failwith "zarith check failed";

  let n = Num.(add_num (Int 1) (Int 2)) in
  if Num.int_of_num n <> 3 then failwith "num check failed";

  let ccl = CCList.map (( + ) 1) [1; 2; 3] in
  if ccl <> [2; 3; 4] then failwith "containers check failed";

  let iter_sum = Iter.(0 -- 4 |> fold ( + ) 0) in
  if iter_sum <> 10 then failwith "iter check failed";

  let bat_sum = BatList.fold_left ( + ) 0 [1; 2; 3; 4] in
  if bat_sum <> 10 then failwith "batteries check failed";

  printf "OCAML_OK\n"
