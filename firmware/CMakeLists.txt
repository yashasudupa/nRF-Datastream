cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(nrf_ble_fw C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_EXTENSIONS ON)

target_sources(app PRIVATE
  src/main.c
  services/gatt_service.c
  drivers/imu_lsm6dsv32x.c
)

target_include_directories(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/services
  ${CMAKE_CURRENT_SOURCE_DIR}/drivers
)
