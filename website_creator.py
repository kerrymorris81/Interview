#  The goal of this script is to create a VPC, a gateway which is attached to the VPC, subnet for our vpc using specified
#  CIDR block, and creating an EC2 Instance. In the EC2 Instance, we will create and populate a database table in DynamoDB,
#  create an S3 bucket, and upload local files making a webpage. This webpage will display the names and roles of the AWS
#  team stored in our DB table. Best practice is variables instantiated outside of functions to promote scalability and
#  mutability. Second Best Practice is to keep each function compartmentalized. This is usually done is seperate scripts,
#  but in the interest of time and simplicity, one script runs all functions.


import boto3
import array
import subprocess
#import os
import json
import decimal

# Amazon Machine Image launches using Amazon Linux AMI 2018.03.0 (HVM), SSD Volume Type
ami = 'ami-0b59bfac6be064b78'

# Region name, in this case, N. Virginia
region = 'us-east-1'
instance='t2.micro'
myKey='For security best practice, key is omitted but would be provided here'

# Creates EC2 Connection
ec2 = boto3.resource('ec2')

# Defines our Virtual Private Cloud
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/27'
                     AmazonProvidedIpv6CidrBlock=False, # Since we are providing our CIDR block, we leave this false
                     DryRun=True,  # Checks our permissions 
                     InstanceTenancy='dedicated' # This will ensure instances are  launched in a VPC run on hardware that's dedicated to a single customer.
                    )

# Establishes our subnet
subnet = vpc.create_subnet(CidrBlock='10.0.0.0/28')

# Creates a gateway, since we don't have a specified gateway, we will not provide a gateway id.
gateway = ec2.create_internet_gateway()

# Attaches our Gateway to our VPC
gateway.attach_to_vpc(VpcId=vpc.vpc_id
                     )

# Associates our gateway Id address
address = ec2.VpcAddress(VpcId)
address.associate(gateway) # This'll give us a place holder until our routing table is set up.

# Creates a routing table
routeTable = vpc.create_route_table(VpcId=vpc.vpc_id
                                    DryRun=True
                                    )

# Routing setup, other parameters are allowed if needed to be specified, but we will use defaults
ipv4 = routeTable.create_route(DestinationCidrBlock='0.0.0.0/0', 
                               GatewayId=gateway.internet_gateway_id,
                               DryRun=True
                              )
ipv6 = routeTable.create_route(DestinationIpv6CidrBlock='::/0', 
                               GatewayId=gateway.internet_gateway_id,
                               DryRun=True
                              )

#Grabs our ID's for subnet association and then associates subnet
subnet = ec2.Subnet('id')
routeTabeId = ec2.describe_route_table('RouteTableId')
routeTable.associate_with_subnet(SubnetId=subnet.subnet_id
                                 RouteTableId=routeTableId,
                                 SubnetId=subnet,
                                )

# Instantiantes our Security Group
security = vpc.create_security_group(GroupName="connectrians", 
                                     Description="This is my sample group"
                                    )

ipv4range = [{
    'CidrIp': '0.0.0.0/0'
}]

ipv6range = [{
    'CidrIpv6': '::/0'
}]

ports = [{
    'IpProtocol': 'TCP',
    'FromPort': 80,  #HTTP Port
    'ToPort': 80,
    'IpRanges': ipv4range,
    'Ipv6Ranges': ipv6range
}, {
    'IpProtocol': 'TCP',
    'FromPort': 443,  #HTTPS Port
    'ToPort': 443,
    'IpRanges': ipv4range,
    'Ipv6Ranges': ipv6range
}, {
    'IpProtocol': 'TCP',
    'FromPort': 22, #SSH Port
    'ToPort': 22,
    'IpRanges': ipv4range,  # Change to supplement use case
    'Ipv6Ranges': ipv6range  # Change to supplement use case
}]

# Uses our above values in the function
security.authorize_security_group_ingress(IpPermissions=ports)

# Grab ARN for use in EC2 Instance instantiation
client = boto3.client('iam')
arn=client.get_user()['User']['Arn'].split(':')[4]

ec2Name = 'AWS Test instance'

#Launches EC2 instance
ec2.create_instances(ImageId=ami,
                     InstanceType=instance,
                     MinCount=1, MaxCount=1,
                     SecurityGroupIds=[security.GroupName],
                     KeyName=myKey,
                     IamInstanceProfile={
                            'Arn':  arn,
                            'Name': ec2Name
}
)

#v=vpc.vpc_id
#g=gateway.internet_gateway_id
#s=routeTable.subnet_id

#bash = array.array(v, g, s)

#print (*bash)#

# Making bash variables for switch to mini-bash scripts
subprocess.run('$SECURITY_GROUP=connectrians')
subprocess.run('$REGION=us-east-1')
subprocess.run('$BUCKET=connectrianbucket')

subprocess.run('aws', 's3api', 'create-bucket', '--bucket $BUCKET', '--region $REGION')

# Runs following CLI command: aws s3api create-bucket --bucket $BUCKET --region $REGION

# Create the S3 client
s3 = boto3.client('s3')

# Get Bucket List from S3
query = s3.list_buckets()

# Pull the name from query
buckets = [bucket['Name'] for bucket in query['Buckets']]

# Assign the bucket name to a local variable
myBucket = print(buckets)

# Upload files to bucket
filename = array.array(subprocess.run('ls', '>', 'files.txt', '|', 'cat', 'files.txt'))
#Runs CLI command ls > files.txt | cat files.txt

# Parses array for upload and pushes files
for x in filename:
    s3.upload_file(filename[x], myBucket, filename[x])

endPoint="http://localhost:8000"

# Initialize Dynamodb connection
dynamodb = boto3.resource('dynamodb', region_name=region, endpoint_url=endPoint)

# Creation of our demo table
table = dynamodb.create_table(
    TableName='AWS TEAM',
    KeySchema=[
        {
            'AttributeName': 'Name',
            'KeyType': 'HASH'  #Partition key
        },
        {
            'AttributeName': 'Role',
            'KeyType': 'RANGE'  #Sort key
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'Name',
            'AttributeType': 'S'
        },
        {
            'AttributeName': 'Role',
            'AttributeType': 'S'
        },

    ],
  # Instatiating Table Size Manually due to lack of autoscaling
    ProvisionedThroughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

# Converts DynameDB items to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

myTable = dynamodb.Table('AWS Team')

name = array.array("Bill West", "AJ Mathis", "Ryan Williams", "Charlie Brown", "Ryan McCormick",
                   "Aileen Curtin", "Brandon Franklin")
role = array.array("Director of Cloud Services", "Cloud Architect", "Systems Engineer",
                   "Cloud Solutions Architect", "Sr. Systems Engineer", "Solution Delivery Analyst",
                   "AWS Administrator")

# Puts items into created database. A Multi-Dimensional array could also be used but not as practical with just two values.

for y in name:
    myTable.put_item(
        Item={
            'Name': name[y],
            'Role': role[y],
        }
)
