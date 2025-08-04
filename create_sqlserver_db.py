import json
import os
import pyodbc

CONFIG_DIR = 'config'
USERS_FILE = os.path.join(CONFIG_DIR, 'users.json')
INVENTORY_FILE = os.path.join(CONFIG_DIR, 'inventory.json')
SELL_HISTORY_FILE = os.path.join(CONFIG_DIR, 'sell_history.json')

# SQL Server connection parameters
SERVER = r'OITS-2100145\SQLEXPRESS'
DATABASE = 'Inventry'

# Connect to SQL Server using Windows Authentication
conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};Trusted_Connection=yes;')
conn.autocommit = True
cursor = conn.cursor()

# Create database if not exists
try:
    cursor.execute(f"IF DB_ID('{DATABASE}') IS NULL CREATE DATABASE {DATABASE}")
    print(f"Database '{DATABASE}' ensured.")
except Exception as e:
    print(f"Error creating database: {e}")

# Connect to the new database
conn.close()
conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;')
cursor = conn.cursor()

# Create tables
cursor.execute('''
IF OBJECT_ID('users', 'U') IS NOT NULL DROP TABLE users;
CREATE TABLE users (
    id INT PRIMARY KEY,
    username NVARCHAR(100),
    password NVARCHAR(100),
    role NVARCHAR(50)
)
''')
cursor.execute('''
IF OBJECT_ID('inventory', 'U') IS NOT NULL DROP TABLE inventory;
CREATE TABLE inventory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100),
    quantity INT,
    price FLOAT,
    barcode NVARCHAR(100)
)
''')
cursor.execute('''
IF OBJECT_ID('sell_history', 'U') IS NOT NULL DROP TABLE sell_history;
CREATE TABLE sell_history (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100),
    quantity_sold INT,
    price FLOAT NULL,
    total_sale FLOAT NULL,
    discount FLOAT NULL,
    discount_percent FLOAT NULL,
    discount_price FLOAT NULL,
    final_total FLOAT NULL,
    timestamp NVARCHAR(50),
    customer_name NVARCHAR(100) NULL,
    contact_number NVARCHAR(100) NULL
)
''')
conn.commit()

# Insert default users if not present
try:
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    result = cursor.fetchone()
    if result and result[0] == 0:
        cursor.execute('INSERT INTO users (id, username, password, role) VALUES (?, ?, ?, ?)', 1, 'admin', 'admin123', 'admin')
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'user'")
    result = cursor.fetchone()
    if result and result[0] == 0:
        cursor.execute('INSERT INTO users (id, username, password, role) VALUES (?, ?, ?, ?)', 2, 'user', 'user123', 'user')
    conn.commit()
    print('Default users ensured in database.')
except Exception as e:
    print(f'Error inserting default users: {e}')

print('Database, tables, and data import complete.') 