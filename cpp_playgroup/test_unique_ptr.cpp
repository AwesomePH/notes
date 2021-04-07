#include <memory>
#include <iostream>

int main() {
  auto up = std::make_unique<int[]>(5); // since c++14
}