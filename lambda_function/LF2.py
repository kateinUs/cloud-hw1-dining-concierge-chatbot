import json
import boto3
import random
from opensearchpy import OpenSearch, RequestsHttpConnection
from boto3.dynamodb.conditions import Key
import os
import logging
import traceback
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Setting values to be referenced later in the program
port = 443
ssl = True
certs = True
service = "es"
region = 'us-east-1'
# open search username and pwd
username = "huiminzhang"
password = "[OPEN_SEARCH_PASSWORD]"
dynamodbTable = 'yelp-restaurants'
email_id = "hz2466@nyu.edu"
# open search host
host = "search-search-yelp-kl4detfhabfrbcdqltkinliak4.us-east-1.es.amazonaws.com"
sns_queue = "https://sqs.us-east-1.amazonaws.com/987428913671/diningsqs"


# Function to receive message from SQS queue
def get_sqsQueueMessage():
    sqs = boto3.client('sqs')
    sqs_message = sqs.receive_message(
        QueueUrl=sns_queue,
        MaxNumberOfMessages=10,
        MessageAttributeNames=['All'],
        AttributeNames=['All'],
        VisibilityTimeout=10,
        WaitTimeSeconds=20
    )
    logger.info(sqs_message)
    message = sqs_message['Messages'][0]

    return sqs, message


# Function to retrieve slots from SQS queue message
def get_slots(message):
    cuisine = message['MessageAttributes'].get('cuisineType').get('StringValue')
    location = message['MessageAttributes'].get('location').get('StringValue')
    dining_date = message['MessageAttributes'].get('diningDate').get('StringValue')
    dining_time = message['MessageAttributes'].get('diningTime').get('StringValue')
    people = message['MessageAttributes'].get('numOfPeople').get('StringValue')
    email_ads = message['MessageAttributes'].get('emailAddress').get('StringValue')
    phone_number = message['MessageAttributes'].get('phoneNumber').get('StringValue')

    return cuisine, location, dining_date, dining_time, people, email_ads, phone_number


# Function to establish OpenSearch connection
def connect_openSearch():
    os = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_auth=(username, password),
        use_ssl=ssl,
        verify_certs=certs,
        connection_class=RequestsHttpConnection
    )
    return os


# Function to perform OpenSearch query using index: restaurants and filter based on cuisines
def get_id(os, cuisine):
    response = os.search(
        index="restaurants",
        body={"query": {"match": {"cuisine": cuisine}}}
    )

    id_list = []
    logger.info(f"OPEN SEARCH RESP: {response}")
    for item in response['hits']['hits']:
        id_list.append(item["_id"])

    suggestion_id_list = random.sample(id_list, 3)
    return suggestion_id_list


# Function to connect to DynamoDB Table
def connect_dynamoDBTable():
    db = boto3.resource('dynamodb')
    table = db.Table(dynamodbTable)
    return table


#  Function to fetch three random restaurants details of a particular cuisine from OpenSearch result
def get_restaurant(table, suggestion_id_list):
    restaurant_list = []
    for suggestion_id in suggestion_id_list:
        restaurant_dict = {}
        resp = table.query(KeyConditionExpression=Key('id').eq(suggestion_id))
        if resp.get('Items', None) is None:
            continue
        restaurant_details = resp['Items'][0]
        restaurant_dict["name"] = restaurant_details["name"]
        restaurant_dict["rating"] = restaurant_details["rating"]
        restaurant_dict["address"] = restaurant_details["address"]
        restaurant_dict["review_count"] = restaurant_details["review_count"]
        restaurant_list.append(restaurant_dict)
    return restaurant_list


#  Function to provide template from sending message by email
def get_message(restaurant_list, cuisine, location, date, dining_time, people, email, phone):
    email_message = "Here are a few {} cuisine recommendations in {} for {} people, on {} at {}. ".format(cuisine,
                                                                                                          location,
                                                                                                          people, date,
                                                                                                          dining_time)
    i=1
    for restaurant_dict in restaurant_list:
        email_message = email_message + "RESTAURANT {}: {}. It has {} reviews with an average {} rating. The address is: {}.".format(
            i, restaurant_dict['name'], restaurant_dict['review_count'], restaurant_dict['rating'],
            restaurant_dict['address'])
        i += 1

    email_message = email_message + "Your recommendations was sent to: {}. Your phone number is: {}. Enjoy your meal!".format(email, phone)
    return email_message


#  Function that uses SES to send emails for recommendations
def send_email(email, email_message):
    ses = boto3.client('ses')

    response = ses.send_email(
        Source=email_id,
        Destination={
            'ToAddresses': [email]
        },
        ReplyToAddresses=[email_id],
        Message={
            'Subject': {
                'Data': 'Dining Conceirge Recommendations',
                'Charset': 'utf-8'
            },
            'Body': {
                'Text': {
                    'Data': email_message,
                    'Charset': 'utf-8'
                },
                'Html': {
                    'Data': email_message,
                    'Charset': 'utf-8'
                }
            }
        }
    )


#  Function to delete message from SQS queue
def delete_SQSEntry(sqs, sns_queue, message):
    receipt_handle = message['ReceiptHandle']
    sqs.delete_message(
        QueueUrl=sns_queue,
        ReceiptHandle=receipt_handle
    )
    logger.info("1 MSG DELETED FROM SQS")


#  Main lambda function that retrieves message from SQS and performs OpenSearch to fetch restaurant recommendations
def lambda_handler(event, context):
    try:
        sqs, message = get_sqsQueueMessage()
        logger.info(f"GET MESSAGE: {message}")

        cuisine, location, date, dining_time, people, email, phone = get_slots(message)

        os = connect_openSearch()
        suggestion_id_list = get_id(os, cuisine)
        logger.info(f"SUGGESTION ID READY: {suggestion_id_list}")
        table = connect_dynamoDBTable()
        restaurant_list = get_restaurant(table, suggestion_id_list)
        logger.info(f"SUGGESTION RESTAURANTS READY: {restaurant_list}")
        logger.info("START TO SEND EMAIL")
        email_message = get_message(restaurant_list, cuisine, location, date, dining_time, people, email, phone)
        logger.info(f"EMAIL CONTENT: {email_message}")
        send_email(email, email_message)
        logger.info("DONE WITH SENDING EMAIL")

        delete_SQSEntry(sqs, sns_queue, message)

        return {
            'statusCode': 200,
            'body': email_message
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        raise
        return {
            'statusCode': 500,
            'body': 'Internal server error'
        }
