import socket
import threading
import json
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

class MultiThreadedClient(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.CHAT_SERVER_IP = "10.100.102.12"
        self.CHAT_SERVER_PORT = 5555
        self.chat_messages = []
        self.new_subject = ""
        self.username = ""
        self.messages = []
        self.current_game = []
        self.found_player = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stop_flag = threading.Event() # Event to signal thread termination
        self.client_thread = threading.Thread(target=self.connect)
        
        self.chat_thread = threading.Thread(target=self.receive_messages_chat)
        self.stop_chat_flag = threading.Event()

        self.encryption = Encryption()

    def run(self):
        self.client_thread.start()

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to server at {self.host}:{self.port}")
        self.receive_data()
        
    def disconnect(self):
        print("Client disconnected")
        self.stop_flag.set() # Set the stop flag to signal thread termination
        self.client_socket.close()

    def send_message(self, data):
        json_message = json.dumps(data)
        self.client_socket.send(json_message.encode())

    def receive_data(self):
        while not self.stop_flag.is_set(): # Check the stop flag in the loop
            try:
                data = self.client_socket.recv(1024)            
                msg = self.decode_json(data)
                if not msg:
                    break
                if type(msg) is list:
                    if msg[0] == "login" or msg[0] == "signup":
                        if msg[1] == "success":
                            self.username = msg[2]
                        self.messages = msg # ["login/signup, "success", self.username])
                        
                    if msg[0] == "game" and msg[1] == "chat" and msg[2] == "joining":
                        self.found_player = True
                        self.messages = msg
                    else:
                        self.messages = msg
                        self.found_player = False
            except:
                self.client_socket.close()

    def decode_json(self, data):
        try:
            decoded_data = data
            if decoded_data:
                return json.loads(decoded_data)
            else:
                # Handle the case when the decoded data is empty
                return None
        except json.decoder.JSONDecodeError as e:
            # Handle the invalid JSON case
            print(f"Error decoding JSON: {e}")
            return None
    
    def connect_to_chat(self):
        self.stop_flag.set()
        self.stop_chat_flag.clear()
        self.chat_thread = threading.Thread(target=self.receive_messages_chat).start()

    def receive_messages_chat(self):
        while not self.stop_chat_flag.is_set():
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                msg = self.decode_json(data)

                if msg[0] and msg[0] == "game" and msg[1] and msg[1] == "chat" and msg[2] and msg[2] == "new round":
                    self.new_subject = msg[3]
                else:
                    self.chat_messages.append(msg)
            except Exception as e:
                break

    def leave_chat(self):
        self.stop_flag.clear()
        self.stop_chat_flag.set()
        self.client_thread = threading.Thread(target=self.receive_data).start()

class Encryption:
    def __init__(self, key=None):
        pass

    def encrypt(self, data):
        salt = os.urandom(16)
        nonce = os.urandom(16)
        # Ensure password is encoded if it's a string
        if isinstance(data, str):
            data = data.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(b'password')  # Replace with your secret key
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        tag = encryptor.tag
        return [str(encrypted_data), str(salt), str(nonce), str(tag)]