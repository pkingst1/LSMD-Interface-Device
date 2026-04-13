# LSMD-Interface-Device
 DataInterfaceApplication folder contains GUI Interface for interactions with Limb Strength Measurement Device (LSMD)
  - Python version 12.9 is needed to run this application **https://www.python.org/downloads/release/python-3129/** 
  - In order to install the application as an exe, double click to run the build_exe.bat file, this will create a dist folder that will contain LSMD_Interface.exe application

 PIC32MX Final- This PIC32MX Final contains the firmware required to program the LSMD-DIU microcontroller. This system is responsible for signal acquisition and processing of load cell data, while managing critical communication between the power management system, enclosure interface, and the BLE module.
 - src/: Contains the raw source code. This can be used for version control tracking or manual compilation.
 - PIC32MX.X/: The official MPLAB X project folder. This contains the configuration and project files necessary to modify, debug, and upload code to the microcontroller.
 - Note: Using the MPLAB X project folder is the recommended method for programming and development.
