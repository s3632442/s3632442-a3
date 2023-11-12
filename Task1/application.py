import uuid
import hashlib
from flask import Flask, render_template
import boto3
import requests
from botocore.exceptions import NoCredentialsError
import time
from datetime import datetime

app = Flask(__name__)


test_user='example_user'
test_password='example_password'
login_credentials_table_name = 'login-credentials'
approved_images_table_name = 'approved-vehicles'
approved_images_bucket_name = "approved-vehicle-images-3632442"
initial_image_url = "https://www.linearity.io/blog/content/images/2023/06/how-to-create-a-car-NewBlogCover.png"

def does_table_exist(table_name):
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    # Check if the table exists
    try:
        dynamodb.describe_table(TableName=table_name)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        return False

def wait_for_table_creation(table_name):
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    while True:
        try:
            # Check the table status
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']

            # If the status is 'ACTIVE', break out of the loop
            if status == 'ACTIVE':
                break
        except dynamodb.exceptions.ResourceNotFoundException:
            pass  # Table not found, continue waiting

        # Sleep for a short duration before checking again
        time.sleep(5)

def does_bucket_exist(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except Exception as e:
        return False

def does_object_exist(bucket_name, object_key):
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except Exception as e:
        return False

def add_approved_vehicle_image(username, filename, image_url):
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    # Specify the table name
    table_name = 'approved-vehicles'

    try:
        # Get the DynamoDB table
        table = dynamodb.Table(table_name)

        # Generate a UUID as the image_id
        image_id = str(uuid.uuid4())

        # Insert the item into the table
        response = table.put_item(
            Item={
                'image_id': image_id,
                'username': username,
                'image_filename': filename,
                'image_url': image_url
            }
        )

        print(f"Item added to '{table_name}' table: {response}")

    except Exception as e:
        print(f"Error adding item to '{table_name}' table: {e}")


def create_s3_bucket_and_upload_image(bucket_name, initial_image_url, test_user):
    s3 = boto3.client('s3')

    # Check if the bucket exists
    if not does_bucket_exist(bucket_name):
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"S3 bucket '{bucket_name}' created successfully.")
        except Exception as e:
            print(f"Error creating S3 bucket: {e}")
            return

    # Generate a unique filename using the current UTC time (including milliseconds)
    current_time = datetime.utcnow()
    object_key = f"image_{current_time.strftime('%Y%m%d%H%M%S%f')}.png"

    # Check if the object (image) already exists in the S3 bucket
    if not does_object_exist(bucket_name, object_key):
        try:
            response = requests.get(initial_image_url)
            if response.status_code == 200:
                s3.put_object(Body=response.content, Bucket=bucket_name, Key=object_key)
                print(f"Image uploaded to S3 bucket '{bucket_name}' with key '{object_key}'.")

                # Get the URL of the uploaded image
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

                # Add the approved vehicle image using the obtained URL
                add_approved_vehicle_image(test_user, object_key, s3_url)
            else:
                print(f"Failed to download the image from {initial_image_url}. Status code: {response.status_code}")
        except NoCredentialsError:
            print("Credentials not available. Unable to upload the image to S3.")
        except Exception as e:
            print(f"Error uploading image to S3: {e}")

def list_objects_in_bucket(bucket_name):
    # Create an S3 client
    s3 = boto3.client('s3')

    # List objects in the S3 bucket
    try:
        response = s3.list_objects(Bucket=bucket_name)
        objects = response.get('Contents', [])

        # Ensure 'image_id' and 'image_filename' are present for each object
        for obj in objects:
            obj['image_id'] = obj.get('image_id', '')  # Set a default value if it doesn't exist
            obj['image_filename'] = obj.get('image_filename', '')  # Set a default value if it doesn't exist

        return objects
    except Exception as e:
        print(f"Error listing objects in S3 bucket: {e}")
        return []

@app.route("/")
def index():
    # List all objects in the S3 bucket
    objects = list_objects_in_bucket("approved-vehicle-images-3632442")

    # Generate full URLs for each image
    base_url = f"https://approved-vehicle-images-3632442.s3.amazonaws.com/"
    for obj in objects:
        obj['full_url'] = f"{base_url}{obj['Key']}"
        print(f"Image ID: {obj['image_id']}, Filename: {obj['image_filename']}, URL: {obj['full_url']}")

    # Render the HTML template and pass variables to it
    return render_template("index.html", uploaded_images=objects)

@app.route("/upload", methods=["POST"])
def upload():
    # Handle the file upload logic here
    # You can access the uploaded file using request.files['file']
    # Implement the logic to upload the file to S3 and update the HTML accordingly

    return "Upload action will be implemented here"

def create_vehicle_id_table(table_name):
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    # Table doesn't exist, create it
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'image_filename',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'username',
                    'KeyType': 'RANGE'  # Sort key
                }
                # Add more key schema if needed
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'image_filename',
                    'AttributeType': 'S'  # Assuming 'S' for string, adjust as needed
                },
                {
                    'AttributeName': 'username',
                    'AttributeType': 'S'  # Assuming 'S' for string, adjust as needed
                }
                # Add more attribute definitions if needed
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,  # Adjust based on your needs
                'WriteCapacityUnits': 5  # Adjust based on your needs
            }
        )
        print(f"DynamoDB table '{table_name}' created successfully. Status: {response['TableDescription']['TableStatus']}")
    except Exception as e:
        print(f"Error creating DynamoDB table: {e}")


def create_login_credentials_table(table_name):
    # Create a DynamoDB client
    dynamodb = boto3.client('dynamodb')

    # Table doesn't exist, create it
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'username',
                    'KeyType': 'HASH'  # Partition key
                }
                # Add more key schema if needed
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'username',
                    'AttributeType': 'S'  # Assuming 'S' for string, adjust as needed
                }
                # Add more attribute definitions if needed
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,  # Adjust based on your needs
                'WriteCapacityUnits': 5  # Adjust based on your needs
            }
        )
        print(f"DynamoDB table '{table_name}' created successfully. Status: {response['TableDescription']['TableStatus']}")
    except Exception as e:
        print(f"Error creating DynamoDB table: {e}")

def hash_password(password):
    # Use a secure hash function (e.g., SHA-256) to hash the password
    return hashlib.sha256(password.encode()).hexdigest()

def insert_login_credentials(username, password):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('login-credentials')

    # Hash the password before storing it
    hashed_password = hash_password(password)

    # Insert the item into the table
    try:
        response = table.put_item(
            Item={
                'username': username,
                'password': hashed_password
            }
        )
        print(f"Item added to 'login-credentials' table: {response}")
    except Exception as e:
        print(f"Error inserting item into 'login-credentials' table: {e}")


def delete_dynamodb_table(table_name):
    dynamodb = boto3.client('dynamodb')

    try:
        dynamodb.delete_table(TableName=table_name)
        print(f"DynamoDB table '{table_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting DynamoDB table: {e}")

def delete_s3_bucket(bucket_name):
    s3 = boto3.client('s3')

    try:
        # List all objects in the bucket
        response = s3.list_objects(Bucket=bucket_name)
        objects = response.get('Contents', [])

        # Delete all objects in the bucket
        for obj in objects:
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])

        # Delete the bucket itself
        s3.delete_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' and its contents deleted successfully.")
    except NoCredentialsError:
        print("Credentials not available. Unable to delete S3 bucket.")
    except Exception as e:
        print(f"Error deleting S3 bucket: {e}")
def create_resources():
    # Check if the table exists before calling the function
    if not does_table_exist(approved_images_table_name):
        create_vehicle_id_table(approved_images_table_name)

    # Check if the bucket exists before calling the function
    if not does_bucket_exist(approved_images_bucket_name):
        create_s3_bucket_and_upload_image(approved_images_bucket_name, initial_image_url, test_user)

    # Check if the table exists before calling the function
    if not does_table_exist(login_credentials_table_name):
        create_login_credentials_table(login_credentials_table_name)
        # Wait for the table to become active before proceeding
        wait_for_table_creation(login_credentials_table_name)
        
        # Call the function to insert a new username and password into the 'login-credentials' table
        insert_login_credentials(test_user, test_password)

def delete_resources():
    # Set the names of the resources to be deleted
    approved_vehicle_images_bucket_name = "approved-vehicle-images-3632442"
    dynamodb_table_names = ["approved-vehicles", "login-credentials"]

    # Delete the S3 bucket
    delete_s3_bucket(approved_vehicle_images_bucket_name)

    # Delete the DynamoDB tables
    for table_name in dynamodb_table_names:
        delete_dynamodb_table(table_name)

delete_resources()
create_resources()


if __name__ == "__main__":
    app.run(host='0.0.0.0')
