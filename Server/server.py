import socket
import select
from server_utils import UsersDB, ScoresDB, Message, Sorting_Numbers, Encryption
from getmac import getmac
import json
import random

SERVER_IP = '10.100.102.12'
SERVER_PORT = 12345

def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(1024)
            client_message = data.decode('utf-8')
            if not data or client_message == "exit":
                break
            print(f"Received data: {data.decode('utf-8')}")

    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_exit(client_socket)

def client_exit(client_socket):
    client_socket.close()
    print("Client has disconnected")


class Server:
    # handles the multiuser server
    def __init__(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.current_usernames = []
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.message = Message()
        self.encryption = Encryption()
        self.clients = [self.server_socket]
        self.clients_names = {}
        
        self.current_associations_index = -1
        self.waiting_for_next_round = 0
        self.wfc = []
        self.chat_players = {}
        self.chat_messages = {}
        self.chat_players_flags = 0
        self.used_words = []
        self.clients_encryption_key = {}

        with open('./Server/associations.json', 'r') as file:
            self.associations = json.load(file)

        self.database = UsersDB()
        self.scores = ScoresDB()
        self.sorting_numbers = Sorting_Numbers()
        self.messages = {}

        # Initialize rlist, wlist, and xlist
        self.rlist = []
        self.wlist = []
        self.xlist = []


    def start(self):
        print(f"Server is listening on {self.server_socket.getsockname()}")

        while True:
            # Copy the clients list to rlist for monitoring read events
            self.rlist = list(self.clients)
            rlist, _, _ = select.select(self.rlist, self.wlist, self.xlist)

            for sock in rlist:  
                if sock == self.server_socket:
                    # New connection, accept it
                    client_socket, client_address = self.server_socket.accept()
                    self.clients.append(client_socket)
                    print(f"New connection from {client_address}")
                    # gets new client's mac address
                    mac_address = getmac.get_mac_address(ip=client_address[0])            
                    self.clients_names[client_socket] = [mac_address, ""]

                    if self.database.check_mac_address(mac_address):
                        username = self.database.get_username_by_mac(mac_address)
                        self.clients_names[client_socket][1] = username
                        client_socket.send(self.message.encode_json(["remember me", username]))
                else:
                    # Handle data from an existing client
                    try:
                        data = sock.recv(1024)
                        temp = list(self.message.decode_json(data))
                        self.messages[sock] = temp
                        result_msg = self.handle_messages()
                        if result_msg is not None:
                            if (result_msg[0] == "login" or result_msg[0] == "signup") and result_msg[1] == "success":
                                self.clients_names[sock][1] = result_msg[2]
                            result_json_msg = self.message.encode_json(result_msg)
                            sock.send(result_json_msg)

                    except:
                        username = self.clients_names[sock][1]
                        if username in self.chat_players:
                            self.chat_players.remove(username)
                            if len(self.wfc) != 0:
                                self.chat_players.append(self.wfc[0])
                                self.clients_names[self.wfc[0]].send(self.message.encode_json(["game", "chat", "joining"]))
                        self.clients_names.pop(sock)
                        self.clients.remove(sock)
                        print("Server: Client has been disconnected")
                    

    def handle_messages(self):
        for sock in self.messages:
            msg = self.messages[sock]
            if type(msg) is list:
                if msg[0] == "login":
                    print("TTTTTTTTTTTTTTTTT")
                    print(type(msg[2]))
                    print(type(json.loads(msg[2])))
                    if self.database.try_login(msg[1], json.loads(msg[2])):
                        username = msg[1]
                        if not bool(self.database.check_remember_me(username)) and msg[3]:
                            mac_address = self.clients_names[sock][0]
                            self.database.update_other_users_mac_address(mac_address)
                            self.database.remember_me_on(mac_address, username)
                        self.messages.pop(sock)
                        return ["login", "success", username] # msg[1] -> username
                    else:
                        if self.database.check_user_registered(msg[1]):
                            self.database.check_user_registered(msg[1])
                        self.messages.pop(sock)
                        return ["login", "error", self.database.check_user_registered(msg[1])]
                    
                if msg[0] == "signup":
                    if not self.database.check_user_registered(msg[1]):
                        mac_address = self.clients_names[sock][0]
                        if msg[3]:
                            self.database.update_other_users_mac_address(mac_address)
                            self.database.insert_user(msg[1], msg[2], msg[3], mac_address)
                        else:
                            self.database.insert_user(msg[1], msg[2], msg[3], "")
                        print("new user successfully registered")
                        username = msg[1]
                        self.messages.pop(sock)
                        return ["signup", "success", username] # [2] -> username
                    else:
                        # the username is already exists
                        print("This username is already exists")
                        self.messages.pop(sock)
                        return ["signup", "error", msg[1]]

                if msg[0] == "database":
                    if msg[1] == "check remember me status":
                        self.messages.pop(sock)
                        return [bool(self.database.check_remember_me(msg[2]))]
                    elif msg[1] == "change remember me":
                        if msg[2]:
                            self.database.remember_me_on(self.clients_names[sock][0], msg[3])
                        else:
                            self.database.remember_me_off(msg[3])
                        self.messages.pop(sock)
                        return ["changed remember me"]
                    elif msg[1] == "get last score mean":
                        if self.scores.checkUserExists(msg[2]):
                            self.messages.pop(sock)
                            return [self.scores.get_last_score(msg[2]), self.scores.getMean(msg[2])]
                        self.messages.pop(sock)
                        return [0, 0]
                    
                if msg[0] == "game":

                    if msg[1] == "sorting numbers":
                        if msg[2] == "start":
                            numbers = self.sorting_numbers.generate_numbers()
                            self.messages.pop(sock)
                            return ["game", "sorting numbers", numbers]
                        
                        if msg[2] == "check sorted numbers":
                            if int(msg[3]) == int(''.join(map(str, sorted(self.sorting_numbers.numbers_to_sort)))):
                                # mean = self.scores.getMean(msg[4])
                                self.messages.pop(sock)
                                return ["game", "sorting numbers", "success"] # , mean
                            self.messages.pop(sock)
                            return ["game", "sorting numbers", "fail"]
                        
                        if msg[2] == "set score":
                            time = msg[4]
                            score = int(((300-time)/30)**2)
                            self.scores.insert_score(msg[3], "sorting numbers", score)
                            self.messages.pop(sock)
                            return ["game", "sorting numbers", "successfully set score", score]
                            
                    if msg[1] == "chat":
                        if msg[2] == "join":
                            if len(self.chat_players) == 5:
                                self.wfc.append(msg[3])
                                self.messages.pop(sock)
                                return ["game", "chat", "full chat"]
                            else:
                                self.chat_players[sock] = [msg[3], 0] # updating player list that currently in the chat
                                self.wfc = []
                                self.chat_players_flags = len(self.chat_players)
                                self.messages.pop(sock)
                                if self.chat_players_flags == 1: # checks if this user is the only user that is in the chat
                                    index = random.randint(0, len(self.associations.keys())-1) # picks an index between 0 to num of the keys in the associations.json file
                                    while index == self.current_associations_index:
                                        # if the chosen index is the last index, it will choose another index untill it will be a new index
                                        index = random.randint(0, len(self.associations.keys())-1) # picks an index between 0 to num of the keys in the associations.json file
                                    self.current_associations_index = index
                                    return ["game", "chat", "joining", list(self.associations.keys())[index]]
                                self.waiting_for_next_round += 1
                                return ["game", "chat", "waiting for round"]
                        
                        elif msg[2] == "leave":
                            if len(self.wfc) != 0:
                                self.chat_players[sock] = [self.wfc[0], 0]
                                for sock2 in self.clients_names:
                                    if self.clients_names[sock2][1] == self.wfc[0]:
                                        sock2.send(self.message.encode_json(["game", "chat", "joining"]))
                            score = self.chat_players[sock][1]
                            self.chat_players.pop(sock)
                            self.chat_players_flags = len(self.chat_players)
                            self.messages.pop(sock)
                            return ["game", "chat", "kicking client", score]
                        
                        elif msg[2] == "sending temp message":
                            self.messages.pop(sock)
                            return ["game", "chat", "temp message"]

                        elif msg[2] == "cancel":
                            if msg[3] in self.wfc:
                                self.wfc.remove(msg[3]) # removes the client from the waiting list
                            if sock in self.chat_players:
                                self.chat_players.pop(sock)
                                self.chat_players_flags = len(self.chat_players)
                            self.messages.pop(sock)
                            return ["game", "chat", "cancel"]

                        elif msg[2] == "send message":
                            if msg[4] in self.used_words:
                                self.messages.pop(sock)
                                return ["game", "chat", "already used"]
                            if msg[4].lower() in self.associations[list(self.associations.keys())[self.current_associations_index]]:
                                self.chat_messages[sock] = str(msg[3] + ": " + msg[4])
                                self.used_words.append(msg[4])
                                self.chat_players[sock][1] += 1
                                self.broadcast_message()
                                return ["game", "chat", "sent"]
                            self.messages.pop(sock)
                            return ["game", "chat", "nope"]
    
                        elif msg[2] == "change subject":
                            self.chat_players_flags -= self.waiting_for_next_round
                            if self.chat_players_flags != 1:
                                self.chat_players_flags -= 1
                                self.messages.pop(sock)
                                return None
                            else:
                                self.chat_players_flags = len(self.chat_players)
                                
                                index = random.randint(0, len(self.associations.keys())-1) # picks an index between 0 to num of the keys in the associations.json file
                                while index == self.current_associations_index:
                                    # if the chosen index is the last index, it will choose another index untill it will be a new index
                                    index = random.randint(0, len(self.associations.keys())-1) # picks an index between 0 to num of the keys in the associations.json file
                                self.current_associations_index = index
                                for s_player in self.chat_players.keys():
                                    if s_player != sock: # sending the message to each player in the game except the player who sent the message
                                        s_player.send(self.message.encode_json(["game", "chat", "new round", list(self.associations.keys())[index]]))
                                self.messages.pop(sock)
                                self.waiting_for_next_round = 0
                                self.used_words = []
                                return ["game", "chat", "new round", list(self.associations.keys())[index]]

    def broadcast_message(self):
        '''
        The function executes when a player sends a message in the chat
        The function sends the message to each player in the chat except the player who sent the message
        '''
        messages_to_remove = []
        for sender_socket in self.chat_messages:            
            for chat_member_socket in self.chat_players:
                if sender_socket is chat_member_socket:
                    pass
                else:
                    chat_member_socket.send(self.message.encode_json(self.chat_messages[sender_socket]))
            messages_to_remove.append(sender_socket)
        
        for sender_socket in messages_to_remove:
            self.chat_messages.pop(sender_socket, None)


if __name__ == "__main__":
    server = Server(SERVER_IP, SERVER_PORT)
    server.start()
    