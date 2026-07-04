cmake_minimum_required(VERSION 3.20)

project(silwright_simple_lang_example LANGUAGES CXX)

add_executable(
    simple_lang_example
    simple_lang.cpp
    simple_lang_dump.cpp
    simple_lang_main.cpp
    simple_lang_visitor.cpp
)

target_compile_features(simple_lang_example PRIVATE cxx_std_20)
set_target_properties(simple_lang_example PROPERTIES CXX_EXTENSIONS OFF)
