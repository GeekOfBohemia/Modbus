# Hlavni routina pro vyvoj

from logging import DEBUG
import sys
import socket
import binascii
import libscrc
import os

import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from appframe.config_data import configData
from appframe.ha_client import HaClient
from lsw3.InverterMap import do_map
from lsw3.globals import (
    REG_DEVICE_CLASS,
    REG_FRIENDLY_NAME,
    REG_ID,
    REG_UNIT,
    REG_VALUE,
    InverterDef,
)


from appframe.helpers import HelperOp
from appframe.core_control import CoreControl
from appframe.logger import app_log
from appframe.homeassistant_mqtt import (
    MQTT_SENSOR_DEVICE_CLASS,
    MQTT_SENSOR_DEVICE_IDENTIFIER,
    MQTT_SENSOR_DEVICE_NAME,
    MQTT_SENSOR_ID,
    MQTT_SENSOR_NAME,
    MQTT_SENSOR_PREFIX_ID,
    MQTT_SENSOR_STATE,
    MQTT_SENSOR_UNIT,
    HomeAssistantMQTT,
)

mapping = (
    (REG_FRIENDLY_NAME, MQTT_SENSOR_NAME),
    (REG_ID, MQTT_SENSOR_ID),
    (REG_DEVICE_CLASS, MQTT_SENSOR_DEVICE_CLASS),
    (REG_VALUE, MQTT_SENSOR_STATE),
    (REG_UNIT, MQTT_SENSOR_UNIT),
)


class DataReg(HaClient):
    def __init__(self):
        super().__init__()
        cfg = configData.get_cfg_data("Inverter")
        InverterDef.inverter_ip = cfg.get("inverter_ip", "")
        InverterDef.inverter_port = cfg.get("inverter_port", "")
        InverterDef.inverter_sn = int(cfg.get("inverter_sn", 0))
        InverterDef.device_name = cfg.get("device_name", "")
        InverterDef.device_idenitifier = cfg.get("device_identifier", "")
        InverterDef.sensor_prefix_id = cfg.get("sensor_prefix_id", "")

        self.ha_mqtt = HomeAssistantMQTT("inverter")
        # Here is configuration what registers to read
        self.loop = [
            "0x0600",
            "0x0610",
            "0x03C0",
            "0x03CA",
            "0x0480",
            "0x04BC",
            "0x04BD",
            "0x04C0",
            "0x580",
            "0x05B4",
        ]

    def read(self):
        loop = self.loop.copy()
        while loop:

            pfin = int(loop.pop(-1), 0)
            pini = int(loop.pop(-1), 0)
            # Data logger frame begin
            start = binascii.unhexlify("A5")  # Logger Start code
            length = binascii.unhexlify("1700")  # Logger frame DataLength
            controlcode = binascii.unhexlify("1045")  # Logger ControlCode
            serial = binascii.unhexlify("0000")  # Serial
            datafield = binascii.unhexlify(
                "020000000000000000000000000000"
            )  # com.igen.localmode.dy.instruction.send.SendDataField
            # Modbus request begin
            pos_ini = str(HelperOp.hex_zfill(pini)[2:])
            pos_fin = str(HelperOp.hex_zfill(pfin - pini + 1)[2:])
            businessfield = binascii.unhexlify(
                "0003" + pos_ini + pos_fin
            )  # Modbus data to count crc
            app_log.info(
                "Modbus request: 0103 "
                + pos_ini
                + " "
                + pos_fin
                + " "
                + str(HelperOp.padhex(hex(libscrc.modbus(businessfield)))[4:6])  # type: ignore
                + str(HelperOp.padhex(hex(libscrc.modbus(businessfield)))[2:4])  # type: ignore
            )

            crc = binascii.unhexlify(
                str(HelperOp.padhex(hex(libscrc.modbus(businessfield)))[4:6])  # type: ignore
                + str(HelperOp.padhex(hex(libscrc.modbus(businessfield)))[2:4])  # type: ignore
            )  # CRC16modbus
            # Modbus request end
            checksum = binascii.unhexlify("00")  # checksum F2
            endCode = binascii.unhexlify("15")  # Logger End code
            inverter_sn2 = bytearray.fromhex(
                hex(InverterDef.inverter_sn)[8:10]
                + hex(InverterDef.inverter_sn)[6:8]
                + hex(InverterDef.inverter_sn)[4:6]
                + hex(InverterDef.inverter_sn)[2:4]
            )
            frame = bytearray(
                start
                + length
                + controlcode
                + serial
                + inverter_sn2
                + datafield
                + businessfield
                + crc
                + checksum
                + endCode
            )

            app_log.info(
                "Hex string to send: A5 1700 1045 0000 "
                + hex(InverterDef.inverter_sn)[8:10]
                + hex(InverterDef.inverter_sn)[6:8]
                + hex(InverterDef.inverter_sn)[4:6]
                + hex(InverterDef.inverter_sn)[2:4]
                + " 020000000000000000000000000000 "
                + "0104"
                + pos_ini
                + pos_fin
                + str(hex(libscrc.modbus(businessfield))[3:5])  # type: ignore
                + str(hex(libscrc.modbus(businessfield))[2:3].zfill(2))  # type: ignore
                + " 00 15"
            )

            app_log.info(f"Data sent: {frame}")
            # Data logger frame end

            checksum = 0
            frame_bytes = bytearray(frame)
            for i in range(1, len(frame_bytes) - 2, 1):
                checksum += frame_bytes[i] & 255
            frame_bytes[len(frame_bytes) - 2] = int((checksum & 255))

            # OPEN SOCKET
            for res in socket.getaddrinfo(
                InverterDef.inverter_ip,
                InverterDef.inverter_port,
                socket.AF_INET,
                socket.SOCK_STREAM,
            ):
                family, socktype, proto, canonname, sockadress = res
                try:
                    clientSocket = socket.socket(family, socktype, proto)
                    clientSocket.settimeout(15)
                    clientSocket.connect(sockadress)
                except socket.error as msg:
                    app_log.info(f"Could not open socket: {msg}")
                    return

                # SEND DATA
                clientSocket.sendall(frame_bytes)

                ok: bool = False
                data = None
                while not ok:
                    try:
                        data = clientSocket.recv(1024)
                        ok = True
                        if data is None:
                            ok = False
                            return

                    except:
                        """
                        self.warning(
                            "Connection timeout - inverter and/or gateway is off"
                        )
                        """
                        return

                # PARSE RESPONSE (start position 56, end position 60)
                if data is None:
                    return
                app_log.info(f"Data received: {data}")
                i = pfin - pini  # Number of registers
                a = 0  # Loop counter
                response = str(
                    "".join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(data))
                )  # +'  '+re.sub('[^\x20-\x7f]', '', '')));

                hexstr = str(
                    " ".join(hex(ord(chr(x)))[2:].zfill(2) for x in bytearray(data))
                )
                app_log.info(f"Hex string received: {hexstr.upper()}")

                data_arr = []
                while a <= i:
                    p1 = 56 + (a * 4)
                    p2 = 60 + (a * 4)
                    responsereg = response[p1:p2]
                    hexpos = str("0x") + str(hex(a + pini)[2:].zfill(4)).upper()
                    err: bool = False
                    try:
                        v = int(str(responsereg), 16) * 0.01
                    except:
                        v = 0
                        err = True

                    if err:
                        data_arr = []
                        break

                    reg = do_map(hexpos, responsereg)
                    if reg is None:
                        app_log.debug(
                            f"Registr: {hexpos} hex: {responsereg} value: {v}"
                        )
                    else:
                        print(reg)

                        data_json = {
                            MQTT_SENSOR_PREFIX_ID: InverterDef.sensor_prefix_id,
                            MQTT_SENSOR_DEVICE_NAME: InverterDef.device_name,
                            MQTT_SENSOR_DEVICE_IDENTIFIER: InverterDef.device_idenitifier,
                        }
                        for source, target in mapping:
                            data_json[target] = reg.get(source, "")
                        unit: str = data_json.get("unit_of_measurement", "")
                        if unit == "%":
                            try:
                                value: float = float(data_json.get("state", "0.0"))
                                err = (value > 100) or (value < 5)
                            except:
                                err = True
                        if err:
                            app_log.debug("Error for data")
                            data_arr = []
                            break
                        else:
                            data_arr.append(data_json)
                    a += 1
                if not err:
                    for data_json in data_arr:
                        self.ha_mqtt.discover_sensor(data_json)


if __name__ == "__main__":
    app_log.setLevel(DEBUG)
    ls = DataReg()
    ls.start()
    while not CoreControl.stop_flag:
        time.sleep(1)
    ls.stop()
