# {
# 'Register address': {'0': '0x0484'}, 'Field': {'0': 'Frequency_Grid'},
# 'Type': {'0': 'U16'},
# 'Accuracy': {'0': 0.01},
# 'Unit': {'0': 'Hz'},
# 'Min': {'0': None},
# 'Max': {'0': None},
# 'Read/Write': {'0': 'R'},
# 'Remarks': {'0': 'Grid frequency'},
# 'User': {'0': 'End User'},
# 'title': {'0': 'Grid frequency'},
# 'metric_type': {'0': 'gauge'},
# 'metric_name': {'0': 'OutpuFreq'},
# 'label_name': {'0': 'Grid'},
# 'label_value': {'0': 'Frequency'}}


import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lsw3.globals import (
    REG_ADDR,
    REG_FRIENDLY_NAME,
    REG_ID,
    REG_DEVICE_CLASS,
    REG_RATIO,
    REG_ROUND,
    REG_TITLE,
    REG_TYPE,
    REG_UNIT,
    REG_VALUE,
    REG_MIN,
    REG_MAX,
    InverterDef,
)
from appframe.config_data import configData
from appframe.logger import app_log

MAP_REGISTER = "Register address"


from appframe.helpers import DictType, HelperOp


csv_file = os.path.join(os.path.dirname(__file__), "registers.csv")
data = []
mapping = {}
radek = 0
with open(csv_file, "r", newline="") as csvfile:
    reader = csv.DictReader(csvfile, delimiter="\t")
    for row in reader:
        data.append(row)
        for k, v in row.items():
            if not k in mapping:
                mapping[k] = {}
            s_radek = str(radek)
            if k == "Accuracy":
                mapping[k][s_radek] = float(v)
            else:
                mapping[k][s_radek] = v
        radek += 1


for k, v in mapping[REG_ADDR].items():
    mapping[REG_ADDR][k] = HelperOp.h_fill(v)


def do_map(register, responsereg) -> DictType:
    err: bool = False
    retval: dict = {}
    register_match: bool = False
    for k, v in mapping[REG_ADDR].items():
        if str(register) != v:
            continue
        register_match = True
        for reg in (
            REG_ADDR,
            REG_TITLE,
            REG_RATIO,
            REG_ROUND,
            REG_TYPE,
            REG_UNIT,
            REG_DEVICE_CLASS,
            REG_MIN,
            REG_MAX,
            REG_FRIENDLY_NAME,
        ):
            retval[reg] = mapping[reg][k]

        value = 0
        if retval[REG_TYPE] == "U16":
            try:
                value = float(int(responsereg, 16)) * float(retval[REG_RATIO])
            except:
                app_log.debug(
                    f"Chyba v transferu hodnoty typ: {retval[REG_TYPE]} hodnota: {responsereg} ratio: {retval[REG_RATIO]}"
                )
                err = True
                break

        elif retval[REG_TYPE] == "I16":
            try:
                value = float(
                    HelperOp.twosComplement_hex(responsereg) * float(retval[REG_RATIO])
                )
            except:
                app_log.debug(
                    f"Chyba v transferu hodnoty typ: {retval[REG_TYPE]} hodnota: {responsereg} ratio: {retval[REG_RATIO]}"
                )
                err = True
                break
        else:
            app_log.error(f"Neznámý typ {reg}")
            break
        try:
            retval_float: float = round(value, int(retval[REG_ROUND]))

        except:
            err = True
            break

        try:
            if retval[REG_MIN] != retval[REG_MAX]:
                min: float = float(retval[REG_MIN])
                max: float = float(retval[REG_MAX])
                err = (retval_float < min) or (retval_float > max)
        except:
            err = True
            app_log.error("Chybne zadana hodnota min nebo max")
        retval[REG_VALUE] = str(retval_float)

        retval[REG_ID] = str(
            str(InverterDef.inverter_sn) + "_" + str(int(retval[REG_ADDR], 16))
        )
        break  # Nalezeny register
    if retval == {}:
        err = True
    return None if err else retval


if __name__ == "__main__":
    print(mapping)
