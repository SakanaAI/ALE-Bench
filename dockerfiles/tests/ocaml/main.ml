open Core

let () =
  let sum_core = List.fold [1; 2; 3; 4] ~init:0 ~f:( + ) in
  if sum_core <> 10 then failwith "core check failed";

  let z = Z.(add (of_int 40) (of_int 2)) in
  if Z.to_int z <> 42 then failwith "zarith check failed";

  let n = Num.(add_num (Int 1) (Int 2)) in
  if Num.int_of_num n <> 3 then failwith "num check failed";

  let ccl = CCList.map (( + ) 1) [1; 2; 3] in
  if not (Stdlib.( = ) ccl [2; 3; 4]) then failwith "containers check failed";

  let iter_sum = Iter.(0 -- 4 |> fold ( + ) 0) in
  if iter_sum <> 10 then failwith "iter check failed";

  let bat_sum = BatList.fold_left ( + ) 0 [1; 2; 3; 4] in
  if bat_sum <> 10 then failwith "batteries check failed";

  let heavy_seconds =
    match Sys.getenv "HEAVY_SECONDS" with
    | None -> 2
    | Some s ->
        (match Int.of_string_opt s with
        | Some n when n >= 1 -> n
        | _ -> failwith "invalid HEAVY_SECONDS")
  in
  let deadline =
    Time_ns.add (Time_ns.now ()) (Time_ns.Span.of_sec (Float.of_int heavy_seconds))
  in
  let rec spin acc i =
    if i = 0 then acc
    else spin ((acc * 1103515245 + i + 12345) mod 1000000007) (i - 1)
  in
  let rec run acc =
    if Time_ns.compare (Time_ns.now ()) deadline >= 0 then acc
    else run (spin acc 100000)
  in
  let heavy_acc = run 1 in

  printf "OCAML_OK\n";
  printf "OCAML_HEAVY_OK %d\n" heavy_acc
