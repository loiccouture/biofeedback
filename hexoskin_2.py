import asyncio
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
import numpy as np
from colour import Color
import tkinter as tk
import time
import socket

PARTICIPANT_NUMBER = 'ministudy-test-05'

# Hexoskin UUIDs
hx_respiration_uuid = "9bc730c3-8cc0-4d87-85bc-573d6304403c"
hx_heartRate_uuid = "00002a37-0000-1000-8000-00805f9b34fb"
hx_activity_uuid = "75246a26-237a-4863-aca6-09b639344f43"


class App:
    async def exec(self):
        self.window = Gui(asyncio.get_event_loop())
        await self.window.test()

class Gui(tk.Tk):
    """Creates window ctkinter object"""
    WIDTH = 780
    HEIGHT = 520

    def __init__(self, loop):
        super().__init__() # Initialize the main Window
        self.loop = loop
        self.root = tk.Tk()
        self.running = True

        ##### SETUP WINDOW #####
        # Setting up initial window parameters
        self.root.title("Engagement Countermeasure")
        # self.protocol("WM_DELETE_WINDOW", self.on_closing)  # call .on_closing() when app gets closed
        self.root.resizable(True, True)
        self.root.geometry(f"{Gui.WIDTH}x{Gui.HEIGHT}")

        # Data lists
        self.raw_respiration = []
        self.raw_activity = []
        self.respiration = []
        self.activity = []
        self.activity_g = []
        self.ts = []

        # Counters
        self.len_respiration = 0
        self.len_activity = 0
        
        self.indexAccumulation = []
        self.maxIndex = 1
        self.minIndex = 1000000

        # Colors
        red = Color("red")
        self.colorGradient = list(red.range_to(Color("green"),101))

        ## FUNCTIONS
        self.createDataFiles()



    def createDataFiles(self):
        with open('data/' + PARTICIPANT_NUMBER + '_biofeedback_data.txt', 'a') as f:
            f.write('DATAFILE - ' + PARTICIPANT_NUMBER + ' - Biofeedback Data \n')
            f.write('ts \t std_respiration \t std_activity \t mean_activity \t index_raw \t index_scaled \t minIndex \t maxIndex\n')
            f.close()
        
        with open('data/'+PARTICIPANT_NUMBER+'_raw_data.txt', 'a') as f:
            f.write('DATAFILE - ' + PARTICIPANT_NUMBER + ' - RAW Data from Hexoskin \n')
            f.write('ts \t respiration data (6 bytes) \t Activity data (7 bytes)\n')
            f.close()
        
        with open('data/'+PARTICIPANT_NUMBER+'_data.txt', 'a') as f:
            f.write('DATAFILE - ' + PARTICIPANT_NUMBER + ' - Data \n')
            f.write('ts \t resp rate \t raw activity \t G activity \n')
            f.close()

    def send_udp_message(self, message, ip, port):
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            # Send the message
            sock.sendto(message.encode('utf-8'), (ip, port))
            print(f"Sent message: {message}")
        except socket.error as e:
            print(f"Error: {e}")
        finally:
            # Close the socket
            sock.close()

    def callback_respiration(self, sender: BleakGATTCharacteristic, data: bytearray):
        self.raw_respiration.append(data)
        self.respiration.append(int(data[1]))
        for d in data:
            print(f"{d}")
        print("\n")

    
    
    def callback_activity(self, sender: BleakGATTCharacteristic, data: bytearray):
        self.raw_activity.append(data)
        self.activity.append(int(data[3]))
        self.activity_g.append(int(data[3])/256)
        for d in data:
            print(f"{d}")
        print("\n")


    async def init_client(self):
        # Make sure that we are connected to hexoskin 
        await self.client.is_connected()
        print("connected to hexoskin")
        with open('data/' + PARTICIPANT_NUMBER + '_Flags.txt', 'a') as f:
            f.write(str(time.time()) + "\t HX client connected\n")
            f.close()

        # Read respiration characteristic (Hexoskin)
        await self.client.start_notify(hx_respiration_uuid, self.callback_respiration)
        print("start respiration notifications")
        with open('data/' + PARTICIPANT_NUMBER + '_Flags.txt', 'a') as f:
            f.write(str(time.time()) + "\t Respiration notification start\n")
            f.close()
        
        # Read activity characteristic (Hexoskin)
        await self.client.start_notify(hx_activity_uuid, self.callback_activity)
        print("start activity notifications")
        with open('data/' + PARTICIPANT_NUMBER + '_Flags.txt', 'a') as f:
            f.write(str(time.time()) + "\t Activity notification start\n")
            f.close()


    async def test(self):
        while self.running:
            async with BleakClient("F4160023-5AC0-4519-D78D-28B4E9C8C481") as client_hexoskin:
                self.client = client_hexoskin
                
                # Initialize client notification
                await self.init_client()
                
                # Initiate disconnect callback - Hexoskin
                client_hexoskin.set_disconnected_callback(on_disconnect_hx())
                
                while self.running and await client_hexoskin.is_connected():
                    # Check if new data was added
                    if(len(self.activity) > self.len_activity and len(self.respiration) > self.len_respiration):
                        # Get timestamp
                        self.ts.append(time.time())

                        # Write RAW data to file
                        with open('data/' + PARTICIPANT_NUMBER + '_raw_data.txt', 'a') as f:
                            len_blancs = 6 - len(self.raw_respiration[-1])
                            f.write(str(self.ts[-1])) 
                            for resp in self.raw_respiration[-1]:
                                f.write('\t' + str(resp))
                            
                            if(len_blancs):
                                for n in range(len_blancs):
                                    f.write("\t NA")
                            
                            for act in self.raw_activity[-1]:
                                f.write("\t" + str(act))
                            f.write('\n')
                            f.close()


                        # Write Processed data to file
                        with open('data/' + PARTICIPANT_NUMBER + '_data.txt', 'a') as f:
                            f.write(str(self.ts[-1]) + "\t" + str(self.respiration[-1]) + '\t' + str(self.activity[-1]) + '\t' + str(self.activity_g[-1])) 
                            f.write('\n')
                            f.close()


                        # if more than 30 seconds, but under 40 seconds (data 1 Hz)
                        if(len(self.respiration) >= 30 and len(self.activity_g) >= 30 and len(self.respiration) < 40 and len(self.activity_g) < 40):
                            # Calculate the window parameters
                            std_respiration = np.std(self.respiration[-30:])
                            std_activity = np.std(self.activity_g[-30:])
                            mean_activity = np.mean(self.activity_g[-30:])

                            # Print window parameter 
                            print("std respiration = "+ str(std_respiration))
                            print("std activity = "+ str(std_activity))
                            print("mean activity = "+ str(mean_activity))
                            
                            # Calculate Engagement index
                            engagement_index = (435.7 * std_activity) - (175.4 * mean_activity) - (0.78 * std_respiration)
                            print("ei init = "+ str(engagement_index))

                            # Accumulate engagement max and min
                            self.indexAccumulation.append(engagement_index)
                        
                            if(len(self.respiration) == 39):
                                self.maxIndex = max(self.indexAccumulation)
                                self.minIndex = min(self.indexAccumulation)
                        


                        # if more than 30 seconds have passed (data 1 Hz)
                        if(len(self.respiration) >= 40 and len(self.activity_g) >= 40):
                            # Calculate the window parameters
                            std_respiration = np.std(self.respiration[-30:])
                            std_activity = np.std(self.activity_g[-30:])
                            mean_activity = np.mean(self.activity_g[-30:])

                            # Print window parameter 
                            print("std respiration = "+ str(std_respiration))
                            print("std activity = "+ str(std_activity))
                            print("mean activity = "+ str(mean_activity))
                            
                            # Calculate Engagement index
                            engagement_index = (435.7 * std_activity) - (175.4 * mean_activity) - (0.78 * std_respiration)
                            print("ei init = "+ str(engagement_index))
                            
                            if(engagement_index < self.minIndex):
                                self.minIndex = engagement_index
                                print("MinIndex=" + str(self.minIndex) + ", engagement index=" + str(engagement_index))
                            
                            if(engagement_index > self.maxIndex):
                                self.maxIndex = engagement_index
                                print("MaxIndex=" + str(self.maxIndex) + ", engagement index=" + str(engagement_index))

                            ei = int(((engagement_index - self.minIndex)/(self.maxIndex - self.minIndex))*100)
                            print(ei)
                            # ei = (engagement_index/self.maxIndex)*100

                            with open('data/'+PARTICIPANT_NUMBER+'_biofeedback_data.txt', 'a') as f:
                                f.write(str(self.ts[-1]) + '\t' + str(std_respiration) + '\t' + str(std_activity) + '\t' + str(mean_activity) + '\t' + str(engagement_index) + '\t' + str(ei)  + '\t' + str(self.minIndex)+ '\t'+ str(self.maxIndex)+ '\n')
                                f.close()

                            print("ei second = "+ str(ei))
                            
                            self.root.configure(bg=self.colorGradient[ei])
                            message = str(self.colorGradient[ei])
                            ip = "10.199.11.255"
                            port = 12345
                            self.send_udp_message(message, ip, port)
                            self.root.update()

                        self.len_activity += 1
                        self.len_respiration += 1

                    await asyncio.sleep(0.1)

def on_disconnect_hx():
    print("disconnected from Hexoskin")


async def main():
    # Create Flags file
    with open('data/' + PARTICIPANT_NUMBER + '_Flags.txt', 'a') as f:
        f.write('DATAFILE - ' + PARTICIPANT_NUMBER + ' - Flags timestamps \n')
        f.write('UNIX \t Type \n')
        f.close()
    
    # Start GUI App
    await App().exec()
        

asyncio.run(main())