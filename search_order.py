import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import pymongo
from pymongo import MongoClient
import boto3
from boto3.dynamodb.conditions import Attr


def search_display_orders(current_db_config, customer_id):
    messages = []
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        orders_collection = db['orders']
        products_collection = db['products']
        orders = list(orders_collection.find({'customer_id': customer_id}))

        if not orders:
            messages.append("No orders found for the specified customer.")
            return messages
        
        for order in orders:
            order_info = [
                f"Order ID: {order['order_id']}",
                f"Date: {order['date']}",
                f"Total Price: ${order['total_price']:.2f}",
                f"Status: {order['status']}"
            ]
            items_info = []
            for item in order['items']:
                product_id = item['product_id']
                product_info = products_collection.find_one({'product_id': product_id})
                if product_info:
                    item_description = f"- Product Name: {product_info.get('name')}, Quantity: {item['quantity']}"
                else:
                    item_description = f"- Product ID {product_id} not found"
                items_info.append(item_description)

            messages.append({'order_info': order_info, 'items_info': items_info})

    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        orders_table = dynamodb.Table('Orders')
        products_table = dynamodb.Table('Products')
        response = orders_table.scan(
            FilterExpression=Attr('customer_id').eq(str(customer_id))
        )
        orders = response.get('Items', [])

        if not orders:
            return [{'order_info': ["No orders found for the specified customer."]}]

        for order in sorted(orders, key=lambda x: int(x['order_id'])):
            order_info = [
                f"Order ID: {order['order_id']}",
                f"Date: {order['date']}",
                f"Total Price: ${order['total_price']}",
                f"Status: {order['status']}"
            ]
            items_info = []
            for item in order['items']:
                product_response = products_table.get_item(
                    Key={'product_id': str(item['product_id'])}
                )
                product_info = product_response.get('Item')
                item_description = f"- Product Name: {product_info.get('name')}, Quantity: {item['quantity']}"
                items_info.append(item_description)
            messages.append({'order_info': order_info, 'items_info': items_info})
    
    return messages