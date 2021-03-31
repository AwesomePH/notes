// .bss
int global_uninitialized_int;

// .data
int global_initialized_int = 1;

// .data
static int global_static_initialized_int = 2;

extern int extern_int;

int fun();

int main() {
  // .data
  static int local_static_int = 3;
  
  int local = extern_int;

  local = fun();
}