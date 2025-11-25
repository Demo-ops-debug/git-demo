import boto3

def get_ec2_resource(region='us-east-1'):
    return boto3.resource('ec2', region_name=region)

def get_ec2_client(region='us-east-1'):
    return boto3.client('ec2', region_name=region)

def get_elbv2_client(region='us-east-1'):
    return boto3.client('elbv2', region_name=region)

def get_ssm_client(region='us-east-1'):
    return boto3.client('ssm', region_name=region)

def create_security_group(ec2, group_name, description, vpc_id, ingress_rules):
    sg = ec2.create_security_group(
        GroupName=group_name,
        Description=description,
        VpcId=vpc_id
    )
    sg.authorize_ingress(IpPermissions=ingress_rules)
    return sg

def get_default_vpc_and_subnets(ec2_client):
    vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets'][:2]]
    return vpc_id, subnet_ids

def create_target_group(elbv2, vpc_id):
    tg = elbv2.create_target_group(
        Name='tooplate-tg',
        Protocol='HTTP',
        Port=80,
        VpcId=vpc_id,
        TargetType='instance',
        HealthCheckProtocol='HTTP',
        HealthCheckPort='80',
        HealthCheckPath='/'
    )
    return tg['TargetGroups'][0]['TargetGroupArn']

def create_alb(elbv2, name, subnets, security_group_id):
    alb = elbv2.create_load_balancer(
        Name=name,
        Subnets=subnets,
        SecurityGroups=[security_group_id],
        Scheme='internet-facing',
        Type='application',
        IpAddressType='ipv4'
    )
    return alb['LoadBalancers'][0]['LoadBalancerArn']

def create_listener(elbv2, alb_arn, tg_arn):
    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[{
            'Type': 'forward',
            'TargetGroupArn': tg_arn
        }]
    )

def create_key_pair(ec2, key_name, filename):
    key_pair = ec2.create_key_pair(KeyName=key_name)
    with open(filename, 'w') as file:
        file.write(key_pair.key_material)
    return key_name

def get_latest_ami(ssm):
    return ssm.get_parameter(
        Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
    )['Parameter']['Value']

def launch_instance(ec2, ami_id, key_name, sg_id, user_data):
    instance = ec2.create_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        UserData=user_data
    )[0]
    return instance

USER_DATA = '''#!/bin/bash
yum update -y
yum install -y httpd wget unzip
systemctl enable httpd
systemctl start httpd
cd /var/www/html
wget https://www.tooplate.com/zip-templates/2136_kool_form_pack.zip
unzip 2136_kool_form_pack.zip
cp -r 2136_kool_form_pack/* .
rm -rf 2136_kool_form_pack 2136_kool_form_pack.zip
chown -R apache:apache /var/www/html
'''

# Main entry point for provisioning AWS infrastructure components for the Tooplate application.

# 1. Initialize AWS service clients and resources
region = 'us-east-1'
ec2 = get_ec2_resource(region)
ec2_client = get_ec2_client(region)
elbv2 = get_elbv2_client(region)
ssm = get_ssm_client(region)

# 2. Retrieve the default VPC ID and subnet IDs
vpc_id, subnet_ids = get_default_vpc_and_subnets(ec2_client)

# 3. Create a security group for the ALB to allow HTTP from anywhere
alb_sg = create_security_group(
    ec2,
    group_name='tooplate-alb-sg',
    description='Allow HTTP from anywhere for ALB',
    vpc_id=vpc_id,
    ingress_rules=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
    ]
)

# 4. Create a target group and ALB, then set up a listener
tg_arn = create_target_group(elbv2, vpc_id)
alb_arn = create_alb(elbv2, name='tooplate-alb', subnets=subnet_ids, security_group_id=alb_sg.id)
create_listener(elbv2, alb_arn, tg_arn)

# 5. Generate an EC2 key pair for SSH access
key_name = create_key_pair(ec2, key_name='tooplate-keypair', filename='tooplate-keypair.pem')

# 6. Create a security group for EC2 instances to allow HTTP and SSH
sg = create_security_group(
    ec2,
    group_name='tooplate-sg',
    description='Allow HTTP and SSH',
    vpc_id=vpc_id,
    ingress_rules=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        },
        {
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
    ]
)

# 7. Retrieve the latest Amazon Linux AMI ID
ami_id = get_latest_ami(ssm)

# 8. Launch an EC2 instance with the specified configuration
instance = launch_instance(
    ec2,
    ami_id=ami_id,
    key_name=key_name,
    sg_id=sg.id,
    user_data=USER_DATA
)

# 9. Output the launched EC2 instance ID
print(f'Launched EC2 Instance ID: {instance.id}')
    region = 'us-east-1'
    ec2 = get_ec2_resource(region)
    ec2_client = get_ec2_client(region)
    elbv2 = get_elbv2_client(region)
    ssm = get_ssm_client(region)

    vpc_id, subnet_ids = get_default_vpc_and_subnets(ec2_client)

    alb_sg = create_security_group(
        ec2,
        'tooplate-alb-sg',
        'Allow HTTP from anywhere for ALB',
        vpc_id,
        [{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
          'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}]
    )

    tg_arn = create_target_group(elbv2, vpc_id)
    alb_arn = create_alb(elbv2, 'tooplate-alb', subnet_ids, alb_sg.id)
    create_listener(elbv2, alb_arn, tg_arn)

    key_name = create_key_pair(ec2, 'tooplate-keypair', 'tooplate-keypair.pem')

    sg = create_security_group(
        ec2,
        'tooplate-sg',
        'Allow HTTP and SSH',
        vpc_id,
        [
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )

    ami_id = get_latest_ami(ssm)
    instance = launch_instance(ec2, ami_id, key_name, sg.id, USER_DATA)
    print(f'Launched EC2 Instance ID: {instance.id}')

if __name__ == '__main__':
    main()