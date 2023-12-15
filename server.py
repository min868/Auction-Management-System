import socket
import threading
import signal
import sys
import json
import time
from cryptography.fernet import Fernet

# socket connection
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = '127.0.0.1'
port = 12345
server_socket.bind((host, port))
server_socket.listen()
print("Server is waiting for connections...")

# CONSTANT FILE PATHS AND CURRENT_USER
USERS_FILE = "./database/users.txt"
AUCTIONS_FILE = "./database/auctions.txt"
BIDS_FILE = "./database/bids.txt"

custom_key = b'WYqcUk6g3TGalejnuQ3_39Q77R2CXhSLlwbJ-mldx6E='
cipher_suite = Fernet(custom_key)


def send_encrypted_message(client_socket, message):
    encrypted_message = cipher_suite.encrypt(message.encode())
    client_socket.sendall(encrypted_message)


def receive_decrypted_message(client_socket):
    try:
        encrypted_message = client_socket.recv(1024)
        decrypted_message = cipher_suite.decrypt(encrypted_message).decode()
        return decrypted_message
    except Exception as e:
        print(f"Error decrypting message: {e}")
        return None


def save_data(data: dict, file_path: str):
    """Function to save data to files"""
    with open(file_path, "w", encoding='utf-8') as file:
        json.dump(data, file, indent=4)


def load_data(file_path: str):
    """Function to load data from files"""
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def user_action(client_socket, action, data):
    """Function to handle user actions (register or login)"""
    if action == 'register':
        register_user(client_socket, data)
    elif action == 'login':
        login_user(client_socket, data)


def handle_client(client_socket, address):
    print(f"Connected to {address}")

    try:
        send_encrypted_message(client_socket, "Connected to the server!")

        while True:
            data = receive_decrypted_message(client_socket).strip()
            if not data:
                break
            action, json_str = data.split('|')
            

            if action in ['register', 'login']:
                user_data = json.loads(json_str)
                user_action(client_socket, action, user_data)
            elif action == 'user_check':
                user_data = json.loads(json_str)
                send_encrypted_message(client_socket, user_checker(user_data))
            elif action == 'mail_check':
                user_data = json.loads(json_str)
                send_encrypted_message(client_socket, mail_checker(user_data))
            elif action == 'title_check':
                user_data = json.loads(json_str)
                send_encrypted_message(client_socket,auction_title_check(user_data))
            elif action == 'create_auction':
                auction_data = json.loads(json_str)
                auction_creator(client_socket, auction_data)
            elif action == 'bid_auction':
                bid_data = json.loads(json_str)
                bidder(client_socket, bid_data)
            elif action == 'show_auction':
                auction_status(client_socket)

    except Exception as e:
        print(f"Error handling client: {e}")

    finally:
        client_socket.close()
        print(f"Connection with {address} closed.")


def register_user(client_socket, user_data):
    users = load_data(USERS_FILE)
    users.append(user_data)
    save_data(users, USERS_FILE)
    response = "Registration Success!\nYou're good to go!"
    send_encrypted_message(client_socket, response)



def user_checker(name):
    users = load_data(USERS_FILE)
    if name in [user['username'] for user in users]:
        return "exists"
    return 'None'


def mail_checker(mail):
    users = load_data(USERS_FILE)
    if mail in [user['email'] for user in users]:
        return "exists"
    return 'None'


def login_user(client_socket, user):
    users = load_data(USERS_FILE)
    matching_users = [data for data in users if data['email'] == user['email'] and data['password'] == user['password']]

    if matching_users:
        matched_user = matching_users[0]
        response = f"Welcome back, {matched_user['username']}!"
        USER_DATA = {'username': matched_user['username'], 'money': matched_user['money']}
    else:
        response = "Invalid username or password. Please try again."
        USER_DATA = {}

    # Send the response to the client
    send_encrypted_message(client_socket, response)

    # Send USER_DATA to the client
    send_data = json.dumps(USER_DATA)
    send_encrypted_message(client_socket, send_data)

def auction_title_check(user_data):
    auctions = load_data(AUCTIONS_FILE)
    if user_data in [auction['title'] for auction in auctions]:
        return "exists"
    return "None"

def auction_creator(client_socket, auction_data):
    auctions = load_data(AUCTIONS_FILE)
    auctions.append(auction_data)
    save_data(auctions, AUCTIONS_FILE)
    response = "Auction created successfully!"
    send_encrypted_message(client_socket, response)


def bidder(client_socket, bid_data):
    users = load_data(USERS_FILE)
    auctions = load_data(AUCTIONS_FILE)
    bids = load_data(BIDS_FILE)

    try:
        user_index = next(index for index, user in enumerate(users) if user.get('username') == bid_data['username'])
    except StopIteration:
        msg = f"No user found with the username: {bid_data['username']}"
        encoded_msg = msg.encode()
        send_encrypted_message(client_socket, encoded_msg)
        return

    matching_auctions = [auction for auction in auctions if auction['title'] == bid_data['title']]

    if matching_auctions:
        auction = matching_auctions[0]
        end_time = time.strptime(auction['end_time'], "%Y-%m-%d %H:%M")
        current_time = time.gmtime()

        if current_time > end_time:
            response = "Bidding for this auction has ended."
            en_rsp = response.encode()
            send_encrypted_message(client_socket, en_rsp)
            return

        if bid_data['bid_amount'] > auction['highest_bid']:
            auction['highest_bidder'] = bid_data['username']
            auction['highest_bid'] = bid_data['bid_amount']

            users[user_index]['money'] -= bid_data['bid_amount']
            msg = f'Bid successful! You are now the highest bidder.'
        else:
            msg = f'Your bid amount is not higher than the current highest bid.'
    else:
        msg = f"No auction found with the title: {bid_data['title']}"

    send_encrypted_message(client_socket, msg)

    # Save the updated data to files
    save_data(auctions, AUCTIONS_FILE)
    save_data(bids, BIDS_FILE)
    save_data(users, USERS_FILE)


def auction_status(client_socket):
    """Function to display auction status"""
    auctions = load_data(AUCTIONS_FILE)
    response = json.dumps(auctions)
    send_encrypted_message(client_socket,response)



def signal_handler(sig, frame):
    print("\nStopping the server...")
    server_socket.close()
    sys.exit(0)


# Register the signal handler for a keyboard interrupt (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

while True:
    try:
        client_socket, client_address = server_socket.accept()

        # Create a new thread to handle the client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Stopping the server...")
        server_socket.close()
        sys.exit(0)
