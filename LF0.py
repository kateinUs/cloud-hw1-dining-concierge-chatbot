import json

def lambda_handler(event, context):
    message_string = {
        "messages" : [
            {
                "type": "unstructured",
                "unstructured": {
                    "id": "1",
                    "text": "Application under development. Search functionality will be implemented in Assignment 2",
                    "timestamp": "1"
                }
            }
        ]
    }
    return {
        "statusCode": 200,
            "headers": 
            { "Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET" 
                
            },
        
        "body":json.dumps(message_string)
    }