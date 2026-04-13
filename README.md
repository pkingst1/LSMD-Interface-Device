# LSMD-Interface-Device
 DataInterfaceApplication folder contains GUI Interface for interactions with Limb Strength Measurement Device (LSMD)
  - Python version 12.9 is needed to run this application **https://www.python.org/downloads/release/python-3129/** 
  - In order to install the application as an exe, double click to run the build_exe.bat file, this will create a dist folder that will contain LSMD_Interface.exe application

 PIC32MX Final- This PIC32MX Final contains the firmware required to program the LSMD-DIU microcontroller. This system is responsible for signal acquisition and processing of load cell data, while managing critical communication between the power management system, enclosure interface, and the BLE module.
 - src/: Contains the raw source code. This can be used for version control tracking or manual compilation.
 - PIC32MX.X/: The official MPLAB X project folder. This contains the configuration and project files necessary to modify, debug, and upload code to the microcontroller.
 - Note: Using the MPLAB X project folder is the recommended method for programming and development.

nRF DK - This folder contains the current version of software that was flashed to the nRF52 Development Kit
This version of software successfully allowed secure BLE communications in a lab setting with a Bluetooth enabled laptop running the LSMD-DIU GUI Interface application
The nRF52 Development Kit used was v2.7.0 and it used all relevant toolchains and managers as per the nRF Connect page via Nordic Semiconductor. A wizard within Visual Studio gave guidance on downloading these packages.
The nRF52 DK was programmed from a cloned BLE UART Service from within the nRF Connect libraries installed on Visual Studio.
The main files needed to edit for functionality with the LSMD DIU GUI Interface application are as follows:
- app.overlay: this file programs the physical pins and buttons of the nRF DK as well as setting UART speed
- prj.conf: this file sets the core nRF capabilities and quantities such as enabling BLE, GPIOs, RTT and console
- main.c: this file contains the running program of the nRF52 DK and contains calls to all necessary libraries. It also contains all necessary functionality for sending and receiving to PIC32 and the connected device.
