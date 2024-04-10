import sqlite3
import json
import random
import pickle
# Encryption
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

class UsersDB:

    def __init__(self):
        self.database = 'users.db'
        self.encryption = Encryption()

    def connect_to_db(self):
        conn = sqlite3.connect(self.database)
        return conn

    def create_table(self):
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY NOT NULL, 
                password TEXT NOT NULL,
                remember_me INTEGER,
                mac_address TEXT
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()

    def insert_user(self, username, password, remember_me, mac_address):
        mac_address2 = (mac_address)
        remember_me = int(remember_me)
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO users (username, password, remember_me, mac_address) VALUES (?, ?, ?, ?)''', (username, json.dumps(password), int(remember_me), mac_address2))
        conn.commit()
        cursor.close()
        conn.close()

    def check_user_registered(self, username):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM users WHERE username=(?)''', (username,))
        result = cursor.fetchone() is not None
        conn.commit()
        cursor.close()
        conn.close()
        return result
        # returns true or false

    """def update_username(self, new_username, old_username):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET username=(?) WHERE username=(?)''', (new_username, old_username))
        conn.commit()
        cursor.close()
        conn.close()
"""
    
    def try_login(self, username, password_data):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT password FROM users WHERE username=(?)''', (username,))
        result = json.loads(json.loads(cursor.fetchone()[0]))
        encrypted_password = password_data[0]
        salt = password_data[1]
        nonce = password_data[2]
        tag = password_data[3]
        decrypted_entered_password = self.encryption.decrypt(eval(encrypted_password), eval(salt), eval(nonce), eval(tag))  # Decrypt the provided password
        decrypted_stored_password = self.encryption.decrypt(eval(result[0]), eval(result[1]), eval(result[2]), eval(result[3]))  # Retrieve the stored encrypted password
        if decrypted_entered_password == decrypted_stored_password:            
            login_result = True
        else:
            login_result = False
        cursor.close()
        conn.close()
        return login_result
    
    def check_remember_me(self, username):
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT remember_me FROM users WHERE username=(?)''', (username,))
        result = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return result

    def remember_me_on(self, mac_address, username):
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET remember_me=(?), mac_address=(?) WHERE username=(?)''', (True, mac_address, username))
        cursor.close()
        conn.commit()
        conn.close()

    def remember_me_off(self, username):
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET remember_me=(?), mac_address=(?) WHERE username=(?)''', (False, "", username))
        cursor.close()
        conn.commit()
        conn.close()

    def check_mac_address(self, mac_address):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM users WHERE mac_address=(?)''', (mac_address,))
        result = cursor.fetchall() != []
        cursor.close()
        conn.close()
        return result

    def update_other_users_mac_address(self, mac_address):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM users WHERE mac_address=(?)''', (mac_address,))
        result = cursor.fetchone()
        if result:
            cursor.execute('''UPDATE users SET mac_address=(?), remember_me=(?)''', ("", False))
            conn.commit()
        cursor.close()
        conn.close()

    def get_username_by_mac(self, mac_address):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT username FROM users WHERE mac_address=(?)''', (mac_address,))
        result = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return result

class ScoresDB:
    def __init__(self):
        self.database = 'scores.db'
        self.score_coefficient = 0.8

    def connect_to_db(self):
        conn = sqlite3.connect(self.database)
        return conn

    def create_table(self):
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                username TEXT, 
                game TEXT,
                lastScore INTEGER,
                mean INTEGER,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()

    def insert_score(self, username, game, score):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        if self.checkUserExists(username):
            mean = int((self.getMean(username)*self.score_coefficient) + (score*(1-self.score_coefficient)))
            cursor.execute('''UPDATE scores SET lastScore=(?), mean=(?) WHERE username=(?) AND game=(?)''', (score, mean, username, game))
        else:
            mean = score
            cursor.execute('''INSERT INTO scores (username, game, lastScore, mean) VALUES (?, ?, ?, ?)''', (username, game, score, mean))
        conn.commit()
        cursor.close()
        conn.close()

    def checkUserExists(self, username):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM scores WHERE username=(?)''', (username,))
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return not result == []

    def getMean(self, username):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT mean FROM scores WHERE username=(?) AND game=(?)''', (username, "sorting numbers"))
        mean = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        if mean:
            return mean
        return 0

    def get_last_score(self, username):
        self.create_table()
        conn = self.connect_to_db()
        cursor = conn.cursor()
        cursor.execute('''SELECT lastScore FROM scores WHERE username=(?) AND game=(?)''', (username, "sorting numbers"))
        lastScore = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        if lastScore:
            return lastScore
        return 0

class Message:

    def __init__(self):
        self.username = ''
        self.password = ''
        self.database = UsersDB()
    
    def decode_json(self, data):
        # gets data of bytes type
        # returns the data as a the list type
        try:
            decoded_data = data.decode()
            if decoded_data:
                return json.loads(decoded_data)
            else:
                # Handle the case when the decoded data is empty
                return None
        except json.decoder.JSONDecodeError as e:
            # Handle the invalid JSON case
            print(f"Error decoding JSON: {e}")
            return None
        
    def encode_json(self, data):
        # gets data of list type
        # returns the data as a bytes type
        try:
            json_data = json.dumps(data)
            return json_data.encode()
        except json.decoder.JSONDecodeError as e:
            # Handle the invalid JSON case
            print(f"Error decoding JSON: {e}")
            return None
        
class Sorting_Numbers:
    def __init__(self):
        self.numbers_to_sort = []
    
    def generate_numbers(self):
        numbers_to_sort = random.sample(range(1, 10), 5)
        random.shuffle(numbers_to_sort)
        self.numbers_to_sort = numbers_to_sort
        return numbers_to_sort

class Encryption:
    def __init__(self, key=None):
        self.password_key = b"password"
    
    def decrypt(self, encrypted_password, salt, nonce, tag):
        print("TRYING TO DECRYPT")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(self.password_key)
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_password = decryptor.update(encrypted_password) + decryptor.finalize()
        return decrypted_password

    