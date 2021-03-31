cmake_minimum_required(VERSION 2.8)

project(prj_test_compile)

# add_executable(demo test_objs.cpp some_defs.cpp)

aux_source_directory(. SRCS)

add_executable(demo ${SRCS})

add_subdirectory(my_lib)

target_link_libraries(demo MYLIB)