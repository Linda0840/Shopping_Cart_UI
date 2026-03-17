import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output
import boto3
import pymongo
from pymongo import MongoClient

def cancel_order(current_db_config, customer_id, order_id):
    response_messages = []
    if current_db_config['type'] == 'mongodb':
        client = MongoClient(current_db_config['config']['uri'])
        db = client[current_db_config['config']['db_name']]
        orders_collection = db['orders']
        products_collection = db['products']

        order = orders_collection.find_one({'order_id': int(order_id)})
        if not order:
            return {'status': 'error', 'messages': ['Order not found.']}

        if order['customer_id'] != customer_id:
            return {'status': 'error', 'messages': ["This order does not belong to you."]}

        current_status = order.get('status', '')
        if current_status == 'cancelled':
            return {'status': 'error', 'messages': ["This order is already cancelled."]}
        elif current_status == 'placed':
            items = order['items']
            orders_collection.update_one({'order_id': int(order_id)}, {'$set': {'status': 'cancelled'}})
            response_messages.append("Order {} has been cancelled.".format(order_id))
            
            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']
                products_collection.update_one({'product_id': product_id}, {'$inc': {'stock': quantity}})
                response_messages.append(f"{quantity} unit(s) of product {product_id} added back to stock.")
        else:
            return {'status': 'error', 'messages': [f"This order cannot be cancelled as its status is {current_status}."]}

    elif current_db_config['type'] == 'dynamodb':
        dynamodb = boto3.resource('dynamodb', region_name=current_db_config['config']['region'])
        orders_table = dynamodb.Table('Orders')
        products_table = dynamodb.Table('Products')
        response = orders_table.get_item(Key={'order_id': str(order_id)})
        order = response.get('Item')
        
        if not order:
            return {'status': 'error', 'messages': ['Order not found.']}

        if order['customer_id'] != str(customer_id):
            return {'status': 'error', 'messages': ["This order does not belong to you."]}

        current_status = order['status']
        if current_status == 'cancelled':
            return {'status': 'error', 'messages': ["This order is already cancelled."]}
        elif current_status == 'placed':
            orders_table.update_item(
                Key={'order_id': str(order_id)},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'cancelled'}
            )
            response_messages.append(f"Order {order_id} has been cancelled.")
            for item in order['items']:
                product_id = item['product_id']
                quantity = item['quantity']
                products_table.update_item(
                    Key={'product_id': str(product_id)},
                    UpdateExpression='ADD stock :qty',
                    ExpressionAttributeValues={':qty': quantity}
                )
                response_messages.append(f"{quantity} unit(s) of product {product_id} added back to stock.")
        else:
            return {'status': 'error', 'messages': [f"This order cannot be cancelled as its status is {current_status}."]}

    return {'status': 'success', 'messages': response_messages}
