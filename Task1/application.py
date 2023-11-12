import datetime
from flask import Flask, render_template
import boto3
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)

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

def create_s3_bucket_and_upload_image(bucket_name, image_url):
    # Create an S3 client
    s3 = boto3.client('s3')

    # Check if the bucket already exists
    buckets = s3.list_buckets()['Buckets']
    if not any(bucket['Name'] == bucket_name for bucket in buckets):
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"S3 bucket '{bucket_name}' created successfully.")
        except Exception as e:
            print(f"Error creating S3 bucket: {e}")

    # Generate a unique filename using current UTC time (including milliseconds)
    current_time = datetime.datetime.utcnow()
    object_key = f"image_{current_time.strftime('%Y%m%d%H%M%S%f')}.png"

    # Upload the image to the S3 bucket
    try:
        with open("tmp_image.png", 'wb') as f:
            f.write(requests.get(image_url).content)
        s3.upload_file("tmp_image.png", bucket_name, object_key)
        print(f"Image uploaded to S3 bucket '{bucket_name}' with key '{object_key}'.")
        return object_key  # Return the generated object key
    except NoCredentialsError:
        print("Credentials not available. Unable to upload the image to S3.")
    except Exception as e:
        print(f"Error uploading image to S3: {e}")
    finally:
        # Remove the temporary file
        os.remove("tmp_image.png")

@app.route("/")
def index():
    # Assuming you have the upload_date available (replace it with the actual upload date)
    upload_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Call the function to create the S3 bucket and upload the image, and get the generated object key
    object_key = create_s3_bucket_and_upload_image("approved-cars-3632442", "https://www.linearity.io/blog/content/images/2023/06/how-to-create-a-car-NewBlogCover.png")

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

if __name__ == "__main__":
    app.run(host='0.0.0.0')
