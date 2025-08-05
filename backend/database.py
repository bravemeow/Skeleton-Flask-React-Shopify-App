import sqlite3
import os
from datetime import datetime

DB_PATH = "shopify_app.db"

# Database Connection
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Database Initialization
def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                shop TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                scope TEXT,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# Database Testing
if __name__ == "__main__":
    init_db()
    print("Database initialized [dev mode]")
    print("Database path: ", DB_PATH)
    print("choose your action:")
    print("1. Show all shops")
    print("2. Show a shop")
    print("3. Add a shop")
    print("4. Delete a shop")
    print("5. Exit")
    choice = input("Enter your choice: ")

    if choice == "1":
        with get_db() as db:
            shops = db.execute("SELECT * FROM shops").fetchall()
            for shop in shops:
                print(shop["shop"])
            if not shops:
                print("No shops found")
    elif choice == "2":
        shop = input("Enter shop name: ")
        with get_db() as db:
            shop = db.execute("SELECT * FROM shops WHERE shop = ?", (shop,)).fetchone()
            if not shop:
                print("Shop not found")
            else:
                print(shop)
    elif choice == "3":
        shop = input("Enter shop name: ")
        with get_db() as db:
            db.execute("INSERT INTO shops (shop, access_token, scope, installed_at) VALUES (?, ?, ?, ?)", (shop, "", "", datetime.now()))
            print("Shop added")
    elif choice == "4":
        shop = input("Enter shop name: ")
        with get_db() as db:
            db.execute("DELETE FROM shops WHERE shop = ?", (shop,))
            print("Shop deleted")
    elif choice == "5":
        print("Exiting...")
        exit()
    else:
        print("Invalid choice")
