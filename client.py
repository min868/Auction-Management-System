import sys
import time
from getpass import getpass
import json
import re
import socket
from cryptography.fernet import Fernet

# Constants
HOST = '127.0.0.1'
PORT = 12345
USER = None

# Socket connection
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

custom_key = b'WYqcUk6g3TGalejnuQ3_39Q77R2CXhSLlwbJ-mldx6E='
cipher_suite = Fernet(custom_key)


def send_encrypted_message(client_socket, action, data=None):
    """Send a message to the server."""
    if data is not None:
        json_str = json.dumps(data)
        message = f"{action}|{json_str}"
    else:
        message = f"{action}|None"

    encrypted_message = cipher_suite.encrypt(message.encode())
    client_socket.sendall(encrypted_message)


def receive_decrypted_message(client_socket):
    try:
        encrypted_message = client_socket.recv(1024)
        if encrypted_message:
            decrypted_message = cipher_suite.decrypt(encrypted_message).decode()
            return decrypted_message
        else:
            print("Error: Empty message received.")
            return None
    except Exception as e:
        print(f"Error decrypting message: {e}")
        return None



def connect_to_server():
    try:
        client_socket.connect((HOST, PORT))
        print(receive_decrypted_message(client_socket))
    except ConnectionRefusedError:
        print("Error: Connection to the server failed. Make sure the server is running.")
        sys.exit(1)


def register():
    """USER REGISTRATION FUNCTION"""
    attempts = 0
    max_attempts = 4

    while attempts < max_attempts:
        fullname = input("Your Fullname >>> ")
        if not fullname.strip():
            print("Name can't be empty!")
            attempts += 1
            continue
        break

    while attempts < max_attempts:
        username = input("Public Username >>> ")
        if not username.strip():
            print("Username can't be empty!")
            attempts += 1
            continue
        else:
            send_encrypted_message(client_socket, 'user_check', username)
            if receive_decrypted_message(client_socket) == 'exists':
                print('Username is already taken. Choose another one, please!')
                continue
            break

    while attempts < max_attempts:
        password = getpass("Password >>> ")
        if not password.strip():
            attempts += 1
            print("Password can't be empty.")
            continue
        break

    while attempts < max_attempts:
        email = input("Email >>> ")
        if re.match(r'\S+@\S+\.\S+', email):
            send_encrypted_message(client_socket, 'mail_check', email)
            if receive_decrypted_message(client_socket) == 'exists':
                print("Email is already registered!")
                continue
            break
        attempts += 1
        print("Invalid email format. Please enter a valid email address.")

    user_data = {
        'fullname': fullname,
        'username': username,
        'password': password,
        'email': email,
        'money': 1_000_000
    }
    send_encrypted_message(client_socket, 'register', user_data)

    # Receive and print the response from the server
    response = receive_decrypted_message(client_socket)
    print(response)
    if response == "Registration Success!\nYou're good to go!":
        global USER
        USER = {'username': username, 'money': 1_000_000}
        auction_app()

def login():
    """USER LOGIN FUNCTION"""
    email = input("Email --> ")
    password = getpass("Password --> ")
    login_info = {'email': email, 'password': password}
    send_encrypted_message(client_socket, 'login', login_info)

    response = receive_decrypted_message(client_socket)
    
    if response is None:
        print("Error: Unable to receive a valid response from the server.")
        return

    print(response)
    
    response = receive_decrypted_message(client_socket)
    global USER
    USER = json.loads(response) if response != 'None' else None

    if USER:
        auction_app()



def auction_app():
    """USER AUCTION APP"""

    def auction_creation():
        while True:
            title = input("Enter the title of the auction: ")
            send_encrypted_message(client_socket, 'title_check', title)
            if receive_decrypted_message(client_socket) == 'exists':
                    print("Auctions is already registered!")
                    continue
            break

        description = input("Enter the description of the auction: ")
        end_time = input("Enter the auction end time (format: YYYY-MM-DD HH:MM)")

        auction_data = {
            'title': title,
            'description': description,
            'end_time': end_time,
            'highest_bid': 0,
            'highest_bidder': None,
            'created_by': USER['username']
        }
        send_encrypted_message(client_socket, 'create_auction', auction_data)
        response = receive_decrypted_message(client_socket)
        print(response)

    def bidding():
        auction_status()
        bid_title = input("Enter the title of the auction you want to bid on: ")
        bid_amount = float(input("Enter your bid amount: "))
        bid_data = {"title": bid_title, "username": USER['username'], "bid_amount": bid_amount}
        send_encrypted_message(client_socket, 'bid_auction', bid_data)
        response = receive_decrypted_message(client_socket)
        print(response)

    def auction_status():
        send_encrypted_message(client_socket, 'show_auction', 'None')
        response = receive_decrypted_message(client_socket)
        auctions = json.loads(response)

        print("\nAuction Status:")
        print("--------------------------------------------------------------------------------")
        print("|       Title        |  Highest Bid |     Time Remaining     | Highest Bidder  |")
        print("--------------------------------------------------------------------------------")

        for auction in auctions:
            end_time = time.strptime(auction['end_time'], "%Y-%m-%d %H:%M")
            current_time = time.gmtime()

            time_remaining = max(0, int(time.mktime(end_time) - time.mktime(current_time)))

            if auction['highest_bidder'] is not None:
                highest_bidder_display = auction['highest_bidder'][:15]
            else:
                highest_bidder_display = "None"

            print(
                f"| {auction['title'][:18]:18} | {auction['highest_bid']:12.2f} | {time_remaining:14} seconds | {highest_bidder_display:15} |")

        print("--------------------------------------------------------------------------------")

    while True:
        try:
            action = int(input("1 >>> Create Auction\n2 >>> Place Bid \n3 >>> Display Auction Status \n4 >>> Main Menu --> "))
            if action == 1:
                auction_creation()
            elif action == 2:
                bidding()
            elif action == 3:
                auction_status()
            elif action == 4:
                break
        except ValueError:
            print("Choose a valid option!")


def main_menu():
    """Main menu"""
    while True:
        print("\nAuction Management System")
        print("1. Register")
        print("2. Login")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            register()
        elif choice == "2":
            login()
        elif choice == "3":
            client_socket.close()
            break
        else:
            print("\nInvalid choice. Please try again.")


# Run the program
if __name__ == "__main__":
    connect_to_server()
main_menu()
