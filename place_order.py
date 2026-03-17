import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import boto3
import pymongo
from pymongo import MongoClient
import re
from boto3.dynamodb.conditions import Attr


def display_product(current_db_config, output, search_term=None):
    products_list = []
    
    if search_term is None:
        return 
        
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        products_collection = db['products']
        
        regex_pattern = re.compile(search_term, re.IGNORECASE)

        # Search for products by name in the database
        products = list(products_collection.find({"name": {"$regex": regex_pattern}}, {'_id': 0}))
        
    
    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        products_table = dynamodb.Table('Products')

        response = products_table.scan(
            FilterExpression=Attr('name').contains(search_term)
        )
        products = response.get('Items', [])

    for product in products:
        products_list.append({
            'product_id': product.get('product_id', 'N/A'),
            'name': product.get('name', 'N/A'),
            'price': product.get('price', 'N/A'),
            'stock': product.get('stock', 'N/A'),
            'maker': product.get('maker', 'N/A'),
            'rating': product.get('rating', 'N/A'),
            'description': product.get('description', 'N/A')
        })

    return products_list

def get_next_order_id(current_db_config):
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        orders_collection = db['orders']

        # Find the last order in the collection
        last_order = orders_collection.find().sort([('order_id', -1)]).limit(1)

        if last_order:
            next_order_id = last_order[0]['order_id'] + 1              ### 
        else:
            # If there are no orders yet, start from order_id 0
            next_order_id = 0

    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        orders_table = dynamodb.Table('Orders')     # previous orders_dy
        
        # Query the orders table to find the last order ID
        response = orders_table.scan(
            ProjectionExpression="order_id",
        )
        items = response['Items']

        max_order_id = max(int(item['order_id']) for item in items) if items else 0
        next_order_id = max_order_id + 1

    return next_order_id


def order_placer(current_db_config, customer_id, items):
    success = False
    
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        orders_collection = db['orders']
        products_collection = db['products']

        purchased_items = []
        total_price = 0

        for item in items:
            product_info = products_collection.find_one({'product_id': item['product_id']})
            if product_info:
                requested_quantity = item['quantity']
                if product_info['stock'] >= requested_quantity:
                    total_price += requested_quantity * product_info['price']
                    products_collection.update_one({'product_id': item['product_id']}, {'$inc': {'stock': -requested_quantity}})
                    purchased_items.append({'product_id': item['product_id'], 'quantity': requested_quantity})

        if purchased_items:  # Proceed if there are items to order
            order = {
                'order_id': get_next_order_id(current_db_config),
                'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'items': purchased_items,
                'total_price': total_price,
                'status': 'placed',
                'customer_id': customer_id
            }
            orders_collection.insert_one(order)
            success = True

    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        orders_table = dynamodb.Table('Orders')
        products_table = dynamodb.Table('Products')

        purchased_items = []
        total_price = 0

        for item in items:
            response = products_table.get_item(Key={'product_id': str(item['product_id'])})
            product_info = response.get('Item')

            if product_info and int(product_info['stock']) >= item['quantity']:
                requested_quantity = item['quantity']
                total_price += requested_quantity * (product_info['price'])
                products_table.update_item(
                    Key={'product_id': str(item['product_id'])},
                    UpdateExpression="SET stock = stock - :qty",
                    ExpressionAttributeValues={":qty": requested_quantity}
                )
                purchased_items.append({'product_id': str(item['product_id']), 'quantity': requested_quantity})

        if purchased_items:
            order_id = get_next_order_id(current_db_config)
            order = {
                'order_id': str(order_id),
                'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'items': purchased_items,
                'total_price': int(total_price),
                'status': 'placed',
                'customer_id': str(customer_id)
            }
            orders_table.put_item(Item=order)
            success = True

    return success