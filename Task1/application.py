from flask import Flask, render_template
import boto3
import requests
from botocore.exceptions import NoCredentialsError
import os

app = Flask(__name__)

# Set your S3 bucket name, image URL, and object key
approved_images_bucket_name = "approved-cars-3632442"
image_url = "https://www.linearity.io/blog/content/images/2023/06/how-to-create-a-car-NewBlogCover.png"
object_key = "car_image.png"

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

def create_s3_bucket_and_upload_image(bucket_name, image_url, object_key):
    s3 = boto3.client('s3')

    # Check if the bucket exists
    if not does_bucket_exist(bucket_name):
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"S3 bucket '{bucket_name}' created successfully.")
        except Exception as e:
            print(f"Error creating S3 bucket: {e}")

    # Check if the object (image) already exists in the S3 bucket
    if not does_object_exist(bucket_name, object_key):
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                s3.put_object(Body=response.content, Bucket=bucket_name, Key=object_key)
                print(f"Image uploaded to S3 bucket '{bucket_name}' with key '{object_key}'.")
            else:
                print(f"Failed to download the image from {image_url}. Status code: {response.status_code}")
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
        return objects
    except Exception as e:
        print(f"Error listing objects in S3 bucket: {e}")
        return []

@app.route("/")
def index():
    
    # List all objects in the S3 bucket
    objects = list_objects_in_bucket("approved-cars-3632442")

    # Render the HTML template and pass variables to it
    return render_template("index.html", uploaded_images=objects)

@app.route("/upload", methods=["POST"])
def upload():
    # Handle the file upload logic here
    # You can access the uploaded file using request.files['file']
    # Implement the logic to upload the file to S3 and update the HTML accordingly

    return "Upload action will be implemented here"

# Check if the bucket and initial file exist before calling the function
if not does_bucket_exist(approved_images_bucket_name) or not does_object_exist(approved_images_bucket_name, object_key):
    create_s3_bucket_and_upload_image(approved_images_bucket_name, image_url, object_key)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
