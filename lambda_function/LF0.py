import json
import boto3


def lambda_handler(event, context):
    print(event)
    try:
        print(type(event))
        print(event)
        client = boto3.client('lex-runtime')
        body = json.loads(event.get('body'))
        text = (body.get('messages')[0].get('unstructured').get('text'))
        print("text is", text)

        response = client.post_text(botName='DiningConcierge', botAlias='dc_chatbot', userId="id", inputText=text)
        print(response.get("message"))
        message_string = {
            'messages': [{'type': 'unstructured', 'unstructured': {'text': response.get('message')}}]
        }
        return {
            "statusCode": 200,
            "headers":
                {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET",

                },

            "body": json.dumps(message_string)
        }
    except:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
            },
            "body": "Internal server error"
        }
