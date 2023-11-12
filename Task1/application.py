from flask import Flask
import boto3
import requests
from botocore.exceptions import NoCredentialsError
app = Flask(__name__)

@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

def create_s3_bucket_and_upload_image(bucket_name, image_url, object_key):
    # Create an S3 client
    s3 = boto3.client('s3')

    # Create an S3 bucket
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' created successfully.")
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")

    # Upload the image to the S3 bucket
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            s3.put_object(Body=response.content, Bucket=bucket_name, Key=object_key)
            print(f"Image uploaded to S3 bucket '{bucket_name}' with key '{object_key}'.")
        else:
            print(f"Failed to download the image from {image_url}. Status code: {response.status_code}")
    except NoCredentialsError:
        print("Credentials not available. Unable to upload the image to S3.")

# Set your S3 bucket name, image URL, and object key
bucket_name = "approved-cars-3632442"
image_url = "https://www.linearity.io/blog/content/images/2023/06/how-to-create-a-car-NewBlogCover.png"
object_key = "car_image.png"

# Call the function to create the S3 bucket and upload the image
create_s3_bucket_and_upload_image(bucket_name, image_url, object_key)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
