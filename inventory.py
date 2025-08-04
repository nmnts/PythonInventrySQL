import json
import os

INVENTORY_FILE = 'inventory.json'
USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'user': {'password': 'user123', 'role': 'user'}
}

def load_inventory():
    if not os.path.exists(INVENTORY_FILE):
        return []
    with open(INVENTORY_FILE, 'r') as f:
        return json.load(f)

def save_inventory(inventory):
    with open(INVENTORY_FILE, 'w') as f:
        json.dump(inventory, f, indent=2)

def authenticate():
    print('--- Login ---')
    username = input('Username: ')
    password = input('Password: ')
    user = USERS.get(username)
    if user and user['password'] == password:
        print(f'Logged in as {username} ({user["role"]})')
        return user['role']
    else:
        print('Invalid credentials!')
        return None

def list_items(inventory):
    print('\n--- Inventory List ---')
    if not inventory:
        print('No items in inventory.')
        return
    for idx, item in enumerate(inventory, 1):
        print(f"{idx}. Name: {item['name']}, Quantity: {item['quantity']}, Price: {item['price']}")

def add_item(inventory):
    print('\n--- Add Item ---')
    name = input('Item name: ')
    quantity = int(input('Quantity: '))
    price = float(input('Price: '))
    inventory.append({'name': name, 'quantity': quantity, 'price': price})
    save_inventory(inventory)
    print('Item added!')

def edit_item(inventory):
    list_items(inventory)
    idx = int(input('Enter item number to edit: ')) - 1
    if 0 <= idx < len(inventory):
        print('Leave blank to keep current value.')
        name = input(f"New name ({inventory[idx]['name']}): ") or inventory[idx]['name']
        quantity = input(f"New quantity ({inventory[idx]['quantity']}): ")
        price = input(f"New price ({inventory[idx]['price']}): ")
        inventory[idx]['name'] = name
        if quantity:
            inventory[idx]['quantity'] = int(quantity)
        if price:
            inventory[idx]['price'] = float(price)
        save_inventory(inventory)
        print('Item updated!')
    else:
        print('Invalid item number.')

def delete_item(inventory):
    list_items(inventory)
    idx = int(input('Enter item number to delete: ')) - 1
    if 0 <= idx < len(inventory):
        removed = inventory.pop(idx)
        save_inventory(inventory)
        print(f"Deleted item: {removed['name']}")
    else:
        print('Invalid item number.')

def main():
    role = None
    while not role:
        role = authenticate()
    inventory = load_inventory()
    while True:
        print('\n--- Menu ---')
        print('1. List items')
        print('2. Add item')
        print('3. Edit item')
        if role == 'admin':
            print('4. Delete item')
            print('5. Exit')
        else:
            print('4. Exit')
        choice = input('Choose an option: ')
        if choice == '1':
            list_items(inventory)
        elif choice == '2':
            if role == 'admin':
                add_item(inventory)
            else:
                print('Only admin can add items.')
        elif choice == '3':
            edit_item(inventory)
        elif choice == '4':
            if role == 'admin':
                delete_item(inventory)
            else:
                print('Goodbye!')
                break
        elif choice == '5' and role == 'admin':
            print('Goodbye!')
            break
        else:
            print('Invalid choice.')

if __name__ == '__main__':
    main() 