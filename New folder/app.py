from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import sqlite3
from flask import flash

app = Flask(__name__)

def connect_to_database():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    # Print the schema of the items table
    print(cursor.execute("PRAGMA table_info(items)").fetchall())
    
    cursor.execute('''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit TEXT NOT NULL,
    cost_per_unit REAL NOT NULL,
    total_cost REAL NOT NULL,
    selling_price REAL NOT NULL,
    supplier TEXT,
    date_added DATE NOT NULL,
    last_updated DATE,
    location TEXT,
    min_stock_level INTEGER,
    max_stock_level INTEGER,
    reorder_quantity INTEGER,
    notes TEXT,
    current_date DATE NOT NULL
)
''')

    cursor.execute('''
CREATE TABLE IF NOT EXISTS issued_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,  -- Foreign key to items table
    name TEXT,
    quantity_issued INTEGER,
    date_issued DATE,
    department_name TEXT  -- Add this line to create the department_name column
)
''')
    
    cursor.execute('''
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    transaction_type TEXT,
    quantity INTEGER,
    transaction_date DATE,
    FOREIGN KEY (item_id) REFERENCES items (id)
)
''')

    conn.commit()

    return conn, cursor

@app.route('/')
def display_inventory():
    conn, cursor = connect_to_database()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    conn.close()

    return render_template('inventory.html', items=items)
# -------------------------------------------------------------------------------
@app.route('/search_inventory', methods=['GET'])
def search_inventory():
    conn, cursor = connect_to_database()

    # Get the search term from the query parameters
    search_term = request.args.get('search', '').strip()

    # Perform a search in the database (modify the query as needed)
    cursor.execute("SELECT * FROM items WHERE name LIKE ?", ('%' + search_term + '%',))
    items = cursor.fetchall()

    conn.close()

    # Render the template with the search results
    return render_template('inventory.html', items=items)

# --------------------------------------------------------------------------------------------------
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    conn, cursor = connect_to_database()

    # Delete the item from the database
    cursor.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('display_inventory'))


@app.route('/update_item/<int:item_id>', methods=['GET', 'POST'])
def update_item(item_id):
    conn, cursor = connect_to_database()

    if request.method == 'POST':
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        # Update the item in the database
        cursor.execute("UPDATE items SET quantity=?, selling_price=? WHERE id=?", (quantity, price, item_id))
        conn.commit()
        conn.close()

        return redirect(url_for('display_inventory'))

    # Fetch the item details for pre-filling the form
    cursor.execute("SELECT * FROM items WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()

    return render_template('update_item.html', item=item)

# ----------------------------------------------------------------------------

# @app.route('/display_issued_items', methods=['GET', 'POST'])
# def display_issued_items():
#     conn, cursor = connect_to_database()
#     cursor.execute("SELECT * FROM issued_items")
#     issue_item = cursor.fetchall()
#     conn.close()

#     return render_template('issue_item.html', issue_item=issue_item)

# ---------------------------------------------------------------------------------

# Modify the issue_item route
# Modify the issue_item route
@app.route('/issue_item', methods=['GET', 'POST'])
def issue_item():
    conn, cursor = connect_to_database()

    item = None  # Initialize item to None

    if request.method == 'POST':
        item_id = request.form.get('item_id')  # Get item_id from form
        quantity_issued = int(request.form['quantity_issued'])
        department_name = request.form['department_name']

        print(f"Debug: item_id={item_id}, quantity_issued={quantity_issued}, department_name={department_name}")

        if not item_id or not item_id.isdigit():
            flash("Invalid item ID. Please enter a valid number.", 'danger')
            conn.close()
            return redirect(url_for('issue_item'))

        item_id = int(item_id)

        # Fetch item details
        cursor.execute("SELECT * FROM items WHERE id=?", (item_id,))
        item = cursor.fetchone()

        if item and item[2] >= quantity_issued and quantity_issued > 0:
            try:
                # Update item quantity in the items table
                cursor.execute("UPDATE items SET quantity=? WHERE id=?", (item[2] - quantity_issued, item_id))

                # Insert issued item details into the issued_items table
                cursor.execute("INSERT INTO issued_items (item_id, name, quantity_issued, date_issued, department_name) VALUES (?, ?, ?, ?, ?)",
                                (item_id, item[1], quantity_issued, datetime.now().date(), department_name))
                print("Debug: Data inserted into issued_items table.")

                cursor.execute("INSERT INTO ledger (item_id, transaction_type, quantity, transaction_date) VALUES (?, ?, ?, ?)",
                                (item_id, 'issue', quantity_issued, datetime.now().date()))


                conn.commit()  # Commit changes to the database
                conn.close()

                flash(f"{quantity_issued} {item[1]} issued to {department_name}.", 'success')
                return redirect(url_for('view_issued_items'))

            except Exception as e:
                print(f"Error issuing item: {str(e)}")
                flash(f"Error issuing item: {str(e)}", 'danger')
                conn.close()

        else:
            flash("Failed to issue item. Please check the entered details.", 'danger')

    conn.close()
    return render_template('issue_item.html', item=item)



# Add this to your Flask application
# Add a new route for viewing issued items in a table
# Add this to your Flask application
# Add a new route for viewing issued items in a table
# Update the view_issued_items route in your Flask application
@app.route('/view_issued_items', methods=['GET', 'POST'])
def view_issued_items():
    conn, cursor = connect_to_database()
    cursor.execute("SELECT * FROM issued_items")
    issued_items = cursor.fetchall()
    conn.close()

    return render_template('view_issued_items.html', issued_items=issued_items)


# -----------------------------------------------------------------------------------------------------

@app.route('/view_ledger/<int:item_id>')
def view_ledger(item_id):
    conn, cursor = connect_to_database()

    # Fetch item details for the ledger
    cursor.execute("SELECT * FROM items WHERE id=?", (item_id,))
    item = cursor.fetchone()

    if item:
        # Fetch ledger data for the item
        cursor.execute("SELECT * FROM ledger WHERE item_id=?", (item_id,))
        ledger_data = cursor.fetchall()

        conn.close()

        return render_template('view_ledger.html', item=item, ledger_data=ledger_data)
    else:
        flash("Item not found.", 'danger')
        conn.close()
        return redirect(url_for('display_inventory'))



# -----------------------------------------------------------------------------------------------

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        conn, cursor = connect_to_database()
        id = request.form['id']
        name = request.form['name']
        quantity = int(request.form['quantity'])
        unit = request.form['unit']
        cost_per_unit = float(request.form['cost_per_unit'])
        selling_price = float(request.form['selling_price'])
        supplier = request.form['supplier']
        date_added_str = request.form['date_added']

        # Check if date_added is provided, set to current date if not
        date_added = datetime.now().date() if not date_added_str else datetime.strptime(date_added_str, '%Y-%m-%d').date()

        location = request.form['location']
        min_stock_level = int(request.form['min_stock_level'])
        max_stock_level = int(request.form['max_stock_level'])
        reorder_quantity = int(request.form['reorder_quantity'])
        notes = request.form['notes']

        current_date = datetime.now().date()

        cursor.execute("INSERT INTO items (id, name, quantity, unit, cost_per_unit, total_cost, selling_price, supplier, date_added, location, min_stock_level, max_stock_level, reorder_quantity, notes, current_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (id, name, quantity, unit, cost_per_unit, quantity * cost_per_unit, selling_price, supplier, date_added, location, min_stock_level, max_stock_level, reorder_quantity, notes, current_date))

        conn.commit()
        conn.close()

        return redirect(url_for('display_inventory'))

    current_date = datetime.now().date()
    return render_template('add_item.html', current_date=current_date)



if __name__ == '__main__':
    app.secret_key = 'ucbpl'  # Set your secret key here
    app.run(debug=False)

