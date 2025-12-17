import can
import time
import random
import threading


# This class simulates the ECU controller
class CanController():

    def __init__(self, bus_interface: str, bus_type: str):
        print(bus_interface,bus_type)
        self.__bus = can.interface.Bus(bus_interface,interface=bus_type)

    def get_bus(self):
        return self.__bus
    
# This class simulates the ECU
class CanECU():
    
    def __init__(self, canController: CanController, can_id: int, time_out:float):
        self.__canController = canController
        self.__isRunning = False
        self.__id = can_id
        self.__timeout = time_out

    def send_message(self,data:list):
        msg = can.Message(arbitration_id=self.__id, data=data, is_extended_id=False)
        self.__canController.get_bus().send(msg)

    def __ecu_action(self):
        while self.__isRunning:
            self.send_message([random.randint(0,250)])
            time.sleep(self.__timeout)

    def start_ecu(self):
        self.__isRunning = True
        print(f"Starting ECU {self.__id}...")
        t = threading.Thread(target=self.__ecu_action, daemon=True)
        t.start()

    def stop_ecu(self):
        self.__isRunning = False


if __name__ == "__main__":

        canc1 = CanController('vcan0', 'socketcan')
        ecu1 = CanECU(canc1,100,0.1)
        ecu2 = CanECU(CanController('vcan0', 'socketcan'),200,0.2)
        ecu1.start_ecu()
        ecu2.start_ecu()

        # Read what is happening on the bus
        bus = can.interface.Bus('vcan0', interface='socketcan')
        try:
            while True:
                msg = bus.recv()
                if msg is not None:
                    print(f"ID: {hex(msg.arbitration_id)}, Data: {msg.data}, Timestamp: {msg.timestamp}")
        except KeyboardInterrupt:
            print("Stopping ECUs")
