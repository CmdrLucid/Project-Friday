cmake_minimum_required(VERSION 3.16)
project(landstalker C)

# genrecomp checkout; build.sh clones it into .deps/
set(GENRECOMP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.deps/genrecomp" CACHE PATH "genrecomp checkout")
if(NOT EXISTS "${GENRECOMP_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "genrecomp not found at ${GENRECOMP_DIR}. Run ./build.sh")
endif()
add_subdirectory(${GENRECOMP_DIR} genrecomp_build)

# src/recomp is generated from your own ROM and never committed
file(GLOB RECOMP_SOURCES src/recomp/*.c)
if(NOT RECOMP_SOURCES)
    message(FATAL_ERROR "src/recomp/ is empty. Run ./build.sh path/to/your.rom")
endif()

add_executable(landstalker src/main.c ${RECOMP_SOURCES})
target_link_libraries(landstalker PRIVATE genrecomp)
target_include_directories(landstalker PRIVATE src/)
