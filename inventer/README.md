# SOFAR Inverter 8KTL-3PH + LSW-3
Code for SOFAR Inverter for HomeAssistant.
This is not typical integration - running on isolate server communication with HomeAssistant is via REST-API

For the base was used MichaluxPL library together with knowledge https://www.elektroda.pl/rtvforum/topic3698233-240.html
# Required python modules
```
libscrc
pandas
```

# Required my modules
```
appframe
```

# Structure to run
```bash

your_directory
├── appframe
│   ├── __init__.py
|
├── lsw3
│   ├── InverterDataReg.py
│   ├── registers.xls
config.cfg
control.log
```
  

Main file: InverterDataReg.py
Configuration