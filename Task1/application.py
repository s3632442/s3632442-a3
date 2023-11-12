import datetime
from flask import Flask, render_template, request
import boto3
import requests
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)

def does_object_exist(approved_images_bucket_name, object_key):
    # Create an S3 client
    s3 = boto3.client('s3')

    # Check if the object (image) already exists in the S3 bucket
    try:
        s3.head_object(Bucket=approved_images_bucket_name, Key=object_key)
        return True
    except Exception as e:
        return False

def create_s3_bucket_and_upload_image(approved_images_bucket_name, image_url):
    # Create an S3 client
    s3 = boto3.client('s3')

    # Create an S3 bucket if it doesn't exist
    if not does_object_exist(approved_images_bucket_name, ""):
        try:
            s3.create_bucket(Bucket=approved_images_bucket_name)
            print(f"S3 bucket '{approved_images_bucket_name}' created successfully.")
        except Exception as e:
            print(f"Error creating S3 bucket: {e}")

    # Generate a unique filename using current UTC time (including milliseconds)
    current_time = datetime.datetime.utcnow()
    object_key = f"image_{current_time.strftime('%Y%m%d%H%M%S%f')}.png"

    # Upload the image to the S3 bucket
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            s3.put_object(Body=response.content, Bucket=approved_images_bucket_name, Key=object_key)
            print(f"Image uploaded to S3 bucket '{approved_images_bucket_name}' with key '{object_key}'.")
            return object_key  # Return the generated object key
        else:
            print(f"Failed to download the image from {image_url}. Status code: {response.status_code}")
    except NoCredentialsError:
        print("Credentials not available. Unable to upload the image to S3.")
    except Exception as e:
        print(f"Error uploading image to S3: {e}")

@app.route("/")
def index():
    # Assuming you have the upload_date available (replace it with the actual upload date)
    upload_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Call the function to create the S3 bucket and upload the image, and get the generated object key
    object_key = create_s3_bucket_and_upload_image("approved-cars-3632442", "https://www.linearity.io/blog/content/images/2023/06/how-to-create-a-car-NewBlogCover.png")

    # Render the HTML template and pass variables to it
    return render_template("index.html", uploaded_image=f"https://approved-cars-3632442.s3.amazonaws.com/{object_key}", upload_date=upload_date)

@app.route("/upload", methods=["POST"])
def upload():
    # Handle the file upload logic here
    # You can access the uploaded file using request.files['file']
    # Implement the logic to upload the file to S3 and update the HTML accordingly

    return "Upload action will be implemented here"

if __name__ == "__main__":
    app.run(host='0.0.0.0')
