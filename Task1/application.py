import hashlib
from flask import Flask, render_template, request, jsonify
import boto3
import requests
from botocore.exceptions import NoCredentialsError
import time
from datetime import datetime, timezone

app = Flask(__name__)

test_user = 'example_user'
test_password = 'example_password'
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
    
def add_approved_vehicle_image(username, filename, image_url, key):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('approved-vehicles')

    try:
        response = table.put_item(
            Item={
                'image_id': key,  # Use the provided key as the image_id
                'username': username,
                'image_filename': filename,
                'image_url': image_url
            }
        )
        print(f"Item added to 'approved-vehicles' table: {response}")
    except Exception as e:
        print(f"Error adding item to 'approved-vehicles' table: {e}")

def create_s3_bucket_and_upload_image(bucket_name, initial_image_url, test_user):
    s3 = boto3.client('s3')

    # Generate a unique filename using the current UTC time (including milliseconds)
    current_time = datetime.utcnow()
    object_key = f"image_{current_time.strftime('%Y%m%d%H%M%S%f')}.png"

    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' created successfully.")
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")
        return

    # Check if the object (image) already exists in the S3 bucket
    if not does_object_exist(bucket_name, object_key):
        try:
            response = requests.get(initial_image_url)
            if response.status_code == 200:
                s3.put_object(Body=response.content, Bucket=bucket_name, Key=object_key)
                print(f"Image uploaded to S3 bucket '{bucket_name}' with key '{object_key}'.")

                # Get the URL of the uploaded image
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

                # Add the approved vehicle image using the obtained URL and key
                add_approved_vehicle_image(test_user, object_key, s3_url, object_key)
            else:
                print(f"Failed to download the image from {initial_image_url}. Status code: {response.status_code}")
        except NoCredentialsError:
            print("Credentials not available. Unable to upload the image to S3.")
        except Exception as e:
            print(f"Error uploading image to S3: {e}")

def fetch_data_from_table(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    try:
        # Scan the entire table (not recommended for large tables in production)
        response = table.scan()
        items = response.get('Items', [])
        return items
    except Exception as e:
        print(f"Error fetching data from '{table_name}' table: {e}")
        return []

# Update your convert_utc_to_local function to use the browser's time zone
def convert_utc_to_local(utc_string):
    try:
        # Extract the timestamp from the S3 object key (assuming format 'image_YYYYMMDDHHMMSS%f.png')
        timestamp_str = utc_string.split('_')[1].split('.')[0]

        # Parse the timestamp string to a datetime object
        utc_datetime = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S%f')

        # Convert to the local browser time zone
        local_timezone = timezone('UTC')  # Set the default to UTC
        if browser_time_zone:
            local_timezone = timezone(browser_time_zone)

        local_datetime = utc_datetime.astimezone(local_timezone)

        return local_datetime
    except Exception as e:
        print(f"Error converting UTC to local: {e}")
        return None
    
# New route to handle the time zone information sent from the client
@app.route("/set_timezone", methods=["POST"])
def set_timezone():
    global browser_time_zone
    data = request.get_json()
    browser_time_zone = data.get('timeZone', None)
    return jsonify({'status': 'success'})



@app.route("/")
def index():
    # List all objects in the S3 bucket
    objects = list_objects_in_bucket(approved_images_bucket_name, approved_images_table_name)

    # Generate full URLs for each image
    base_url = f"https://{approved_images_bucket_name}.s3.amazonaws.com/"
    for obj in objects:
        # Check if 'Key' is present in the object before using it
        if 'Key' in obj:
            obj['full_url'] = f"{base_url}{obj['Key']}"
            obj['local_date'] = convert_utc_to_local(obj['Key'][6:-4])  # Assuming the format is 'image_YYYYMMDDHHMMSS%f.png'
        else:
            obj['full_url'] = "N/A"
            obj['local_date'] = "N/A"

    # Fetch debug data from tables
    login_credentials_data = fetch_data_from_table(login_credentials_table_name)
    approved_vehicle_images_data = fetch_data_from_table(approved_images_table_name)

    # Render the HTML template and pass variables to it
    return render_template("index.html", uploaded_images=objects, login_credentials_data=login_credentials_data, approved_vehicle_images_data=approved_vehicle_images_data)


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

def list_objects_in_bucket(bucket_name, table_name):
    # Create an S3 client
    s3 = boto3.client('s3')
    
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
        
    try:
        # Get the DynamoDB table
        table = dynamodb.Table(table_name)
        
        # List objects in the S3 bucket
        response = s3.list_objects(Bucket=bucket_name)
        objects = response.get('Contents', [])

        # Create a list to store image details
        image_details = []

        # Check if there are any objects in the bucket
        if objects:
            # Iterate through each object in the S3 bucket
            for obj in objects:
                # Check if 'Key' is present in the object
                if 'Key' in obj:
                    # Get image details from DynamoDB table using the filename
                    response = table.get_item(
                        Key={
                            'image_filename': obj['Key'],  # Include 'Key' in the DynamoDB key
                            'username': test_user
                        }
                    )
                    item = response.get('Item', None)

                    if item:
                        # Extract relevant details
                        image_id = item.get('image_id', '')
                        image_url = item.get('image_url', '')
                        image_filename = item.get('image_filename', '')
                        username = item.get('username', '')
                        
                        # Get the local system time and date
                        local_date = datetime.now()

                        # Create a dictionary with image details
                        image_detail = {
                            'image_id': image_id,
                            'image_url': image_url,
                            'image_filename': image_filename,
                            'username': username,
                            'local_date': local_date.strftime('%Y-%m-%d %H:%M'),
                            'full_url': f"https://{bucket_name}.s3.amazonaws.com/{obj['Key']}"
                        }

                        # Append the dictionary to the list
                        image_details.append(image_detail)
                else:
                    print("Warning: 'Key' not found in object.")
                    print('Image Details:', image_details)

        return image_details

    except Exception as e:
        print(f"Error listing objects in S3 bucket: {e}")
        return []



delete_resources()
create_resources()


if __name__ == "__main__":
    app.run(host='0.0.0.0')
