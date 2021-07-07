import json
import os
import boto3
import os
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    
    
    connection_id = event["requestContext"].get("connectionId")   # Get connection-ID per client .
    data_base = boto3.resource('dynamodb')                        # create connection with the database.
    table = data_base.Table('Users')                             # connect with the table
    
    client_id = event['queryStringParameters']['id']              # Get client id from the connection request.
    client_name = event['queryStringParameters']['name']          # Get client name from the connection request.
    
    
    
    users_map = table.get_item(Key={'field':'users'})['Item']['users']            # Get the users on current table.
    
    logger.info(users_map)  
    
    # # Add the new player to the table.
    if not client_id in users_map:
        # Choose the data for player.
        client_info = {
                        'balance':1000,
                        'connection_id': connection_id,
                        'name': client_name
                      }
        # Update users_map (this map is copied from database byvalue).            
        users_map[client_id] = client_info
              
        
    else: 
        client_info = users_map[client_id]
        balance = client_info["balance"]
        name = client_info["name"]
        client_info = {
                        'balance': balance,
                        'connection_id': connection_id,
                        'name': name
                      }
        users_map[client_id] = client_info
        
    # Update the database.
    table.update_item(Key={'field':'users'},
                                ExpressionAttributeNames={'#u': 'users'},
                                UpdateExpression="set #u = :u_map",
                                ExpressionAttributeValues={':u_map': users_map}
                         )
    
    response = "Connected successfully to server!"
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
