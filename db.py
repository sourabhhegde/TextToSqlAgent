from sqlalchemy import create_engine, text
import os

# Define the database file name
DB_FILE = 'products.db'
DB_PATH = os.path.join(os.getcwd(), DB_FILE)

# If the database file already exists, remove it (for a clean start each time)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Existing database '{DB_FILE}' removed.")

# Create the SQLAlchemy engine for SQLite
# The 'sqlite:///' prefix indicates a SQLite database
# f"sqlite:///{DB_FILE}" creates a database file named 'products.db' in your project root
engine = create_engine(f"sqlite:///{DB_FILE}")

# Connect to the database and execute SQL commands
with engine.connect() as connection:
    # Create a simple 'products' table
    create_table_sql = """
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT,
        price REAL,
        stock_quantity INTEGER
    );
    """
    connection.execute(text(create_table_sql))
    print("Table 'products' created successfully.")

    # Insert some sample data
    insert_data_sql = """
    INSERT INTO products (product_name, category, price, stock_quantity) VALUES
    ('Laptop Pro', 'Electronics', 1200.00, 50),
    ('Mechanical Keyboard', 'Electronics', 150.00, 120),
    ('Wireless Mouse', 'Accessories', 35.50, 300),
    ('USB-C Hub', 'Accessories', 50.00, 80),
    ('Monitor 27-inch', 'Electronics', 300.00, 70),
    ('Ergonomic Chair', 'Furniture', 350.00, 30),
    ('Webcam Full HD', 'Accessories', 75.00, 90);
    """
    connection.execute(text(insert_data_sql))
    print("Sample data inserted into 'products' table.")

    # Commit the changes
    connection.commit()

print(f"Database '{DB_FILE}' created and populated at {DB_PATH}")
print("Database setup complete!")