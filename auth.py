import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import NoCredentialsError
from pymongo import MongoClient
import decimal
from decimal import Decimal

def authenticate_user_dynamodb(username, password, db_config):
    dynamodb = boto3.resource('dynamodb', region_name=db_config['region'])
    if dynamodb:
        table = dynamodb.Table('Users')
        try:

            response = table.scan(
                FilterExpression="email = :email",
                ExpressionAttributeValues={
                    ':email': username
                }
            )
            if response['Items']:
                user = response['Items'][0]  # the first match should be the only match
                if user['password'] == password:
                    return True, user 
                else:
                    print("Invalid password. Please try again!")
                    return False, None
            else:
                print("User not found. Please try again!")
                return False, None
        except Exception as e:
            print("Error querying Users table:", e)

def authenticate_user_mongodb(username, password, db_config):
    client = MongoClient(db_config['uri'])
    if client:
        db = client[db_config['db_name']]  
        users_collection = db['users']

        try:
            user = users_collection.find_one({"email": username})

            if user:
                if user['password'] == password:
                    return True, user
                else:
                    print("Invalid password. Please try again!")
                    return False, None
            else:
                print("User not found. Please try again!")
                return False, None
        except pymongo.errors.PyMongoError as e:
            print("Error querying Users collection:", e)
            return False, None
    else:
        return False, None
    
def check_user_exists_mongodb(email, db_config):
    client = MongoClient(db_config['uri'])
    db = client[db_config['db_name']]
    collection = db['users']
    user_count = collection.count_documents({'email': email})
    return user_count > 0

def check_user_exists_dynamodb(email, db_config):
    dynamodb = boto3.resource('dynamodb', region_name=db_config['region'])
    table = dynamodb.Table('Users')
    response = table.scan(
        FilterExpression='#email = :email',
        ExpressionAttributeNames={'#email': 'email'},  # Use # to avoid reserved word conflicts
        ExpressionAttributeValues={':email': email}  # Bind the email value safely
    )
    users = response.get('Items', [])

    if not users: 
        return False 
    else: # user exists
        return True 

def add_user_to_mongodb(user_details, config):
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    users = db['users']

    result = users.insert_one(user_details)
    print(f"User added to MongoDB with ID: {user_details['customer_id']}")

def add_user_to_dynamodb(user_details, config):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('Users')
    
    response = table.put_item(Item=user_details)
    
    print(f"User added to DynamoDB with ID: {user_details['customer_id']}")
    
def get_next_user_id_dynamodb(table_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)

    # Scan the table to get all customer_ids
    try:
        response = table.scan(
            ProjectionExpression="customer_id"
        )
        items = response['Items']

        # Find the maximum customer_id
        max_customer_id = max(int(item['customer_id']) for item in items) if items else 0
        next_customer_id = max_customer_id + 1
        return str(next_customer_id)
    
    except Exception as e:
        print("Failed to fetch customer IDs:", e)
        return None

def get_next_product_id_mongodb(db_config):
    client = MongoClient(db_config['uri'])
    db = client[db_config['db_name']]
    products_collection = db['products']

    # Find the last order in the collection
    last_product = products_collection.find().sort([('product_id', -1)]).limit(1)

    if last_product:
        next_product_id = last_product[0]['product_id'] + 1         
    else:
        next_product_id = 0

    return next_product_id

def get_next_user_id_mongodb(db_config):
    client = MongoClient(db_config['uri'])
    db = client[db_config['db_name']]
    users_collection = db['users']

    # Find the last order in the collection
    last_user = users_collection.find().sort([('customer_id', -1)]).limit(1)

    if last_user:
        next_user_id = last_user[0]['customer_id'] + 1         
    else:
        next_user_id = 0

    return next_user_id

def add_product_to_mongodb(product_details, config):
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    users = db[config['products']]

    result = users.insert_one(product_details)
    print(f"User added to MongoDB with ID: {product_details['product_id']}")

def add_product_to_dynamodb(product_details, config):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table('Products')
    
    response = table.put_item(Item=product_details)
    
    print(f"User added to DynamoDB with ID: {product_details['product_id']}")

def get_next_product_id_dynamodb(table_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    table = dynamodb.Table(table_name)

    try:
        response = table.scan(
            ProjectionExpression="product_id"
        )
        items = response['Items']

        max_product_id = max(int(item['product_id']) for item in items) if items else 0
        next_product_id = max_product_id + 1
        return next_product_id
    
    except Exception as e:
        print("Failed to fetch product IDs:", e)
        return None

def delete_product_mongodb(product_id, config):
    try:
        client = MongoClient(config['uri'])
        db = client[config['db_name']]
        collection = db['products'] 
        
        result = collection.delete_one({'product_id': int(product_id)}) 
        if result.deleted_count > 0:
            print(f"Product with ID {product_id} deleted successfully from MongoDB.")
            return True
        else:
            print(f"No product found with ID {product_id} in MongoDB.")
            return False
    except Exception as e:
        print(f"Failed to delete product from MongoDB: {e}")
        return False

    
def delete_product_dynamodb(product_id, config):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config['region'])
        table = dynamodb.Table('Products')
        
        key_response = table.get_item(Key={'product_id': product_id})
        product = key_response.get('Item')
        
        if not product:
            print(f"No product found with ID {product_id}. Nothing to delete.")
            return
        
        delete_response = table.delete_item(
            Key={
                'product_id': product_id
            }
        )
        # Check the response to confirm deletion
        if delete_response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
            print(f"Product with ID {product_id} deleted successfully from DynamoDB.")
            return True
        else:
            print(f"Failed to delete product from DynamoDB: {delete_response}")
            return False
    except Exception as e:
        print(f"Error deleting product from DynamoDB: {e}")
        return False

def update_product_mongodb(product_id, update_details, config):
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    collection = db['products']
    
    # Prepare the update document
    update_doc = {k: v for k, v in update_details.items() if v}  

    if update_doc:
        result = collection.update_one({'product_id': product_id}, {'$set': update_doc})
        if result.modified_count > 0:
            print(f"Product with ID {product_id} updated successfully in MongoDB.")
        else:
            print(f"No changes made to the product with ID {product_id}.")
    else:
        print("No valid data provided for update.")
    
def update_product_dynamodb(product_id, update_details, config):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config['region'])
        table = dynamodb.Table('Products')
        
        # Construct the update expression dynamically
        update_expression = "set "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Map each attribute to a placeholder to avoid reserved keyword conflicts
        first = True
        for key, val in update_details.items():
            if val:  # Only update if there is a value
                if not first:
                    update_expression += ", "
                # Use placeholders for attribute names to avoid conflicts with reserved keywords
                placeholder = f"#{key}"
                expression_attribute_names[placeholder] = key
                expression_attribute_values[f":{key}"] = val if key != "price" else int(str(val))
                update_expression += f"{placeholder} = :{key}"
                first = False

        # Make the update call
        if expression_attribute_values:
            response = table.update_item(
                Key={'product_id': product_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )
            # Check the response to confirm update
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                print(f"Product with ID {product_id} updated successfully in DynamoDB.")
            else:
                print(f"Failed to update product in DynamoDB: {response}")
    except Exception as e:
        print(f"Error updating product in DynamoDB: {e}")

def update_user_mongodb(customer_id, update_details, config):
    client = MongoClient(config['uri'])
    db = client[config['db_name']]
    collection = db['users']
    
    # Prepare the update document
    update_doc = {k: v for k, v in update_details.items() if v}  # Exclude null or empty values

    if update_doc:
        result = collection.update_one({'customer_id': customer_id}, {'$set': update_doc})
        if result.modified_count > 0:
            print(f"User with ID {customer_id} updated successfully in MongoDB.")
        else:
            print(f"No changes made to the user with ID {customer_id}.")
    else:
        print("No valid data provided for update.")

def update_user_dynamodb(customer_id, update_details, config):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=config['region'])
        table = dynamodb.Table('Users')
        
        update_expression = "set "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Map each attribute to a placeholder to avoid reserved keyword conflicts
        first = True
        for key, val in update_details.items():
            if val: 
                if not first:
                    update_expression += ", "
                placeholder = f"#{key}"
                expression_attribute_names[placeholder] = key
                expression_attribute_values[f":{key}"] = val if key != "price" else decimal.Decimal(str(val))
                update_expression += f"{placeholder} = :{key}"
                first = False

        if expression_attribute_values:
            response = table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="UPDATED_NEW"
            )
            # Check the response to confirm update
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                print(f"Customer with ID {customer_id} updated successfully in DynamoDB.")
            else:
                print(f"Failed to update user in DynamoDB: {response}")
    except Exception as e:
        print(f"Error updating user in DynamoDB: {e}")
                
def create_session(user):
    print(f"Session created for {user}")
    return True

def end_session(user):
    print(f"Session ended for {user}")
    return True
