import os

# Setting environment variables
os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAU6GDVBMRZ3SGFPVF'
os.environ['AWS_SECRET_ACCESS_KEY'] = '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'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'

from flask import Flask, request, jsonify, render_template
import auth  
import csv_loader_nora
import boto3
from boto3.dynamodb.conditions import Attr
import decimal
import json
import pymongo
from pymongo import MongoClient
from place_order import display_product, order_placer
import bson
from bson import ObjectId
from cancel_order import cancel_order
from search_order import search_display_orders

def serialize_mongo_documents(data):
    if isinstance(data, list):
        return [serialize_mongo_documents(item) for item in data]
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = serialize_mongo_documents(value)
        return data
    if isinstance(data, ObjectId):
        return str(data)
    return data

app = Flask(__name__)

current_db_config = {}
user_session = {
    'email': None,
    'role': None,
    'customer_id': None,
    'cart': []
}

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_database', methods=['POST'])
def set_database():
    db_choice = request.form['database']
    try:
        if db_choice == 'MongoDB':
            current_db_config['type'] = 'mongodb'
            current_db_config['config'] = {
                'uri': "mongodb://localhost:27017/",
                'db_name': "ecommerce_db",
            }
            message = csv_loader_nora.load_csv_to_database('mongodb', current_db_config['config'])
            print(json.dumps(message))  
            return jsonify(message)
        elif db_choice == 'DynamoDB':
            current_db_config['type'] = 'dynamodb'
            current_db_config['config'] = {
                'region': 'us-east-2',
            }
            message =csv_loader_nora.load_csv_to_database('dynamodb', current_db_config['config'])
            print(json.dumps(message))
            return jsonify(message)
        return jsonify({'message': 'Database setup failed.'})
    except Exception as e:
        error_message = {'message': f'Error setting up database: {str(e)}'}
        print(json.dumps(error_message)) 
        return jsonify(error_message)


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if current_db_config['type'] == 'mongodb':
        is_authenticated, user_info = auth.authenticate_user_mongodb(username, password, current_db_config['config'])
    else:
        is_authenticated, user_info = auth.authenticate_user_dynamodb(username, password, current_db_config['config'])

    if is_authenticated:
        user_session['email'] = username
        user_session['role'] = user_info['role']
        user_session['customer_id'] = user_info['customer_id'] 
        return jsonify({
            'status': 'success', 
            'message': 'Logged in successfully', 
            'role': user_info['role'] 
        })
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        if current_db_config['type'] == 'mongodb':
            if auth.check_user_exists_mongodb(email, current_db_config['config']):
                return jsonify({'status': 'error', 'message': 'User already exists. Please log in or use a different email.'})
            customer_id = auth.get_next_user_id_mongodb(current_db_config['config'])
        elif current_db_config['type'] == 'dynamodb':
            if auth.authenticate_user_dynamodb(email, current_db_config['config']):
                return jsonify({'status': 'error', 'message': 'User already exists. Please log in or use a different email.'})
            customer_id = auth.get_next_user_id_dynamodb('Users')

        user_session['email'] = email
        user_session['role'] = role
        user_session['customer_id'] = customer_id

        user_details = {
            'customer_id': customer_id,
            'email': email,
            'fname': request.form['first_name'],
            'lname': request.form['last_name'],
            'address': request.form['address'],
            'phone_number': request.form['phone_number'],
            'password': request.form['password'],
            'role': role
        }
        if current_db_config['type'] == 'mongodb':
            auth.add_user_to_mongodb(user_details, current_db_config['config'])
        elif current_db_config['type'] == 'dynamodb':
            auth.add_user_to_dynamodb(user_details, current_db_config['config'])

        return jsonify({'status': 'success', 'message': 'Sign up successful', 'role': request.form['role']})

    return jsonify({'status': 'error', 'message': 'Unable to sign up'})


@app.route('/user-info', methods=['GET'])
def user_info():
    if 'customer_id' not in user_session:
        return jsonify({'status': 'error', 'message': 'User not logged in or session expired'}), 401
    
    try:
        user = None
        if current_db_config['type'] == 'mongodb':
            client = MongoClient(current_db_config['config']['uri'])
            db = client[current_db_config['config']['db_name']]
            collection = db['users']
            user = collection.find_one({'customer_id': user_session['customer_id']})
            if user:
                user = serialize_mongo_documents(user) 
        elif current_db_config['type'] == 'dynamodb':
            dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
            table = dynamodb.Table("Users")
            response = table.get_item(Key={'customer_id': user_session['customer_id']})
            user = response.get('Item', {})

        if user:
            return jsonify({'status': 'success', 'user': user})
        else:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/update-user-info', methods=['POST'])
def update_user_info():
    user_updates = request.get_json()
    try:
        update_details = {
            'fname': user_updates.get('fname'),
            'lname': user_updates.get('lname'),
            'email': user_updates.get('email'),
            'address': user_updates.get('address'),
            'phone_number': user_updates.get('phone_number')
        }
        
        if current_db_config['type'] == 'mongodb':
            auth.update_user_mongodb(user_session['customer_id'], update_details, current_db_config['config'])
        elif current_db_config['type'] == 'dynamodb':
            auth.update_user_dynamodb(user_session['customer_id'], update_details, current_db_config['config'])
        
        return jsonify({'status': 'success', 'message': 'User updated successfully'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})



@app.route('/logout', methods=['GET'])
def logout():
    user_session.clear()
    return jsonify({'status': 'success', 'message': 'Logged out successfully'})
    
########################Seller Menu################################################################

@app.route('/get-products', methods=['GET'])
def get_products():
    products = []
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        collection = db['products']
        products = list(collection.find({'maker': user_session['customer_id']}))
        # Sort products by product_id
        products.sort(key=lambda x: x['product_id'])
        products = serialize_mongo_documents(products)
        print(f"Fetched {len(products)} products for customer ID {user_session['customer_id']} from MongoDB.")
    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        products_table = dynamodb.Table("Products")
        try:
            response = products_table.scan(
                FilterExpression=Attr('maker').eq(user_session['customer_id'])
            )
            products = response['Items']
            # Sort products by product_id after converting them to integers if they're stored as strings
            products.sort(key=lambda x: int(x['product_id']))
            print(f"Fetched {len(products)} products for customer ID {user_session['customer_id']} from DynamoDB.")
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

    return jsonify({'status': 'success', 'products': products})


@app.route('/add-product', methods=['POST'])
def add_product():
    product_data = request.get_json()
    try:
        if not product_data or 'name' not in product_data:
            return jsonify({'message': 'Missing product data'}), 400
        
        if current_db_config['type'] == 'mongodb':
            client = MongoClient(current_db_config['config']['uri'])
            db = client[current_db_config['config']['db_name']]
            collection = db['products']

            product_id = auth.get_next_product_id_mongodb(current_db_config['config'])

            product_details = {
                'product_id': product_id,
                'name': product_data['name'],
                'price': float(product_data['price']),
                'stock': int(product_data['stock']),
                'description': product_data['description'],
                'maker': int(user_session['customer_id']),  
                'rating': 5
            }
            collection.insert_one(product_details)
        elif current_db_config['type'] == 'dynamodb':
            dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
            table = dynamodb.Table("Products")
            product_id = auth.get_next_product_id_dynamodb('Products')
            product_details = {
                'product_id': str(product_id),
                'name': product_data['name'],
                'price': int(product_data['price']),
                'stock': int(product_data['stock']),
                'description': product_data['description'],
                'maker': str(user_session['customer_id']),  
                'rating': int('5') 
            }
            table.put_item(Item=product_details)
        return jsonify({'message': 'Product added successfully'})
    except Exception as e:
            return jsonify({'message': f'Error adding product: {str(e)}'}), 500


@app.route('/delete-product', methods=['POST'])
def delete_product():
    product_id = request.json.get('product_id')
    if not product_id:
        return jsonify({'status': 'error', 'message': 'Product ID is required'}), 400

    try:
        if current_db_config['type'] == 'mongodb':
            success = auth.delete_product_mongodb(product_id, current_db_config['config'])
            if not success:
                return jsonify({'status': 'error', 'message': 'Failed to delete product or product not found'}), 404
        elif current_db_config['type'] == 'dynamodb':
            success = auth.delete_product_dynamodb(str(product_id), current_db_config['config'])
            if not success:
                return jsonify({'status': 'error', 'message': 'Failed to delete product or product not found'}), 404
        else:
            return jsonify({'status': 'error', 'message': 'Invalid database type'}), 500

        return jsonify({'status': 'success', 'message': 'Product deleted successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/get-product-info/<product_id>', methods=['GET'])
def get_product_info(product_id):
    try:
        product = None
        if current_db_config['type'] == 'mongodb':
            client = MongoClient(current_db_config['config']['uri'])
            db = client[current_db_config['config']['db_name']]
            collection = db['products']
            product = collection.find_one({'product_id': int(product_id)})
            if product:
                product = serialize_mongo_documents(product)  # Serialize the MongoDB document
        elif current_db_config['type'] == 'dynamodb':
            dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
            table = dynamodb.Table("Products")
            response = table.get_item(Key={'product_id': str(product_id)})
            product = response.get('Item', {})
        if product:
            return jsonify({'status': 'success', 'product': product})
        else:
            return jsonify({'status': 'error', 'message': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

 
   
@app.route('/update-product', methods=['POST'])
def update_product():
    product_data = request.get_json()
    product_id = product_data.get('product_id')
    update_details = {
        'name': product_data.get('name') if (product_data.get('name')) else None,
        'price': product_data.get('price') if (product_data.get('price')) else None,
        'stock': product_data.get('stock') if (product_data.get('name')) else None,
        'description': product_data.get('description') if (product_data.get('description')) else None,
    }
    
    update_details = {k: v for k, v in update_details.items() if v is not None}

    if current_db_config['type'] == 'mongodb':
        auth.update_product_mongodb(int(product_id), update_details, current_db_config['config'])
        return jsonify({'status': 'success', 'message': 'Product updated successfully'})
    elif current_db_config['type'] == 'dynamodb':
        auth.update_product_dynamodb(str(product_id), update_details, current_db_config['config'])
        return jsonify({'status': 'success', 'message': 'Product updated successfully'})
    else: 
        return jsonify({'status': 'error', 'message': 'Failed on updating product'})

########################################################################################

# updated by linda 4.18 night

@app.route('/search-products', methods=['GET'])
def search_products():
    # Extract search term from the query string
    search_term = request.args.get('name', '')  # Defaults to empty string if not found

    # Perform product search and return results
    try:
        if not search_term:
            return jsonify({'status': 'error', 'message': 'No search term provided'})

        products = display_product(current_db_config, None, search_term)
        if products:
            response_data = [{
                'product_id': product.get('product_id', 'N/A'),
                'name': product.get('name', 'N/A'),
                'price': product.get('price', 'N/A'),
                'stock': product.get('stock', 'N/A'),
                'maker': product.get('maker', 'N/A'),
                'rating': product.get('rating', 'N/A'),
                'description': product.get('description', 'N/A')
            } for product in products]
            return jsonify({'status': 'success', 'products': response_data})
        else:
            return jsonify({'status': 'error', 'message': 'No products found'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        data = request.json
        product_id = data.get('product_id')
        name = data.get('name')
        quantity = data.get('quantity', 0)
        price = data.get('price')
        description = data.get('description')

        if not all([product_id, name, price, description]) or quantity <= 0:
            return jsonify({'message': 'Invalid product data or negative quantity.'}), 400

        if 'cart' not in user_session:
            user_session['cart'] = []
        # Simulated adding to a session cart (In production, you'd update a database or session store)
        cart_item = {
            'product_id': product_id,
            'name': name,
            'quantity': quantity,
            'price': price,
            'description': description
        }
        # Assuming user_session['cart'] exists and is a list
        user_session['cart'].append(cart_item)
        
        return jsonify({'message': 'Product added to cart successfully!'})

    except Exception as e:
        # Log actual error in production log system
        return jsonify({'message': str(e)}), 500


@app.route('/display_cart', methods=['GET'])
def display_cart():
    cart = user_session.get('cart', [])
    if not cart:
        return jsonify({'message': 'Your cart is empty.'})

    total = 0
    cart_items = []
    for item in cart:
        item_info = {
            'name': item['name'],
            'product_id': item['product_id'],
            'quantity': item['quantity'],
            'price_per_unit': item['price'],
            'description': item['description']
        }
        cart_items.append(item_info)
        total += int(item['quantity']) * float(item['price'])

    return jsonify({'cart_items': cart_items, 'total_price': total})

@app.route('/place_order', methods=['POST'])
def place_order():
    if not user_session['cart']:
        return jsonify({'success': False, 'message': 'Your cart is empty. Please add some products before placing an order.'})

    customer_id = user_session['customer_id']
    success = order_placer(current_db_config, customer_id, user_session['cart'])
    if success:
        user_session['cart'].clear()
        return jsonify({'success': True, 'message': 'Order placed successfully!'})
    else:
        return jsonify({'success': False, 'message': 'There was a problem placing your order. Please try again.'})


@app.route('/view_my_order', methods=['GET'])
def view_my_order():
    customer_id = user_session['customer_id']
    messages = search_display_orders(current_db_config, customer_id)
    if messages:
        return jsonify({'status': 'success', 'messages': messages})
    else:
        return jsonify({'status': 'error', 'message': 'No orders found'})


@app.route('/cancel_order', methods=['POST'])
def web_cancel_order():
    data = request.get_json()  # Make sure to use get_json() to properly parse the incoming JSON data
    customer_id = user_session['customer_id']  # Assuming user_session is correctly populated and managed
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'status': 'error', 'message': 'Order ID is required'}), 400

    result = cancel_order(current_db_config, customer_id, order_id)
    return jsonify(result)


#########################################################################################


if __name__ == '__main__':
    app.run(debug=True)
