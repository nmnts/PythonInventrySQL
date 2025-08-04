import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
import json
import os
import datetime
import re
import calendar
import pandas as pd
import sqlite3
import sys

# Ensure config folder and users.json exist
CONFIG_DIR = 'config'
USERS_FILE = os.path.join(CONFIG_DIR, 'users.json')
DEFAULT_USERS = [
    {'id': 1, 'username': 'admin', 'password': 'admin123', 'role': 'admin'},
    {'id': 2, 'username': 'user', 'password': 'user123', 'role': 'user'}
]
if getattr(sys, 'frozen', False):
    # Running as a bundled exe
    os.chdir(os.path.dirname(sys.executable))
else:
    # Running as script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump(DEFAULT_USERS, f, indent=2)

INVENTORY_FILE = os.path.join(CONFIG_DIR, 'inventory.json')
SELL_HISTORY_FILE = os.path.join(CONFIG_DIR, 'sell_history.json')
LOCALDB_FILE = os.path.join(CONFIG_DIR, 'localdb.sqlite')

# --- MIGRATION: Ensure cost_price column exists in sell_history before any DB access ---
if os.path.exists(LOCALDB_FILE):
    conn = sqlite3.connect(LOCALDB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(sell_history)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'cost_price' not in columns:
        cursor.execute("ALTER TABLE sell_history ADD COLUMN cost_price REAL DEFAULT 0")
        conn.commit()
    conn.close()

def initialize_database():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(LOCALDB_FILE):
        conn = sqlite3.connect(LOCALDB_FILE)
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        ''')
        # Insert default users if table is empty
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            for user in DEFAULT_USERS:
                cursor.execute('INSERT INTO users (id, username, password, role) VALUES (?, ?, ?, ?)',
                               (user['id'], user['username'], user['password'], user['role']))
        # Create inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                quantity INTEGER,
                price REAL,
                barcode TEXT,
                cost_price REAL DEFAULT 0
            )
        ''')
        # Create sell_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sell_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                quantity_sold INTEGER,
                price REAL,
                total_sale REAL,
                discount REAL,
                discount_percent REAL,
                discount_price REAL,
                final_total REAL,
                timestamp TEXT,
                customer_name TEXT,
                contact_number TEXT,
                cost_price REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

def load_users():
    if not os.path.exists(LOCALDB_FILE):
        return []
    conn = sqlite3.connect(LOCALDB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password, role FROM users')
    users = [
        {'id': row[0], 'username': row[1], 'password': row[2], 'role': row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return users

def save_users(users):
    # This function should be refactored to update the SQLite DB if needed
    pass

def get_next_user_id(users):
    if not users:
        return 1
    return max(u['id'] for u in users) + 1

def find_user_by_username(users, username):
    for u in users:
        if u['username'] == username:
            return u
    return None

def find_user_by_id(users, user_id):
    for u in users:
        if u['id'] == user_id:
            return u
    return None

def load_inventory():
    if not os.path.exists(LOCALDB_FILE):
        return []
    conn = sqlite3.connect(LOCALDB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, quantity, price, barcode, cost_price FROM inventory')
    inventory = [
        {'id': row[0], 'name': row[1], 'quantity': row[2], 'price': row[3], 'barcode': row[4], 'cost_price': row[5]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return inventory

def save_inventory(inventory):
    # This function should be refactored to update the SQLite DB if needed
    pass

def load_sell_history():
    if not os.path.exists(LOCALDB_FILE):
        return []
    conn = sqlite3.connect(LOCALDB_FILE)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, name, quantity_sold, price, total_sale, discount, discount_percent, discount_price, final_total, timestamp, customer_name, contact_number, cost_price FROM sell_history''')
    history = [
        {
            'id': row[0],
            'name': row[1],
            'quantity_sold': row[2],
            'price': row[3],
            'total_sale': row[4],
            'discount': row[5],
            'discount_percent': row[6],
            'discount_price': row[7],
            'final_total': row[8],
            'timestamp': row[9],
            'customer_name': row[10],
            'contact_number': row[11],
            'cost_price': row[12]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return history

def save_sell_history(history):
    with open(SELL_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def get_customer_name_by_contact(contact_number):
    history = load_sell_history()
    # Find the most recent entry for this contact number
    for entry in reversed(history):
        if isinstance(entry, dict) and entry.get('contact_number', '') == contact_number:
            return entry.get('customer_name', '')
    return ''

class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Cloth Inventory')
        self.root.geometry('500x450')
        self.root.configure(bg='#f0f4f8')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f0f4f8')
        style.configure('TLabel', background='#f0f4f8', font=('Segoe UI', 12))
        style.configure('TButton', font=('Segoe UI', 12), padding=6)
        style.configure('TEntry', font=('Segoe UI', 12), padding=6)
        style.configure('Inventory.TFrame', background='#ffffff', relief='groove', borderwidth=2)
        style.configure('Inventory.TLabel', background='#ffffff', font=('Segoe UI', 12))
        style.configure('Inventory.TButton', font=('Segoe UI', 12), padding=6)
        self.role = None
        self.inventory = load_inventory()
        self.users = load_users()
        self.login_screen()

    def login_screen(self):
        self.clear()
        self.root.configure(bg='#f0f4f8')
        frame = ttk.Frame(self.root, style='Inventory.TFrame')
        frame.pack(pady=60, padx=60)
        title = ttk.Label(frame, text='Login', font=('Segoe UI', 18, 'bold'), style='Inventory.TLabel', foreground='#333')
        title.grid(row=0, column=0, columnspan=2, pady=(10, 20))
        ttk.Label(frame, text='Username:', style='Inventory.TLabel').grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.username_entry = ttk.Entry(frame, width=20, style='TEntry')
        self.username_entry.grid(row=1, column=1, pady=5, padx=5)
        ttk.Label(frame, text='Password:', style='Inventory.TLabel').grid(row=2, column=0, sticky='e', pady=5, padx=5)
        self.password_entry = ttk.Entry(frame, show='*', width=20, style='TEntry')
        self.password_entry.grid(row=2, column=1, pady=5, padx=5)
        login_btn = ttk.Button(frame, text='Login', command=self.authenticate, style='Inventory.TButton')
        login_btn.grid(row=3, column=0, columnspan=2, pady=(20, 10))
        self.username_entry.focus()

    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user = find_user_by_username(self.users, username)
        if user and user['password'] == password:
            self.role = user['role']
            self.current_user_id = user['id']
            self.main_screen()
        else:
            messagebox.showerror('Error', 'Invalid credentials!')

    def main_screen(self):
        self.clear()
        self.root.configure(bg='#f0f4f8')
        # Remove any existing menu
        if hasattr(self, 'menu') and self.menu:
            self.root.config(menu=None)
        self.menu = tk.Menu(self.root)
        # File menu
        file_menu = tk.Menu(self.menu, tearoff=0)
        if self.role == 'admin':
            file_menu.add_command(label='Add Item', command=self.add_item)
            file_menu.add_command(label='Edit Item', command=self.edit_item)
            file_menu.add_command(label='Delete Item', command=self.delete_item)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.root.quit)
        self.menu.add_cascade(label='File', menu=file_menu)
        # Inventory menu
        inventory_menu = tk.Menu(self.menu, tearoff=0)
        inventory_menu.add_command(label='View Stock', command=self.view_stock)
        inventory_menu.add_command(label='Sell Item', command=self.sell_item)
        inventory_menu.add_command(label='Sell History', command=self.view_history)
        inventory_menu.add_command(label='Profit/Loss Report', command=self.profit_loss_report)
        self.menu.add_cascade(label='Inventory', menu=inventory_menu)
        # Users menu (admin only)
        if self.role == 'admin':
            users_menu = tk.Menu(self.menu, tearoff=0)
            users_menu.add_command(label='Add User', command=self.add_user)
            users_menu.add_command(label='Manage Users', command=self.manage_users)
            # Customers menu
            customers_menu = tk.Menu(self.menu, tearoff=0)
            customers_menu.add_command(label='Customer List', command=self.customer_list)
            self.menu.add_cascade(label='Customers', menu=customers_menu)
            self.menu.add_cascade(label='Users', menu=users_menu)
        # Session menu
        session_menu = tk.Menu(self.menu, tearoff=0)
        session_menu.add_command(label='Logout', command=self.login_screen)
        self.menu.add_cascade(label='Session', menu=session_menu)
        self.root.config(menu=self.menu)
        frame = ttk.Frame(self.root, style='Inventory.TFrame')
        frame.pack(pady=30, padx=30, fill='both', expand=True)
        ttk.Label(frame, text=f'Logged in as {self.role}', style='Inventory.TLabel', font=('Segoe UI', 12, 'italic')).pack(pady=(10, 0))
        # Search bar
        search_frame = ttk.Frame(frame, style='Inventory.TFrame')
        search_frame.pack(pady=(5, 0), padx=10, fill='x')
        ttk.Label(search_frame, text='Search:', style='Inventory.TLabel').pack(side='left')
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30, style='TEntry')
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', self.on_search)
        # Table
        table_frame = ttk.Frame(frame, style='Inventory.TFrame')
        table_frame.pack(pady=10, padx=10, fill='both', expand=True)
        columns = ('ID', 'Name', 'Quantity', 'Price', 'Total Price', 'Cost Price')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        self.tree.heading('ID', text='ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Price', text='Price')
        self.tree.heading('Total Price', text='Total Price')
        self.tree.heading('Cost Price', text='Cost Price')
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('Name', width=150, anchor='center')
        self.tree.column('Quantity', width=80, anchor='center')
        self.tree.column('Price', width=80, anchor='center')
        self.tree.column('Total Price', width=100, anchor='center')
        self.tree.column('Cost Price', width=100, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.refresh_list()
        # Grand total label
        self.grand_total_var = tk.StringVar()
        grand_total_label = ttk.Label(frame, textvariable=self.grand_total_var, font=('Segoe UI', 12, 'bold'), foreground='#333', background='#f0f4f8')
        grand_total_label.pack(side='bottom', pady=5)
        self.update_grand_total()
        # Creator label at the bottom
        creator_label = ttk.Label(self.root, text='Created by: Namneet Singh | Contact: 8437379895', font=('Segoe UI', 10, 'italic'), background='#f0f4f8', foreground='#555')
        creator_label.pack(side='bottom', pady=2)

    def on_search(self, event=None):
        query = self.search_var.get().strip().lower()
        if not query:
            filtered = self.inventory
        else:
            filtered = [item for item in self.inventory if query in item['name'].lower()]
        if hasattr(self, 'tree'):
            for row in self.tree.get_children():
                self.tree.delete(row)
            for idx, item in enumerate(filtered, 1):
                total_price = item['quantity'] * item['price']
                self.tree.insert('', 'end', values=(idx, item['name'], item['quantity'], item['price'], total_price, item.get('cost_price', 0)))
        self.update_grand_total()

    def refresh_list(self):
        self.inventory = load_inventory()
        if hasattr(self, 'tree'):
            for row in self.tree.get_children():
                self.tree.delete(row)
            for idx, item in enumerate(self.inventory, 1):
                total_price = item['quantity'] * item['price']
                self.tree.insert('', 'end', values=(idx, item['name'], item['quantity'], item['price'], total_price, item.get('cost_price', 0)))
        self.update_grand_total()

    def update_grand_total(self):
        if hasattr(self, 'inventory'):
            grand_total = sum(item['quantity'] * item['price'] for item in self.inventory)
            if hasattr(self, 'grand_total_var'):
                self.grand_total_var.set(f'Grand Total: {grand_total}')

    def add_item(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Add Item')
        dialog.configure(bg='#f0f4f8')
        ttk.Label(dialog, text='Item name:', style='Inventory.TLabel').grid(row=0, column=0, pady=8, padx=8, sticky='e')
        name_entry = ttk.Entry(dialog, width=25, style='TEntry')
        name_entry.grid(row=0, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Quantity:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
        quantity_entry = ttk.Entry(dialog, width=25, style='TEntry')
        quantity_entry.grid(row=1, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Price:', style='Inventory.TLabel').grid(row=2, column=0, pady=8, padx=8, sticky='e')
        price_entry = ttk.Entry(dialog, width=25, style='TEntry')
        price_entry.grid(row=2, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Cost Price:', style='Inventory.TLabel').grid(row=3, column=0, pady=8, padx=8, sticky='e')
        cost_price_entry = ttk.Entry(dialog, width=25, style='TEntry')
        cost_price_entry.grid(row=3, column=1, pady=8, padx=8)
        def submit():
            name = name_entry.get()
            try:
                quantity = int(quantity_entry.get())
                price = float(price_entry.get())
                cost_price = float(cost_price_entry.get())
            except ValueError:
                messagebox.showerror('Error', 'Invalid quantity or price!')
                return
            if not name:
                messagebox.showerror('Error', 'Name cannot be empty!')
                return
            conn = sqlite3.connect(LOCALDB_FILE)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO inventory (name, quantity, price, barcode, cost_price) VALUES (?, ?, ?, ?, ?)',
                           (name, quantity, price, '', cost_price))
            conn.commit()
            conn.close()
            self.refresh_list()
            messagebox.showinfo('Success', 'Item added!')
            dialog.destroy()
        ttk.Button(dialog, text='Add', command=submit, style='Inventory.TButton').grid(row=4, column=0, columnspan=2, pady=12)
        dialog.grab_set()
        name_entry.focus()

    def edit_item(self):
        if not hasattr(self, 'tree'):
            return
        selection = self.tree.selection()
        if not selection:
            messagebox.showerror('Error', 'No item selected!')
            return
        item_values = self.tree.item(selection[0])['values']
        idx = int(item_values[0]) - 1
        item = self.inventory[idx]
        dialog = tk.Toplevel(self.root)
        dialog.title('Edit Item')
        dialog.configure(bg='#f0f4f8')
        ttk.Label(dialog, text='Item name:', style='Inventory.TLabel').grid(row=0, column=0, pady=8, padx=8, sticky='e')
        name_entry = ttk.Entry(dialog, width=25, style='TEntry')
        name_entry.insert(0, item['name'])
        name_entry.grid(row=0, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Quantity:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
        quantity_entry = ttk.Entry(dialog, width=25, style='TEntry')
        quantity_entry.insert(0, str(item['quantity']))
        quantity_entry.grid(row=1, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Price:', style='Inventory.TLabel').grid(row=2, column=0, pady=8, padx=8, sticky='e')
        price_entry = ttk.Entry(dialog, width=25, style='TEntry')
        price_entry.insert(0, str(item['price']))
        price_entry.grid(row=2, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Cost Price:', style='Inventory.TLabel').grid(row=3, column=0, pady=8, padx=8, sticky='e')
        cost_price_entry = ttk.Entry(dialog, width=25, style='TEntry')
        cost_price_entry.insert(0, str(item.get('cost_price', 0)))
        cost_price_entry.grid(row=3, column=1, pady=8, padx=8)
        def submit():
            name = name_entry.get()
            try:
                quantity = int(quantity_entry.get())
                price = float(price_entry.get())
                cost_price = float(cost_price_entry.get())
            except ValueError:
                messagebox.showerror('Error', 'Invalid quantity or price!')
                return
            if not name:
                messagebox.showerror('Error', 'Name cannot be empty!')
                return
            conn = sqlite3.connect(LOCALDB_FILE)
            cursor = conn.cursor()
            cursor.execute('UPDATE inventory SET name=?, quantity=?, price=?, cost_price=? WHERE id=?',
                           (name, quantity, price, cost_price, item['id']))
            conn.commit()
            conn.close()
            self.refresh_list()
            messagebox.showinfo('Success', 'Item updated!')
            dialog.destroy()
        ttk.Button(dialog, text='Update', command=submit, style='Inventory.TButton').grid(row=4, column=0, columnspan=2, pady=12)
        dialog.grab_set()
        name_entry.focus()

    def delete_item(self):
        if not hasattr(self, 'tree'):
            return
        selection = self.tree.selection()
        if not selection:
            messagebox.showerror('Error', 'No item selected!')
            return
        item_values = self.tree.item(selection[0])['values']
        idx = int(item_values[0]) - 1
        item = self.inventory[idx]
        if messagebox.askyesno('Confirm', f"Delete item: {item['name']}?"):
            self.inventory.pop(idx)
            save_inventory(self.inventory)
            self.refresh_list()
            messagebox.showinfo('Success', 'Item deleted!')

    def sell_item(self):
        if not hasattr(self, 'tree'):
            return
        selection = self.tree.selection()
        idx = None
        item = None
        if selection:
            item_values = self.tree.item(selection[0])['values']
            idx = int(item_values[0]) - 1
            item = self.inventory[idx]
        sell_dialog = tk.Toplevel(self.root)
        sell_dialog.title('Sell Item')
        sell_dialog.configure(bg='#f0f4f8')
        ttk.Label(sell_dialog, text='Select item to sell', style='Inventory.TLabel').grid(row=0, column=0, columnspan=2, pady=10, padx=10)
        ttk.Label(sell_dialog, text='Item name:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
        name_entry = ttk.Entry(sell_dialog, width=25, style='TEntry')
        name_entry.grid(row=1, column=1, pady=8, padx=8)
        ttk.Label(sell_dialog, text='Quantity to sell:', style='Inventory.TLabel').grid(row=2, column=0, pady=8, padx=8, sticky='e')
        qty_entry = ttk.Entry(sell_dialog, width=15, style='TEntry')
        qty_entry.grid(row=2, column=1, pady=8, padx=8)
        ttk.Label(sell_dialog, text='Price:', style='Inventory.TLabel').grid(row=3, column=0, pady=8, padx=8, sticky='e')
        price_entry = ttk.Entry(sell_dialog, width=25, style='TEntry')
        price_entry.grid(row=3, column=1, pady=8, padx=8)
        ttk.Label(sell_dialog, text='Customer Name:', style='Inventory.TLabel').grid(row=4, column=0, pady=8, padx=8, sticky='e')
        customer_name_entry = ttk.Entry(sell_dialog, width=25, style='TEntry')
        customer_name_entry.grid(row=4, column=1, pady=8, padx=8)
        ttk.Label(sell_dialog, text='Contact Number:', style='Inventory.TLabel').grid(row=5, column=0, pady=8, padx=8, sticky='e')
        contact_number_entry = ttk.Entry(sell_dialog, width=25, style='TEntry')
        contact_number_entry.grid(row=5, column=1, pady=8, padx=8)
        
        def autofill_customer_name(event=None):
            contact = contact_number_entry.get().strip()
            if contact and re.fullmatch(r'\d{10}', contact):
                name = get_customer_name_by_contact(contact)
                if name:
                    customer_name_entry.delete(0, tk.END)
                    customer_name_entry.insert(0, name)
        contact_number_entry.bind('<FocusOut>', autofill_customer_name)
        contact_number_entry.bind('<Return>', autofill_customer_name)

        ttk.Label(sell_dialog, text='Discount (%):', style='Inventory.TLabel').grid(row=6, column=0, pady=8, padx=8, sticky='e')
        discount_percent_entry = ttk.Entry(sell_dialog, width=25, style='TEntry')
        discount_percent_entry.insert(0, '0')
        discount_percent_entry.grid(row=6, column=1, pady=8, padx=8)
        qty_in_stock_label = ttk.Label(sell_dialog, text=f"In stock: {item['quantity']}" if item else '', style='Inventory.TLabel')
        qty_in_stock_label.grid(row=7, column=0, columnspan=2, pady=5)
        if item:
            name_entry.insert(0, item['name'])
            price_entry.insert(0, str(item['price']))
        def submit():
            name = name_entry.get()
            try:
                sell_qty = int(qty_entry.get())
                price = float(price_entry.get())
                discount_percent = float(discount_percent_entry.get())
            except ValueError:
                messagebox.showerror('Error', 'Invalid quantity or price!')
                return
            customer_name = customer_name_entry.get().strip()
            contact_number = contact_number_entry.get().strip()
            # Validation for customer name (alphabets and spaces only)
            if not customer_name:
                messagebox.showerror('Error', 'Customer name cannot be empty!')
                return
            if not re.fullmatch(r'[A-Za-z ]+', customer_name):
                messagebox.showerror('Error', 'Customer name must contain only alphabets and spaces!')
                return
            # Validation for contact number (10 digits only)
            if not contact_number:
                messagebox.showerror('Error', 'Contact number cannot be empty!')
                return
            if not re.fullmatch(r'\d{10}', contact_number):
                messagebox.showerror('Error', 'Contact number must be exactly 10 digits!')
                return
            # Find item by name
            matched_item = None
            for itm in self.inventory:
                if itm['name'] == name:
                    matched_item = itm
                    break
            if not matched_item:
                messagebox.showerror('Error', 'Item not found!')
                return
            if sell_qty <= 0:
                messagebox.showerror('Error', 'Quantity must be positive!')
                return
            if sell_qty > matched_item['quantity']:
                messagebox.showerror('Error', 'Not enough in stock!')
                return
            matched_item['quantity'] -= sell_qty
            # Update inventory in DB
            conn = sqlite3.connect(LOCALDB_FILE)
            cursor = conn.cursor()
            cursor.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (matched_item['quantity'], matched_item['id']))
            conn.commit()
            # Save to sell history in DB
            total_sale = sell_qty * price
            if discount_percent < 0 or discount_percent > 100:
                messagebox.showerror('Error', 'Discount percent must be between 0 and 100!')
                conn.close()
                return
            discount = (discount_percent / 100.0) * total_sale
            final_total = total_sale - discount
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''INSERT INTO sell_history (
                name, quantity_sold, price, total_sale, discount_percent, discount_price, final_total, timestamp, customer_name, contact_number, cost_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (matched_item['name'], sell_qty, price, total_sale, discount_percent, discount, final_total, now_str, customer_name, contact_number, matched_item.get('cost_price', 0)))
            conn.commit()
            conn.close()
            self.refresh_list()
            sell_dialog.destroy()
            self.show_bill(matched_item['name'], sell_qty, price, total_sale, discount_percent, discount, final_total, now_str, customer_name, contact_number)
        ttk.Button(sell_dialog, text='Sell', command=submit, style='Inventory.TButton').grid(row=8, column=0, columnspan=2, pady=12)
        sell_dialog.grab_set()
        name_entry.focus()

    def show_bill(self, name, quantity, price, total, discount_percent, discount, final_total, timestamp, customer_name, contact_number):
        bill_dialog = tk.Toplevel(self.root)
        bill_dialog.title('Print Bill')
        bill_dialog.configure(bg='#f0f4f8')
        bill_text = f"BILL\nDate/Time: {timestamp}\n-----------------------------\nCustomer Name: {customer_name}\nContact Number: {contact_number}\n-----------------------------\nItem: {name}\nQuantity: {quantity}\nPrice per item: {price}\nTotal: {total}\nDiscount: {discount_percent}%\nDiscount Price: {discount}\nFinal Total: {final_total}\n-----------------------------\nThank you for your purchase!"
        text_widget = tk.Text(bill_dialog, width=40, height=16, font=('Segoe UI', 12), bg='#f8fafc', bd=0)
        text_widget.insert('1.0', bill_text)
        text_widget.config(state='disabled')
        text_widget.pack(padx=10, pady=10)
        def print_bill_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import os
            except ImportError:
                messagebox.showerror('Missing Library', 'reportlab is required to save PDF. Please install it with:\npip install reportlab')
                return
            # Prepare billing folder structure: billing/<month_name>/<date>/
            bill_dt = None
            try:
                bill_dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except Exception:
                bill_dt = datetime.datetime.now()
            month_name = bill_dt.strftime('%B')
            date_str = bill_dt.strftime('%Y-%m-%d')
            billing_folder = os.path.join('billing', month_name, date_str)
            if not os.path.exists(billing_folder):
                os.makedirs(billing_folder)
            # Prepare file name with contact number and datetime
            safe_contact = str(contact_number).replace(' ', '').replace('/', '').replace('\\', '')
            safe_datetime = timestamp.replace(':', '').replace(' ', '_').replace('-', '')
            file_name = os.path.join(billing_folder, f"bill_{safe_contact}_{safe_datetime}.pdf")
            c = canvas.Canvas(file_name, pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont('Helvetica-Bold', 16)
            c.drawString(50, y, 'BILL')
            c.setFont('Helvetica', 12)
            y -= 30
            c.drawString(50, y, f'Date/Time: {timestamp}')
            y -= 20
            c.drawString(50, y, '-----------------------------')
            y -= 20
            c.drawString(50, y, f'Customer Name: {customer_name}')
            y -= 20
            c.drawString(50, y, f'Contact Number: {contact_number}')
            y -= 20
            c.drawString(50, y, '-----------------------------')
            y -= 20
            c.drawString(50, y, f'Item: {name}')
            y -= 20
            c.drawString(50, y, f'Quantity: {quantity}')
            y -= 20
            c.drawString(50, y, f'Price per item: {price}')
            y -= 20
            c.drawString(50, y, f'Total: {total}')
            y -= 20
            c.drawString(50, y, f'Discount: {discount_percent}%')
            y -= 20
            c.drawString(50, y, f'Discount Price: {discount}')
            y -= 20
            c.drawString(50, y, f'Final Total: {final_total}')
            y -= 20
            c.drawString(50, y, '-----------------------------')
            y -= 30
            c.drawString(50, y, 'Thank you for your purchase!')
            c.save()
            messagebox.showinfo('Bill Saved', f'Bill saved as {file_name}')
            bill_dialog.destroy()
        ttk.Button(bill_dialog, text='Print/Save Bill (PDF)', command=print_bill_pdf, style='Inventory.TButton').pack(pady=10)
        ttk.Button(bill_dialog, text='Close', command=bill_dialog.destroy, style='Inventory.TButton').pack(pady=5)
        bill_dialog.grab_set()

    def view_stock(self):
        stock_dialog = tk.Toplevel(self.root)
        stock_dialog.title('Current Stock')
        stock_dialog.configure(bg='#f0f4f8')
        columns = ('ID', 'Name', 'Quantity', 'Price', 'Total Price')
        tree = ttk.Treeview(stock_dialog, columns=columns, show='headings', height=10)
        tree.heading('ID', text='ID')
        tree.heading('Name', text='Name')
        tree.heading('Quantity', text='Quantity')
        tree.heading('Price', text='Price')
        tree.heading('Total Price', text='Total Price')
        tree.column('ID', width=50, anchor='center')
        tree.column('Name', width=150, anchor='center')
        tree.column('Quantity', width=80, anchor='center')
        tree.column('Price', width=80, anchor='center')
        tree.column('Total Price', width=100, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        for idx, item in enumerate(self.inventory, 1):
            total_price = item['quantity'] * item['price']
            tree.insert('', 'end', values=(idx, item['name'], item['quantity'], item['price'], total_price))
        scrollbar = ttk.Scrollbar(stock_dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        ttk.Button(stock_dialog, text='Close', command=stock_dialog.destroy, style='Inventory.TButton').pack(pady=10)
        stock_dialog.grab_set()

    def view_history(self):
        history = load_sell_history()
        history_dialog = tk.Toplevel(self.root)
        history_dialog.title('Sell History')
        history_dialog.configure(bg='#f0f4f8')
        columns = ('No.', 'Name', 'Quantity Sold', 'Price', 'Total Sale', 'Discount (%)', 'Discount Price', 'Final Total', 'Cost Price', 'Customer Name', 'Contact Number', 'Timestamp')
        # Frame for tree and scrollbars
        tree_frame = ttk.Frame(history_dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', stretch=True, width=120)
        # Scrollbars
        xscrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        yscrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(xscrollcommand=xscrollbar.set, yscrollcommand=yscrollbar.set)
        tree.grid(row=0, column=0, sticky='nsew')
        yscrollbar.grid(row=0, column=1, sticky='ns')
        xscrollbar.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        for idx, entry in enumerate(history, 1):
            if isinstance(entry, dict):
                tree.insert('', 'end', values=(
                    idx,
                    entry.get('name', ''),
                    entry.get('quantity_sold', ''),
                    entry.get('price', ''),
                    entry.get('total_sale', ''),
                    entry.get('discount_percent', 0),
                    entry.get('discount_price', 0),
                    entry.get('final_total', entry.get('total_sale', 0)),
                    entry.get('cost_price', 0),
                    entry.get('customer_name', ''),
                    entry.get('contact_number', ''),
                    entry.get('timestamp', '')
                ))
        btn_frame = ttk.Frame(history_dialog, style='Inventory.TFrame')
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text='Export as Excel', command=self.export_sell_history_excel, style='Inventory.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Close', command=history_dialog.destroy, style='Inventory.TButton').pack(side='left', padx=5)
        history_dialog.grab_set()

    def export_sell_history_excel(self):
        try:
            import pandas as pd
            import os
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror('Missing Library', 'pandas is required to export Excel. Please install it with:\npip install pandas openpyxl')
            return
        history = load_sell_history()
        if not history:
            from tkinter import messagebox
            messagebox.showinfo('No Data', 'No sell history to export.')
            return
        df = pd.DataFrame(history)
        reports_folder = 'reports'
        if not os.path.exists(reports_folder):
            os.makedirs(reports_folder)
        import datetime
        now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = os.path.join(reports_folder, f'sell_history_{now_str}.xlsx')
        try:
            df.to_excel(file_name, index=False)
            from tkinter import messagebox
            messagebox.showinfo('Exported', f'Sell history exported as {file_name}')
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror('Error', f'Failed to export Excel: {e}')

    def add_user(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Add User')
        dialog.configure(bg='#f0f4f8')
        ttk.Label(dialog, text='Username:', style='Inventory.TLabel').grid(row=0, column=0, pady=8, padx=8, sticky='e')
        username_entry = ttk.Entry(dialog, width=25, style='TEntry')
        username_entry.grid(row=0, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Password:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
        password_entry = ttk.Entry(dialog, width=25, style='TEntry', show='*')
        password_entry.grid(row=1, column=1, pady=8, padx=8)
        ttk.Label(dialog, text='Role:', style='Inventory.TLabel').grid(row=2, column=0, pady=8, padx=8, sticky='e')
        role_var = tk.StringVar(value='user')
        role_combo = ttk.Combobox(dialog, textvariable=role_var, values=['admin', 'user'], state='readonly', width=22)
        role_combo.grid(row=2, column=1, pady=8, padx=8)
        def submit():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            role = role_var.get()
            if not username or not password:
                messagebox.showerror('Error', 'Username and password cannot be empty!')
                return
            if find_user_by_username(self.users, username):
                messagebox.showerror('Error', 'Username already exists!')
                return
            new_id = get_next_user_id(self.users)
            self.users.append({'id': new_id, 'username': username, 'password': password, 'role': role})
            save_users(self.users)
            messagebox.showinfo('Success', f"User '{username}' added!")
            dialog.destroy()
        ttk.Button(dialog, text='Add User', command=submit, style='Inventory.TButton').grid(row=3, column=0, columnspan=2, pady=12)
        ttk.Button(dialog, text='Cancel', command=dialog.destroy, style='Inventory.TButton').grid(row=4, column=0, columnspan=2, pady=5)
        dialog.grab_set()
        username_entry.focus()

    def manage_users(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Manage Users')
        dialog.configure(bg='#f0f4f8')
        columns = ('ID', 'Username', 'Role')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
        tree.heading('ID', text='ID')
        tree.heading('Username', text='Username')
        tree.heading('Role', text='Role')
        tree.column('ID', width=50, anchor='center')
        tree.column('Username', width=120, anchor='center')
        tree.column('Role', width=80, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        for user in self.users:
            tree.insert('', 'end', values=(user['id'], user['username'], user['role']))
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        btn_frame = ttk.Frame(dialog, style='Inventory.TFrame')
        btn_frame.pack(pady=10)
        def edit_user():
            selection = tree.selection()
            if not selection:
                messagebox.showerror('Error', 'No user selected!')
                return
            user_id = int(tree.item(selection[0])['values'][0])
            user = find_user_by_id(self.users, user_id)
            if user is None:
                messagebox.showerror('Error', 'User not found!')
                return
            if user_id == getattr(self, 'current_user_id', None):
                messagebox.showerror('Error', 'You cannot edit yourself here.')
                return
            edit_dialog = tk.Toplevel(dialog)
            edit_dialog.title('Edit User')
            edit_dialog.configure(bg='#f0f4f8')
            ttk.Label(edit_dialog, text='ID:', style='Inventory.TLabel').grid(row=0, column=0, pady=8, padx=8, sticky='e')
            ttk.Label(edit_dialog, text=str(user['id']), style='Inventory.TLabel').grid(row=0, column=1, pady=8, padx=8, sticky='w')
            ttk.Label(edit_dialog, text='Username:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
            ttk.Label(edit_dialog, text=user['username'], style='Inventory.TLabel').grid(row=1, column=1, pady=8, padx=8, sticky='w')
            ttk.Label(edit_dialog, text='Password:', style='Inventory.TLabel').grid(row=2, column=0, pady=8, padx=8, sticky='e')
            password_entry = ttk.Entry(edit_dialog, width=25, style='TEntry')
            password_entry.insert(0, user['password'])
            password_entry.grid(row=2, column=1, pady=8, padx=8)
            ttk.Label(edit_dialog, text='Role:', style='Inventory.TLabel').grid(row=3, column=0, pady=8, padx=8, sticky='e')
            role_var = tk.StringVar(value=user['role'])
            role_combo = ttk.Combobox(edit_dialog, textvariable=role_var, values=['admin', 'user'], state='readonly', width=22)
            role_combo.grid(row=3, column=1, pady=8, padx=8)
            def save_edit():
                new_password = password_entry.get().strip()
                new_role = role_var.get()
                if not new_password:
                    messagebox.showerror('Error', 'Password cannot be empty!')
                    return
                user['password'] = new_password
                user['role'] = new_role
                save_users(self.users)
                messagebox.showinfo('Success', f"User '{user['username']}' updated!")
                edit_dialog.destroy()
                dialog.destroy()
                self.manage_users()
            ttk.Button(edit_dialog, text='Save', command=save_edit, style='Inventory.TButton').grid(row=4, column=0, columnspan=2, pady=12)
            ttk.Button(edit_dialog, text='Cancel', command=edit_dialog.destroy, style='Inventory.TButton').grid(row=5, column=0, columnspan=2, pady=5)
            edit_dialog.grab_set()
            password_entry.focus()
        def delete_user():
            selection = tree.selection()
            if not selection:
                messagebox.showerror('Error', 'No user selected!')
                return
            user_id = int(tree.item(selection[0])['values'][0])
            if user_id == getattr(self, 'current_user_id', None):
                messagebox.showerror('Error', 'You cannot delete yourself.')
                return
            user = find_user_by_id(self.users, user_id)
            if user is None:
                messagebox.showerror('Error', 'User not found!')
                return
            if messagebox.askyesno('Confirm', f"Delete user '{user['username']}'?"):
                self.users = [u for u in self.users if u['id'] != user_id]
                save_users(self.users)
                messagebox.showinfo('Success', f"User '{user['username']}' deleted!")
                dialog.destroy()
                self.manage_users()
        ttk.Button(btn_frame, text='Edit User', command=edit_user, style='Inventory.TButton').grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='Delete User', command=delete_user, style='Inventory.TButton').grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text='Close', command=dialog.destroy, style='Inventory.TButton').grid(row=0, column=2, padx=5)
        dialog.grab_set()

    def customer_list(self):
        # Gather unique customers from sell history
        history = load_sell_history()
        customers = {}
        for entry in history:
            if isinstance(entry, dict):
                key = (entry.get('customer_name', ''), entry.get('contact_number', ''))
                if key[0] and key[1]:
                    customers[key] = True
        customer_list = list(customers.keys())
        dialog = tk.Toplevel(self.root)
        dialog.title('Customer List')
        dialog.configure(bg='#f0f4f8')
        columns = ('No.', 'Customer Name', 'Contact Number')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
        tree.heading('No.', text='No.')
        tree.heading('Customer Name', text='Customer Name')
        tree.heading('Contact Number', text='Contact Number')
        tree.column('No.', width=50, anchor='center')
        tree.column('Customer Name', width=150, anchor='center')
        tree.column('Contact Number', width=120, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        for idx, customer in enumerate(customer_list, 1):
            name = customer[0] if len(customer) > 0 else ''
            contact = customer[1] if len(customer) > 1 else ''
            tree.insert('', 'end', values=(idx, name, contact))
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        btn_frame = ttk.Frame(dialog, style='Inventory.TFrame')
        btn_frame.pack(pady=10)
        def edit_customer():
            selection = tree.selection()
            if not selection:
                messagebox.showerror('Error', 'No customer selected!')
                return
            item = tree.item(selection[0])['values']
            old_name = item[1] if len(item) > 1 else ''
            old_contact = item[2] if len(item) > 2 else ''
            edit_dialog = tk.Toplevel(dialog)
            edit_dialog.title('Edit Customer')
            edit_dialog.configure(bg='#f0f4f8')
            ttk.Label(edit_dialog, text='Customer Name:', style='Inventory.TLabel').grid(row=0, column=0, pady=8, padx=8, sticky='e')
            name_entry = ttk.Entry(edit_dialog, width=25, style='TEntry')
            name_entry.insert(0, old_name)
            name_entry.grid(row=0, column=1, pady=8, padx=8)
            ttk.Label(edit_dialog, text='Contact Number:', style='Inventory.TLabel').grid(row=1, column=0, pady=8, padx=8, sticky='e')
            contact_entry = ttk.Entry(edit_dialog, width=25, style='TEntry')
            contact_entry.insert(0, old_contact)
            contact_entry.grid(row=1, column=1, pady=8, padx=8)
            def save_edit():
                new_name = name_entry.get().strip()
                new_contact = contact_entry.get().strip()
                if not new_name:
                    messagebox.showerror('Error', 'Customer name cannot be empty!')
                    return
                if not re.fullmatch(r'[A-Za-z ]+', new_name):
                    messagebox.showerror('Error', 'Customer name must contain only alphabets and spaces!')
                    return
                if not new_contact:
                    messagebox.showerror('Error', 'Contact number cannot be empty!')
                    return
                if not re.fullmatch(r'\d{10}', new_contact):
                    messagebox.showerror('Error', 'Contact number must be exactly 10 digits!')
                    return
                # Update all sell history entries for this customer
                history = load_sell_history()
                updated = False
                for entry in history:
                    if isinstance(entry, dict):
                        if entry.get('customer_name', '') == old_name and entry.get('contact_number', '') == old_contact:
                            entry['customer_name'] = new_name
                            entry['contact_number'] = new_contact
                            updated = True
                if updated:
                    save_sell_history(history)
                    messagebox.showinfo('Success', 'Customer details updated!')
                    edit_dialog.destroy()
                    dialog.destroy()
                    self.customer_list()
                else:
                    messagebox.showinfo('Info', 'No matching customer found in history.')
            ttk.Button(edit_dialog, text='Save', command=save_edit, style='Inventory.TButton').grid(row=2, column=0, columnspan=2, pady=12)
            ttk.Button(edit_dialog, text='Cancel', command=edit_dialog.destroy, style='Inventory.TButton').grid(row=3, column=0, columnspan=2, pady=5)
            edit_dialog.grab_set()
            name_entry.focus()
        ttk.Button(btn_frame, text='Edit Customer', command=edit_customer, style='Inventory.TButton').grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text='Close', command=dialog.destroy, style='Inventory.TButton').grid(row=0, column=1, padx=5)
        dialog.grab_set()

    def stock_report(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Stock Report')
        dialog.configure(bg='#f0f4f8')
        columns = ('Name', 'Quantity', 'Price', 'Total Price')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        grand_total = 0
        for item in self.inventory:
            total_price = item['quantity'] * item['price']
            grand_total += total_price
            tree.insert('', 'end', values=(item['name'], item['quantity'], item['price'], total_price))
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        grand_total_label = ttk.Label(dialog, text=f'Grand Total: {grand_total}', font=('Segoe UI', 12, 'bold'), background='#f0f4f8')
        grand_total_label.pack(pady=5)
        def export_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import os
            except ImportError:
                messagebox.showerror('Missing Library', 'reportlab is required to save PDF. Please install it with:\npip install reportlab')
                return
            reports_folder = 'reports'
            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)
            import datetime
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = os.path.join(reports_folder, f'stock_report_{now_str}.pdf')
            c = canvas.Canvas(file_name, pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont('Helvetica-Bold', 16)
            c.drawString(50, y, 'Stock Report')
            c.setFont('Helvetica', 12)
            y -= 30
            c.drawString(50, y, f'Date/Time: {now_str}')
            y -= 30
            c.drawString(50, y, 'Name')
            c.drawString(200, y, 'Quantity')
            c.drawString(300, y, 'Price')
            c.drawString(400, y, 'Total Price')
            y -= 20
            c.line(50, y, 500, y)
            y -= 20
            for item in self.inventory:
                c.drawString(50, y, str(item['name']))
                c.drawString(200, y, str(item['quantity']))
                c.drawString(300, y, str(item['price']))
                c.drawString(400, y, str(item['quantity'] * item['price']))
                y -= 20
                if y < 80:
                    c.showPage()
                    y = height - 50
            y -= 10
            c.setFont('Helvetica-Bold', 12)
            c.drawString(50, y, f'Grand Total: {grand_total}')
            c.save()
            messagebox.showinfo('Exported', f'Stock report saved as {file_name}')
        ttk.Button(dialog, text='Export as PDF', command=export_pdf).pack(pady=10)
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)
        dialog.grab_set()

    def sales_report(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Sales Report')
        dialog.configure(bg='#f0f4f8')
        columns = ('Date/Time', 'Item Name', 'Quantity Sold', 'Price', 'Total Sale', 'Discount (%)', 'Discount Price', 'Final Total', 'Customer Name', 'Contact Number')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        history = load_sell_history()
        for entry in history:
            if isinstance(entry, dict):
                tree.insert('', 'end', values=(
                    entry.get('timestamp', ''),
                    entry.get('name', ''),
                    entry.get('quantity_sold', ''),
                    entry.get('price', ''),
                    entry.get('total_sale', ''),
                    entry.get('discount_percent', 0),
                    entry.get('discount_price', 0),
                    entry.get('final_total', entry.get('total_sale', 0)),
                    entry.get('customer_name', ''),
                    entry.get('contact_number', ''),
                ))
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        def export_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import os
            except ImportError:
                messagebox.showerror('Missing Library', 'reportlab is required to save PDF. Please install it with:\npip install reportlab')
                return
            reports_folder = 'reports'
            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)
            import datetime
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = os.path.join(reports_folder, f'sales_report_{now_str}.pdf')
            c = canvas.Canvas(file_name, pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont('Helvetica-Bold', 16)
            c.drawString(50, y, 'Sales Report')
            c.setFont('Helvetica', 12)
            y -= 30
            c.drawString(50, y, f'Date/Time: {now_str}')
            y -= 30
            headers = ['Date/Time', 'Item', 'Qty', 'Price', 'Total', 'Disc(%)', 'Disc Amt', 'Final', 'Cust Name', 'Contact']
            x_positions = [50, 120, 200, 240, 290, 350, 410, 470, 530, 600]
            for i, h in enumerate(headers):
                c.drawString(x_positions[i], y, h)
            y -= 20
            c.line(50, y, 700, y)
            y -= 20
            for entry in history:
                if isinstance(entry, dict):
                    row = [
                        entry.get('timestamp', ''),
                        entry.get('name', ''),
                        entry.get('quantity_sold', ''),
                        entry.get('price', ''),
                        entry.get('total_sale', ''),
                        entry.get('discount_percent', 0),
                        entry.get('discount_price', 0),
                        entry.get('final_total', entry.get('total_sale', 0)),
                        entry.get('customer_name', ''),
                        entry.get('contact_number', ''),
                    ]
                    for i, val in enumerate(row):
                        c.drawString(x_positions[i], y, str(val))
                    y -= 20
                    if y < 80:
                        c.showPage()
                        y = height - 50
            c.save()
            messagebox.showinfo('Exported', f'Sales report saved as {file_name}')
        ttk.Button(dialog, text='Export as PDF', command=export_pdf).pack(pady=10)
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)
        dialog.grab_set()

    def customer_report(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Customer Report')
        dialog.configure(bg='#f0f4f8')
        columns = ('Customer Name', 'Contact Number', 'Total Purchases', 'Total Spent')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center')
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        history = load_sell_history()
        customers = {}
        for entry in history:
            if isinstance(entry, dict):
                key = (entry.get('customer_name', ''), entry.get('contact_number', ''))
                if key not in customers:
                    customers[key] = {'purchases': 0, 'spent': 0}
                customers[key]['purchases'] += 1
                customers[key]['spent'] += float(entry.get('final_total', 0))
        for (name, contact), data in customers.items():
            tree.insert('', 'end', values=(name, contact, data['purchases'], data['spent']))
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        def export_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import os
            except ImportError:
                messagebox.showerror('Missing Library', 'reportlab is required to save PDF. Please install it with:\npip install reportlab')
                return
            reports_folder = 'reports'
            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)
            import datetime
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = os.path.join(reports_folder, f'customer_report_{now_str}.pdf')
            c = canvas.Canvas(file_name, pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont('Helvetica-Bold', 16)
            c.drawString(50, y, 'Customer Report')
            c.setFont('Helvetica', 12)
            y -= 30
            c.drawString(50, y, f'Date/Time: {now_str}')
            y -= 30
            headers = ['Customer Name', 'Contact', 'Purchases', 'Total Spent']
            x_positions = [50, 250, 400, 500]
            for i, h in enumerate(headers):
                c.drawString(x_positions[i], y, h)
            y -= 20
            c.line(50, y, 600, y)
            y -= 20
            for (name, contact), data in customers.items():
                row = [name, contact, data['purchases'], data['spent']]
                for i, val in enumerate(row):
                    c.drawString(x_positions[i], y, str(val))
                y -= 20
                if y < 80:
                    c.showPage()
                    y = height - 50
            c.save()
            messagebox.showinfo('Exported', f'Customer report saved as {file_name}')
        ttk.Button(dialog, text='Export as PDF', command=export_pdf).pack(pady=10)
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)
        dialog.grab_set()

    def summary_report(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Summary Report')
        dialog.configure(bg='#f0f4f8')
        history = load_sell_history()
        total_sales = 0
        total_discount = 0
        total_revenue = 0
        num_sales = 0
        for entry in history:
            if isinstance(entry, dict):
                total_sales += float(entry.get('total_sale', 0))
                total_discount += float(entry.get('discount_price', 0))
                total_revenue += float(entry.get('final_total', 0))
                num_sales += 1
        summary_text = (
            f'Total Sales: {total_sales}\n'
            f'Total Discount: {total_discount}\n'
            f'Total Revenue: {total_revenue}\n'
            f'Number of Sales: {num_sales}'
        )
        label = ttk.Label(dialog, text=summary_text, font=('Segoe UI', 13), background='#f0f4f8', justify='left')
        label.pack(padx=20, pady=20)
        def export_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import os
            except ImportError:
                messagebox.showerror('Missing Library', 'reportlab is required to save PDF. Please install it with:\npip install reportlab')
                return
            reports_folder = 'reports'
            if not os.path.exists(reports_folder):
                os.makedirs(reports_folder)
            import datetime
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = os.path.join(reports_folder, f'summary_report_{now_str}.pdf')
            c = canvas.Canvas(file_name, pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont('Helvetica-Bold', 16)
            c.drawString(50, y, 'Summary Report')
            c.setFont('Helvetica', 12)
            y -= 30
            c.drawString(50, y, f'Date/Time: {now_str}')
            y -= 30
            c.drawString(50, y, f'Total Sales: {total_sales}')
            y -= 20
            c.drawString(50, y, f'Total Discount: {total_discount}')
            y -= 20
            c.drawString(50, y, f'Total Revenue: {total_revenue}')
            y -= 20
            c.drawString(50, y, f'Number of Sales: {num_sales}')
            c.save()
            messagebox.showinfo('Exported', f'Summary report saved as {file_name}')
        ttk.Button(dialog, text='Export as PDF', command=export_pdf).pack(pady=10)
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=5)
        dialog.grab_set()

    def profit_loss_report(self):
        history = load_sell_history()
        conn = sqlite3.connect(LOCALDB_FILE)
        cursor = conn.cursor()
        # Map item name to cost price (latest in inventory)
        cursor.execute('SELECT name, cost_price FROM inventory')
        cost_price_map = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        report_dialog = tk.Toplevel(self.root)
        report_dialog.title('Profit/Loss Report')
        report_dialog.configure(bg='#f0f4f8')
        columns = ('No.', 'Item Name', 'Quantity Sold', 'Cost Price', 'Final Total', 'Profit', 'Loss')
        # Frame for tree and scrollbars
        tree_frame = ttk.Frame(report_dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', stretch=True, width=120)
        # Scrollbars
        xscrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        yscrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(xscrollcommand=xscrollbar.set, yscrollcommand=yscrollbar.set)
        tree.grid(row=0, column=0, sticky='nsew')
        yscrollbar.grid(row=0, column=1, sticky='ns')
        xscrollbar.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        total_profit = 0
        total_loss = 0
        for idx, entry in enumerate(history, 1):
            if isinstance(entry, dict):
                name = entry.get('name', '')
                qty = entry.get('quantity_sold', 0) or 0
                final_total = entry.get('final_total', 0) or 0
                cost_price = cost_price_map.get(name, 0) or 0
                try:
                    qty = float(qty)
                except Exception:
                    qty = 0
                try:
                    final_total = float(final_total)
                except Exception:
                    final_total = 0
                try:
                    cost_price = float(cost_price)
                except Exception:
                    cost_price = 0
                cost_total = cost_price * qty
                profit = 0
                loss = 0
                if final_total > cost_total:
                    profit = final_total - cost_total
                    total_profit += profit
                elif final_total < cost_total:
                    loss = cost_total - final_total
                    total_loss += loss
                tree.insert('', 'end', values=(idx, name, qty, cost_price, final_total, profit, loss))
        total_label = ttk.Label(report_dialog, text=f'Total Profit: {total_profit}    Total Loss: {total_loss}', font=('Segoe UI', 12, 'bold'), background='#f0f4f8')
        total_label.pack(pady=10)
        ttk.Button(report_dialog, text='Close', command=report_dialog.destroy, style='Inventory.TButton').pack(pady=5)
        report_dialog.grab_set()

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == '__main__':
    initialize_database()
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop() 