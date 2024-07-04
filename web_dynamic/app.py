#!/usr/bin/python3

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import mysql.connector
import bcrypt
import requests
import os

app = Flask(__name__)
app.secret_key = 'aadasdfsdgsdfsd'
db_host = 'localhost'
db_user = 'Mrithika'
db_password = 'SQL4mri$'
db_database = 'freshbasket'

# Configure MySQL connection
db_config = {
    'host': db_host,
    'user': db_user,
    'password': db_password ,
    'database': db_database
}


# Route for landing page
@app.route('/')
def home():
    if 'email' in session:
        cart_count = get_cart_count()
        return render_template('index.html', cart_count=cart_count)
    else:
        return redirect(url_for('signin'))
     






# Route for the product page
@app.route('/products')
def products():
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve product data from the database
    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Render the template and pass the product data to it
    cart_count = get_cart_count()
    return render_template('shop.html', products=products, cart_count=cart_count)


def get_cart_count():
    # Check if the user is authenticated
    if 'email' in session:
        # Connect to the MySQL database
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()

        # Retrieve the cart count for the user
        select_query = """
        SELECT COUNT(CP.ProductId)
        FROM CartProduct CP
        JOIN Cart C ON CP.CartId = C.Id
        JOIN User U ON C.UserId = U.Id
        WHERE U.Email = %s
        """
        cursor.execute(select_query, (session['email'],))
        cart_count = cursor.fetchone()[0]

        # Close the cursor and connection
        cursor.close()
        cnx.close()

        return cart_count

    pass


# Route for sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Connect to the MySQL database
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()

        # Check if the email already exists in the database
        select_query = "SELECT * FROM User WHERE Email = %s"
        cursor.execute(select_query, (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            # If the email already exists, display an error message
            error_message = 'Email already exists. Please choose a different email.'
            return render_template('signup.html', error_message=error_message)
        else:
            # Insert the user data into the database
            insert_query = "INSERT INTO User (Name, Email, Password, Phone) VALUES (%s, %s, %s, %s)"
            user_data = (name, email, hashed_password.decode('utf-8'), phone)  # Store the hashed password
            cursor.execute(insert_query, user_data)

            # Commit the changes
            cnx.commit()

        # Close the cursor and connection
        cursor.close()
        cnx.close()

        # Create a session for the user
        session['email'] = email

        # Redirect to the profile page
        return redirect(url_for('profile'))
    else:
        return render_template('signup.html')


# Route for sign in
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        # Retrieve form data
        email = request.form.get('email')
        password = request.form.get('password')

        # Connect to the MySQL database
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()

        # Retrieve the hashed password from the database
        query = "SELECT Password FROM User WHERE Email = %s"
        cursor.execute(query, (email,))
        result = cursor.fetchone()

        if result:
            hashed_password = result[0]
            # Verify the password
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                # If credentials are valid, create a session for the user
                session['email'] = email

                # Redirect to the home page
                return redirect(url_for('home'))

        # User not found or invalid credentials
        return render_template('signup.html')

        # Close the cursor and connection
        cursor.close()
        cnx.close()

    # If it's a GET request and the user is already signed in, redirect to the home page
    if 'email' in session:
        return redirect(url_for('home'))

    # If it's a GET request and the user is not signed in, render the sign-in page
    return render_template('signin.html')


@app.route('/profile')
def profile():
    # Check if the user is authenticated (session exists)
    if 'email' in session:
        # Connect to the MySQL database
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()

        # Retrieve user data from the database
        cursor.execute("SELECT * FROM User WHERE Email = %s", (session['email'],))
        user = cursor.fetchone()

         # Retrieve shipping info from database
        select_shipping_query = """
        SELECT * FROM Shipping
        INNER JOIN User ON Shipping.UserId = User.Id
        WHERE User.Email = %s
        """
        cursor.execute(select_shipping_query, (session['email'],))
        shipping_info = cursor.fetchall()

        # Close the cursor and connection
        cursor.close()
        cnx.close()

        # checks items on the cart
        cart_count = get_cart_count()

        # Render the template and pass the user data to it
        return render_template('profile.html', user=user, shipping_info=shipping_info, cart_count=cart_count)
    else:
        return redirect(url_for('signin'))


# Route for signing out
@app.route('/signout')
def signout():
    # Clear the session
    session.clear()

    # Redirect to the sign-in page
    return redirect(url_for('signin'))


@app.route('/search')
def search():
    # Get the search query from the request's query parameters
    query = request.args.get('query')

    # Check if the query is None or empty
    if not query or query.strip() == '':
        # Handle the case when no query is provided
        return redirect(url_for('products'))

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Search for products matching the query
    search_query = "SELECT * FROM Product WHERE Name LIKE %s OR Description LIKE %s"
    pattern = f'%{query}%'
    cursor.execute(search_query, (pattern, pattern))
    products = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # checks items on the cart
    cart_count = get_cart_count()

    # Render the template and pass the product data to it
    return render_template('search_results.html', products=products, query=query, cart_count=cart_count)


# Route for cart
@app.route('/cart')
def cart():
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve cart data for the user from the database
    select_query = """
    SELECT P.Id, P.Name, P.Description, P.Price, P.Image, P.Category,CP.Quantity
    FROM CartProduct CP
    JOIN Product P ON CP.ProductId = P.Id
    JOIN Cart C ON CP.CartId = C.Id
    JOIN User U ON C.UserId = U.Id
    WHERE U.Email = %s
    """
    cursor.execute(select_query, (session['email'],))
    cart_products = cursor.fetchall()

    # Calculate the total price of the cart
    total_query = """
    SELECT SUM(P.Price*Quantity)
    FROM CartProduct CP
    JOIN Product P ON CP.ProductId = P.Id
    JOIN Cart C ON CP.CartId = C.Id
    JOIN User U ON C.UserId = U.Id
    WHERE U.Email = %s
    """
    cursor.execute(total_query, (session['email'],))
    total_price = cursor.fetchone()[0]

     # Retrieve shipping info from database
    select_shipping_query = """
    SELECT * FROM Shipping
    INNER JOIN User ON Shipping.UserId = User.Id
    WHERE User.Email = %s
    """
    cursor.execute(select_shipping_query, (session['email'],))
    shipping_info = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Render the template and pass the cart data and shipping information to it
    return render_template('cart.html', cart_products=cart_products, total_price=total_price, shipping_info=shipping_info)


# Route for adding a product to the cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Retrieve the product ID from the request form
    product_id = request.form.get('product_id')

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve the user's cart ID
    select_cart_query = "SELECT Id FROM Cart WHERE UserId = (SELECT Id FROM User WHERE Email = %s)"
    cursor.execute(select_cart_query, (session['email'],))
    cart_row = cursor.fetchone()

    # Check if the user has an active cart
    if cart_row:
        cart_id = cart_row[0]
    else:
        # If the user does not have a cart, create a new cart
        insert_cart_query = "INSERT INTO Cart (UserId) SELECT Id FROM User WHERE Email = %s"
        cursor.execute(insert_cart_query, (session['email'],))
        cnx.commit()

        # Retrieve the new cart ID
        cart_id = cursor.lastrowid

    # Insert the product into the user's cart
    cursor.execute("select productid from cartproduct where cartid=%s and productid=%s",(cart_id,product_id));
    if(cursor.fetchone()):
        update_cart_product_query="UPDATE CARTPRODUCT SET QUANTITY=QUANTITY+1 WHERE cartid=%s and productid=%s"
        cursor.execute(update_cart_product_query,(cart_id,product_id))
    else:      
        insert_cart_product_query = "INSERT INTO CartProduct (CartId, ProductId,Quantity) VALUES (%s, %s,%s)" #added the 0
        cart_product_data = (cart_id, product_id,1)
        cursor.execute(insert_cart_product_query, cart_product_data)
    cnx.commit()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Redirect back to the products page
    return jsonify({'status': 'success'})


# Route for removing a product from the cart
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Get the product ID from the request form
    product_id = request.form.get('product_id')

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve the user's cart ID
    select_cart_query = "SELECT Id FROM Cart WHERE UserId = (SELECT Id FROM User WHERE Email = %s)"
    cursor.execute(select_cart_query, (session['email'],))
    cart_id = cursor.fetchone()[0]

    # Delete the product from the user's cart
    delete_query = "DELETE FROM CartProduct WHERE CartId = %s AND ProductId = %s"
    cursor.execute(delete_query, (cart_id, product_id))

    # Commit the changes
    cnx.commit()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Redirect back to the cart page
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve cart data for the user from the database
    select_query = """
    SELECT P.Id, P.Name, P.Description, P.Price, P.Image, P.Category,CP.Quantity
    FROM CartProduct CP
    JOIN Product P ON CP.ProductId = P.Id
    JOIN Cart C ON CP.CartId = C.Id
    JOIN User U ON C.UserId = U.Id
    WHERE U.Email = %s
    """
    cursor.execute(select_query, (session['email'],))
    cart_products = cursor.fetchall()

    # Calculate the total price of the cart
    total_query = """
    SELECT SUM(P.Price*Quantity)
    FROM CartProduct CP
    JOIN Product P ON CP.ProductId = P.Id
    JOIN Cart C ON CP.CartId = C.Id
    JOIN User U ON C.UserId = U.Id
    WHERE U.Email = %s
    """
    cursor.execute(total_query, (session['email'],))
    total_price = cursor.fetchone()[0]

    # Retrieve shipping info from database
    select_shipping_query = """
    SELECT * FROM Shipping
    INNER JOIN User ON Shipping.UserId = User.Id
    WHERE User.Email = %s
    """
    cursor.execute(select_shipping_query, (session['email'],))
    shipping_info = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Render the template and pass the cart data to it
    return render_template('checkout.html',
                           cart_products=cart_products,
                           total_price=total_price,
                           shipping_info=shipping_info)


@app.route('/place_order', methods=['POST'])
def place_order():
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Retrieve the user's ID
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve the UserId based on the user's email in the session
    select_user_id_query = "SELECT Id FROM User WHERE Email = %s"
    cursor.execute(select_user_id_query, (session['email'],))
    user_id = cursor.fetchone()[0]

    # Retrieve the user's cart ID
    select_cart_query = "SELECT Id FROM Cart WHERE UserId = %s"
    cursor.execute(select_cart_query, (user_id,))
    cart_id = cursor.fetchone()[0]

    # Calculate the total price of the order
    total_query = """
    SELECT SUM(P.Price*CP.Quantity)
    FROM CartProduct CP
    JOIN Product P ON CP.ProductId = P.Id
    JOIN Cart C ON CP.CartId = C.Id
    JOIN User U ON C.UserId = U.Id
    WHERE U.Id = %s
    """
    cursor.execute(total_query, (user_id,))
    total_price = cursor.fetchone()[0]

    # Insert the order into the database
    insert_order_query = "INSERT INTO `Order` (UserId, Status, Total) VALUES (%s, %s, %s)"
    cursor.execute(insert_order_query, (user_id, 'processing', total_price))
    cnx.commit()
    order_id = cursor.lastrowid
    select_cart_products_query = "SELECT ProductId,Quantity FROM CartProduct WHERE CartId = %s"
    cursor.execute(select_cart_products_query, (cart_id,))
    cart_products = cursor.fetchall()

    # Insert the products into the OrderProduct table
    insert_order_product_query = "INSERT INTO OrderProduct (OrderId, ProductId,Quantity) VALUES (%s, %s,%s)"
    order_product_data = [(order_id, product_id, quantity,) for product_id,quantity, in cart_products]
    cursor.executemany(insert_order_product_query, order_product_data)
    cnx.commit()

    # Remove the products from the user's cart
    delete_cart_products_query = "DELETE FROM CartProduct WHERE CartId = %s"
    cursor.execute(delete_cart_products_query, (cart_id,))

    # Commit the changes
    cnx.commit()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # Redirect to the order confirmation page
    return redirect(url_for('order_confirmation', order_id=order_id))


@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()

    # Retrieve the order details from the database
    select_order_query = """
    SELECT O.Id, P.Name, P.Description, P.Price, P.Image, P.Category,OP.Quantity
    FROM `Order` O
    JOIN OrderProduct OP ON O.Id = OP.OrderId
    JOIN Product P ON OP.ProductId = P.Id
    JOIN User U ON O.UserId = U.Id
    WHERE U.Email = %s AND O.Id = %s
    """
    cursor.execute(select_order_query, (session['email'], order_id))
    order_products = cursor.fetchall()

    # Calculate the total price of the order
    total_query = """
    SELECT SUM(P.Price*OP.Quantity)
    FROM `Order` O
    JOIN OrderProduct OP ON O.Id = OP.OrderId
    JOIN Product P ON OP.ProductId = P.Id
    JOIN User U ON O.UserId = U.Id
    WHERE U.Email = %s AND O.Id = %s
    """
    cursor.execute(total_query, (session['email'], order_id))
    total_price = cursor.fetchone()[0]

    # Retrieve shipping info from database
    select_shipping_query = """
    SELECT * FROM Shipping
    INNER JOIN User ON Shipping.UserId = User.Id
    WHERE User.Email = %s
    """
    cursor.execute(select_shipping_query, (session['email'],))
    shipping_info = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    # checks items on the cart
    cart_count = get_cart_count()

    # Render the template and pass the order data to it
    return render_template('order_confirmation.html',
                           order_id=order_id,
                           order_products=order_products,
                           total_price=total_price,
                           shipping_info=shipping_info,
                           cart_count=cart_count)


# Route for adding shipping information
@app.route('/shipping', methods=['GET', 'POST'])
def shipping():
    # Check if the user is authenticated
    if 'email' not in session:
        return redirect(url_for('signin'))

    if request.method == 'POST':
        if 'delete_shipping' in request.form:
            # Delete shipping information
            shipping_id = request.form.get('delete_shipping')
            # Connect to the MySQL database
            cnx = mysql.connector.connect(**db_config)
            cursor = cnx.cursor()
            
            # Delete the shipping information from the database
            delete_shipping_query = "DELETE FROM Shipping WHERE Id = %s"
            cursor.execute(delete_shipping_query, (shipping_id,))
            cnx.commit()

            # Close the cursor and connection
            cursor.close()
            cnx.close()

            # Redirect the user back to the shipping page
            return redirect(url_for('shipping'))

        else:
            # Retrieve shipping information from the form
            full_name = request.form.get('full_name')
            street_address = request.form.get('street_address')
            city = request.form.get('city')
            state_province = request.form.get('state_province')
            postal_code = request.form.get('postal_code')
            country = request.form.get('country')

            # Connect to the MySQL database
            cnx = mysql.connector.connect(**db_config)
            cursor = cnx.cursor()

            # Retrieve the user's ID
            select_user_query = "SELECT Id FROM User WHERE Email = %s"
            cursor.execute(select_user_query, (session['email'],))
            user_id = cursor.fetchone()[0]

            # Insert the shipping information into the shipping table
            insert_shipping_query = """
            INSERT INTO Shipping (UserId, Full_Name, Street_Address, City, State_Province, Postal_Code, Country)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            shipping_data = (user_id, full_name, street_address, city, state_province, postal_code, country)
            cursor.execute(insert_shipping_query, shipping_data)
            cnx.commit()

            # Retrieve shipping info from database
            select_shipping_query = """
            SELECT * FROM Shipping
            INNER JOIN User ON Shipping.UserId = User.Id
            WHERE User.Email = %s
            """
            cursor.execute(select_shipping_query, (session['email'],))
            shipping_info = cursor.fetchall()

            # Close the cursor and connection
            cursor.close()
            cnx.close()

            # redirect the user back to the shipping page
            return render_template('shipping.html', shipping_info=shipping_info)

    # If it's a GET request, render the shipping information form
    # Retrieve existing shipping info from database
    # Connect to the MySQL database
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    
    # Retrieve shipping info from the database
    select_shipping_query = """
    SELECT * FROM Shipping
    INNER JOIN User ON Shipping.UserId = User.Id
    WHERE User.Email = %s
    """
    cursor.execute(select_shipping_query, (session['email'],))
    shipping_info = cursor.fetchall()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    return render_template('shipping.html', shipping_info=shipping_info)








if __name__ == '__main__':
    app.run(debug=True)