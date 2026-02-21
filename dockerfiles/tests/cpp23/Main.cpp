#include <absl/strings/str_cat.h>
#include <atcoder/dsu>
#include <boost/multiprecision/cpp_int.hpp>
#include <Eigen/Dense>
#include <gmpxx.h>
#include <LightGBM/c_api.h>
#include <ankerl/unordered_dense.h>
#include <dlfcn.h>
#include <immer/vector.hpp>
#include <ortools/linear_solver/linear_solver.h>
#include <range/v3/all.hpp>
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#include <torch/torch.h>
#pragma GCC diagnostic pop
#include <z3++.h>

#include <filesystem>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

void check(bool condition, const char* message) {
  if (!condition) {
    std::cerr << message << std::endl;
    std::exit(1);
  }
}

int main() {
  // ac-library
  atcoder::dsu uf(4);
  uf.merge(0, 1);
  check(uf.same(0, 1), "atcoder::dsu check failed");

  // abseil
  std::string greeting = absl::StrCat("hello", " ", "world");
  check(greeting == "hello world", "abseil StrCat check failed");

  // boost (multiprecision)
  boost::multiprecision::cpp_int big = 1;
  for (int i = 1; i <= 20; ++i) big *= i;
  check(big == boost::multiprecision::cpp_int("2432902008176640000"), "boost multiprecision check failed");

  // eigen
  Eigen::Matrix2d mat;
  mat << 1, 2, 3, 4;
  check(std::abs(mat.determinant() - (-2.0)) < 1e-9, "eigen determinant check failed");

  // gmp
  mpz_class a("123456789012345678901234567890");
  mpz_class b("987654321098765432109876543210");
  mpz_class c = a + b;
  check(c.get_str() == "1111111110111111111011111111100", "gmp addition check failed");

  // unordered_dense
  ankerl::unordered_dense::map<int, int> mp;
  mp[7] = 11;
  check(mp[7] == 11, "unordered_dense check failed");

  // immer
  auto vec = immer::vector<int>{1, 2, 3};
  check(vec.size() == 3, "immer vector check failed");

  // range-v3
  auto doubled = std::vector<int>{};
  for (int x : ranges::views::iota(1, 5)) {
    doubled.push_back(x * 2);
  }
  check(doubled.size() == 4 && doubled[0] == 2 && doubled[3] == 8, "range-v3 check failed");

  // z3
  z3::context ctx;
  z3::solver s(ctx);
  z3::expr x = ctx.int_const("x");
  s.add(x > 10);
  check(s.check() == z3::sat, "z3 solver check failed");

  // lightgbm
  const char* lgbm_error = LGBM_GetLastError();
  check(lgbm_error != nullptr, "LightGBM C API check failed");

  // libtorch
  auto tensor = torch::tensor({1, 2, 3});
  check(tensor.sum().item<int>() == 6, "libtorch tensor check failed");

  // or-tools
  auto* solver = operations_research::MPSolver::CreateSolver("GLOP");
  check(solver != nullptr, "or-tools GLOP solver creation failed");
  auto* var = solver->MakeNumVar(0.0, 1.0, "x");
  solver->MutableObjective()->SetCoefficient(var, 1);
  solver->MutableObjective()->SetMaximization();
  auto status = solver->Solve();
  check(status == operations_research::MPSolver::OPTIMAL, "or-tools solve check failed");
  check(std::abs(var->solution_value() - 1.0) < 1e-9, "or-tools solution check failed");
  delete solver;

  int heavy_seconds = 2;
  if (const char* raw = std::getenv("HEAVY_SECONDS"); raw != nullptr) {
    heavy_seconds = std::atoi(raw);
  }
  check(heavy_seconds >= 1, "invalid HEAVY_SECONDS");

  const auto start = std::chrono::steady_clock::now();
  const auto deadline = start + std::chrono::seconds(heavy_seconds);
  std::uint64_t acc = 1;
  while (std::chrono::steady_clock::now() < deadline) {
    for (std::uint64_t i = 1; i <= 100000; ++i) {
      acc = (acc * 1103515245ULL + i + 12345ULL) % 1000000007ULL;
    }
  }

  std::cout << "CPP23_OK" << std::endl;
  std::cout << "CPP23_HEAVY_OK " << acc << std::endl;
  return 0;
}
