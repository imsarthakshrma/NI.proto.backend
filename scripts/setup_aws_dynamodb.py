
"""
AWS DynamoDB Setup Script for Native IQ
Creates the required DynamoDB table for session storage
"""

import boto3
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def create_dynamodb_table():
    """Create DynamoDB table for Native IQ session storage"""
    
    # Get AWS credentials from environment
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'native_iq_sessions')
    
    if not aws_access_key or not aws_secret_key:
        print("❌ AWS credentials not found in environment variables")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        return False
    
    try:
        # Create DynamoDB client
        dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        print(f"🔄 Creating DynamoDB table: {table_name}")
        
        # Create table
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'session_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'session_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'Native-IQ'
                },
                {
                    'Key': 'Environment',
                    'Value': 'Development'
                }
            ]
        )
        
        print("✅ DynamoDB table created successfully!")
        print(f"Table ARN: {response['TableDescription']['TableArn']}")
        
        # Wait for table to be active
        print("🔄 Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("✅ Table is now active and ready to use!")
        return True
        
    except dynamodb.exceptions.ResourceInUseException:
        print(f"✅ Table {table_name} already exists!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating DynamoDB table: {e}")
        return False

def test_dynamodb_connection():
    """Test DynamoDB connection and basic operations"""
    
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'native_iq_sessions')
    
    try:
        # Create DynamoDB resource
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        table = dynamodb.Table(table_name)
        
        print("🔄 Testing DynamoDB connection...")
        
        # Test write
        test_item = {
            'user_id': 'test_user_123',
            'session_id': 'test_session_456',
            'session_data': {
                'contacts': {},
                'last_activity': '2025-08-19T16:54:56+05:30',
                'message_count': 1
            },
            'created_at': '2025-08-19T16:54:56+05:30',
            'updated_at': '2025-08-19T16:54:56+05:30'
        }
        
        table.put_item(Item=test_item)
        print("✅ Test write successful!")
        
        # Test read
        response = table.get_item(
            Key={
                'user_id': 'test_user_123',
                'session_id': 'test_session_456'
            }
        )
        
        if 'Item' in response:
            print("✅ Test read successful!")
            print(f"Retrieved item: {response['Item']['session_data']}")
        else:
            print("❌ Test read failed - item not found")
            return False
        
        # Clean up test data
        table.delete_item(
            Key={
                'user_id': 'test_user_123',
                'session_id': 'test_session_456'
            }
        )
        print("✅ Test cleanup successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ DynamoDB connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Native IQ AWS DynamoDB Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your AWS credentials")
        sys.exit(1)
    
    # Create table
    if create_dynamodb_table():
        print("\n🧪 Running connection test...")
        if test_dynamodb_connection():
            print("\n🎉 DynamoDB setup complete!")
            print("\nNext steps:")
            print("1. Set up Redis for caching")
            print("2. Configure ChromaDB for vector storage")
            print("3. Deploy your Native IQ application")
        else:
            print("\n❌ Connection test failed. Please check your AWS credentials.")
    else:
        print("\n❌ DynamoDB setup failed. Please check your AWS credentials and permissions.")
