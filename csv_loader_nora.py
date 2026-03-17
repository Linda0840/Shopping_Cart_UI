from flask import Flask, jsonify, request
import pandas as pd
import pymongo
from pymongo import MongoClient
import boto3
import decimal
from botocore.exceptions import NoCredentialsError, ClientError
import json

app = Flask(__name__)

def parse_items(item_string):
    # Convert the JSON-formatted string into a Python list of dictionaries
    return json.loads(item_string)

def delete_table(dynamodb, table_name):
    messages = []
    try:
        table = dynamodb.Table(table_name)
        table.delete()
        table.wait_until_not_exists()
        messages.append(f"Deleted table: {table_name}")
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        messages.append(f"Table {table_name} not found, no need to delete.")
    return messages

def create_tables_if_not_exist(dynamodb, tables_info):
    messages = []
    existing_tables = dynamodb.meta.client.list_tables()['TableNames']

    for table_name, info in tables_info.items():
        if table_name not in existing_tables:
            messages.append(f"Creating table {table_name}...")
            messages.extend(create_table(dynamodb, table_name, info['schema']['KeySchema'], info['schema']['AttributeDefinitions'], info['schema']['throughput']))
        else:
            messages.append(f"Table {table_name} already exists.")
            messages.extend(delete_table(dynamodb, table_name))
            messages.extend(create_table(dynamodb, table_name, info['schema']['KeySchema'], info['schema']['AttributeDefinitions'], info['schema']['throughput']))
    return messages

def create_table(dynamodb, table_name, key_schema, attribute_definitions, throughput):
    messages = []
    try:
        # Creating the DynamoDB Table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput=throughput
        )
        # Wait until the table exists, this function polls the table status
        table.wait_until_exists()
        messages.append(f"Table {table_name} created successfully.")
    except Exception as e:
        messages.append(f"Failed to create table {table_name}: {str(e)}")
    return messages
        

@app.route('/load-data', methods=['POST'])
def load_data():
    db_type = request.json['db_type']
    db_config = request.json['db_config']  # Make sure to pass db_config correctly
    messages = load_csv_to_database(db_type, db_config)
    return jsonify({'success': True, 'messages': messages})

def load_csv_to_database(db_type, db_config):
    messages = []

    data1 = pd.read_csv("Product_info.csv")
    data2 = pd.read_csv("User_info.csv")
    data3 = pd.read_csv("Order_info.csv")

    if db_type == 'mongodb':
        client = MongoClient(db_config['uri'])
        db = client[db_config['db_name']]
        
        products_collection = db['products']
        products_list = data1.to_dict(orient='records')
        
        for product in products_list:
            product['product_id'] = int(product['product_id'])
            product['price'] = float(product['price'])
            product['stock'] = int(product['stock'])
            product['rating'] = float(product['rating'])
        
        products_collection.delete_many({})  
        result = products_collection.insert_many(products_list)
        messages.append(f"Inserted {len(result.inserted_ids)} products into MongoDB")

        users_collection = db['users']
        users_list = data2.to_dict(orient='records')

        for user in users_list:
            user['customer_id'] = int(user['customer_id'])

        users_collection.delete_many({})
        result = users_collection.insert_many(users_list)
        messages.append(f"Inserted {len(result.inserted_ids)} users into MongoDB")


        orders_collection = db['orders']
        data3['order_id'] = data3['order_id'].astype(int)
        data3['customer_id'] = data3['customer_id'].astype(int)
        data3['total_price'] = data3['total_price'].astype(float)
        data3['items'] = data3['items'].apply(parse_items)
        
        orders_data = data3.to_dict('records')
        orders_collection.delete_many({})
        result = orders_collection.insert_many(orders_data)
        messages.append(f"Inserted {len(result.inserted_ids)} orders into MongoDB")


    elif db_type == 'dynamodb':
        try:
            dynamodb = boto3.resource('dynamodb', region_name=db_config['region'])
            tables_info = {
                'Products': {
                    'data': data1,
                    'schema': {
                        'KeySchema': [{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
                        'AttributeDefinitions': [{'AttributeName': 'product_id', 'AttributeType': 'S'}],
                        'throughput': {'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
                    }
                },
                'Users': {
                    'data': data2,
                    'schema': {
                        'KeySchema': [{'AttributeName': 'customer_id', 'KeyType': 'HASH'}],
                        'AttributeDefinitions': [{'AttributeName': 'customer_id', 'AttributeType': 'S'}],
                        'throughput': {'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
                    }
                },
                'Orders': {
                    'data': data3,
                    'schema': {
                        'KeySchema': [{'AttributeName': 'order_id', 'KeyType': 'HASH'}],
                        'AttributeDefinitions': [{'AttributeName': 'order_id', 'AttributeType': 'S'}],
                        'throughput': {'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
                    }
                }
            }

            messages.extend(create_tables_if_not_exist(dynamodb, tables_info))
            
            table1 = dynamodb.Table("Products")
            table2 = dynamodb.Table("Users")
            table3 = dynamodb.Table("Orders")
            
            for index, row in data1.iterrows():
                item = {
                    'product_id': str(row['product_id']),
                    'name': row['name'],
                    'price': int(row['price']),
                    'stock': int(row['stock']),
                    'maker': str(row['maker']),
                    'rating': int(row['rating']),
                    'description': row['description']
                }
                table1.put_item(Item=item)
            messages.append("Successfully loaded items into DynamoDB table Products.")

            for index, row in data2.iterrows():
                item = {
                    'customer_id': str(row['customer_id']),
                    'fname': row['fname'],
                    'lname': row['lname'],
                    'email': row['email'],
                    'address': row['address'],
                    'phone_number': row['phone_number'],
                    'password': row['password'],
                    'role': row['role']
                }
                table2.put_item(Item=item)
            messages.append("Successfully loaded items into DynamoDB table Users.")

            for index, row in data3.iterrows():
                item = {
                    'order_id': str(row['order_id']),
                    'date': row['date'],
                    'items': json.loads(row['items'].replace("'", '"')),
                    'total_price': int(row['total_price']),
                    'status': row['status'],
                    'customer_id': str(row['customer_id'])
                }
                table3.put_item(Item=item)
            messages.append("Successfully loaded items into DynamoDB table Orders.")
            messages.append("You can now Login/Signup!")

        except NoCredentialsError as e:
            messages.append(f"No credentials provided for AWS DynamoDB: {str(e)}")
        except Exception as e:
            messages.append(f"An error occurred: {str(e)}")
    return messages
