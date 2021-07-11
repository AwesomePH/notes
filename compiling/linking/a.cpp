extern int b_global_int;

int a_func() {
    return 1;
}

int main(int argc, const char** argv) {
    int b = b_global_int;
    return 0;
}