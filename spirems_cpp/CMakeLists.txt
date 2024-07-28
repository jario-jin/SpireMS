cmake_minimum_required(VERSION 3.0 FATAL_ERROR)
cmake_policy(SET CMP0054 NEW)

set(PROJECT_VERSION 0.2.0)
project(SpireMS VERSION ${PROJECT_VERSION} LANGUAGES CXX)

add_definitions(-DAPI_EXPORTS)
set(CMAKE_BUILD_TYPE "Release")


find_package(OpenCV REQUIRED)
message(STATUS "OpenCV library status:")
message(STATUS "    version: ${OpenCV_VERSION}")
message(STATUS "    libraries: ${OpenCV_LIBS}")
message(STATUS "    include path: ${OpenCV_INCLUDE_DIRS}")


include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)


# Public header
set(
  public_HEADS
  include/sms_core.h
  include/sms_helper.h
  include/sms_publisher.h
  include/sms_subscriber.h
)

# SpireMS source
set(spirems_SRCS
  src/sms_helper.cpp
  src/sms_publisher.cpp
  src/sms_subscriber.cpp
)

add_library(sms_core SHARED ${spirems_SRCS})
target_link_libraries(
  sms_core
  ${OpenCV_LIBS}
)


# Demo
add_executable(PublisherDemo demo/publisher_demo.cpp)
target_link_libraries(PublisherDemo sms_core)
add_executable(SubscriberDemo demo/subscriber_demo.cpp)
target_link_libraries(SubscriberDemo sms_core)

