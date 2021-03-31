aux_source_directory(. MY_LIB_FILES)

# generate a static library ( *.a)
add_library(MYLIB ${MY_LIB_FILES})

# generate a .so file
# ADD_LIBRARY(mylib SHARED ${mylibSRCS})