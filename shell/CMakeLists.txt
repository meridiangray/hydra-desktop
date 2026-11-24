cmake_minimum_required(VERSION 3.25)
project(hydra_desktop LANGUAGES CXX)

include(FetchContent)
set(saucer_examples OFF CACHE BOOL "" FORCE)
set(saucer_tests OFF CACHE BOOL "" FORCE)
set(saucer_serializer Glaze CACHE STRING "" FORCE)
FetchContent_Declare(saucer
    GIT_REPOSITORY https://github.com/saucer/saucer.git
    GIT_TAG 5afd6097b200fadc70af23e9d6f50f4e8dfb4354
)
FetchContent_MakeAvailable(saucer)

set(HYDRA_SRC "${CMAKE_CURRENT_SOURCE_DIR}/../../hydra-git/src/hydra" CACHE PATH
    "hydra's package folder (hydra-git/src/hydra): the window bar is read from its wiki/assets/windowbar.js")
file(READ "${HYDRA_SRC}/wiki/assets/windowbar.js" HYDRA_DESKTOP_CHROME)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${HYDRA_SRC}/wiki/assets/windowbar.js")
configure_file(chrome.hpp.in chrome.hpp @ONLY)

add_executable(hydra-desktop-shell main.cpp)
target_include_directories(hydra-desktop-shell PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_features(hydra-desktop-shell PRIVATE cxx_std_23)
target_link_libraries(hydra-desktop-shell PRIVATE saucer::saucer)
if(WIN32)
    enable_language(RC)
    target_sources(hydra-desktop-shell PRIVATE icon.rc)
    target_include_directories(hydra-desktop-shell PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    target_link_libraries(hydra-desktop-shell PRIVATE saucer::private shell32 dwmapi)
endif()
install(TARGETS hydra-desktop-shell RUNTIME DESTINATION bin)
