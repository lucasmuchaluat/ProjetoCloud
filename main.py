import boto3
from dotenv import load_dotenv
import os
from botocore.exceptions import ClientError
import time

#global variables
name = "LucasMuchaluat"

key_pair_name = name + "_Key"
key_pair_name_ohio = key_pair_name + "_Ohio"
key_pair_name_nv = key_pair_name + "_NorthVirginia"

key_filename = key_pair_name + ".pem"
key_filename_ohio = key_pair_name + "_Ohio" + ".pem"
key_filename_nv = key_pair_name + "_NorthVirginia" + ".pem"

security_group_name = name + "_SecurityGroup"
security_group_name_ohio = security_group_name + "_Ohio"
security_group_name_nv = security_group_name + "_NorthVirginia"

load_balancer_name = name + "-LoadBalancer"

auto_scaling_group_name = name + "-AutoScalingGroup"

ohioAMI = "ami-0dd9f0e7df0f0a138"
nvAMI = "ami-00ddb0e5626798373"


user_data_db_ohio = """#!/bin/bash
                    sudo apt update
                    sudo apt install postgresql postgresql-contrib -y
                    sudo -u postgres psql -c "CREATE USER cloud WITH PASSWORD 'cloud';"
                    sudo -u postgres createdb -O cloud tasks
                    sudo sed -i "59 c listen_addresses='*'" /etc/postgresql/10/main/postgresql.conf
                    sudo sed -i "$ a host all all 0.0.0.0/0 trust" /etc/postgresql/10/main/pg_hba.conf
                    sudo ufw allow 5432/tcp
                    sudo systemctl restart postgresql 
                    """

user_data_django_nv = """#!/bin/bash
                sudo apt update
                cd /home/ubuntu
                git clone https://github.com/lucasmuchaluat/tasks.git
                sudo sed -i 's/node1/{0}/g' /home/ubuntu/tasks/portfolio/settings.py
                cd tasks
                ./install.sh
                sudo reboot
                """

# import credentials
load_dotenv(verbose=True)

# create session
session = boto3.session.Session(aws_access_key_id=os.getenv(
    "ACCESS-KEY"), aws_secret_access_key=os.getenv("SECRET-KEY"))

# create Ohio client e resource
ohioClient = session.client('ec2', region_name='us-east-2')
ohioResource = session.resource('ec2', region_name='us-east-2')

# create North Virginia client e resource
nvClient = session.client('ec2', region_name='us-east-1')
nvResource = session.resource('ec2', region_name='us-east-1')

# create Load Balancer client
lbClient = session.client('elb', region_name='us-east-1')

# create Auto Scaling Group client
asgClient = session.client('autoscaling', region_name='us-east-1')

# create key pair


def createKeyPair(client, key_name):
    print("------------ Creating Keys ------------\n")
    # deletar caso ja exista
    try:
        client.describe_key_pairs(KeyNames=[key_name])
        try:
            client.delete_key_pair(KeyName=key_name)
            print(f"Deletando par de chaves chamada {key_name}\n")
        except ClientError as e:
            print(e)
    except:
        pass
    # criar par de chaves
    try:
        key = client.create_key_pair(KeyName=key_name)
        print(f"Criando par de chaves chamada {key_name}\n")
        return key
    except ClientError as e:
        print(e)


# save key pair
def saveKeyPair(key, filename):
    print("------------ Saving Keys ------------\n")
    if filename in os.listdir():
        os.remove(filename)
    with open(filename, "w") as new_file:
        new_file.write(key['KeyMaterial'])
    print(f"Par de chaves {filename} criada e salva nos arquivos\n")

    os.chmod(filename, 0o400)
    print(f"Par de chaves {filename} invisível publicamente\n")


# create instance
def createInstance(resource, client, image_id, key_pair, securityGroup_name, user_data):
    print("------------ Creating Instance ------------\n")
    instance = resource.create_instances(
        ImageId=image_id,
        InstanceType='t2.micro',
        KeyName=key_pair,
        MaxCount=1,
        MinCount=1,
        Monitoring={
            'Enabled': True
        },
        SecurityGroups=[
            securityGroup_name,
        ],
        # SubnetId='string',
        UserData=user_data,
        # ClientToken='string',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': name
                    },
                    {
                        'Key': 'Name',
                        'Value': "INSTANCE"
                    },
                ]
            },
        ]
    )

    print(f"Aguardando a instancia {instance[0].id} ser criada...\n")
    waiter = client.get_waiter('instance_running')  # instance_status_ok
    waiter.wait(InstanceIds=[instance[0].id])

    print(f"A instancia {instance} foi criada com sucesso!\n")

    return instance[0].id


# get instance ip
def getInstanceIP(resource, instance_id):
    print("------------ Getting Instance IP ------------\n")
    running_instances = resource.instances.filter(
        Filters=[
            {
                'Name': 'tag:Owner',
                'Values': [name, ]
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )

    for instance in running_instances:
        if instance.id == instance_id:
            ip = instance.public_ip_address
            print(f"IP da instancia {instance.id} é IP: '{ip}'\n")
            return ip
        else:
            print(f"Instancia {instance_id} não encontrada!\n")


# terminate instance
def terminateInstance(resource, client):
    print("------------ Deleting Instance ------------\n")

    running_instances = resource.instances.filter(
        Filters=[
            {
                'Name': 'tag:Owner',
                'Values': [name, ]
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )

    if list(running_instances.limit(1)):
        for instance in running_instances:
            try:
                client.terminate_instances(
                    InstanceIds=[
                        instance.id,
                    ]
                )
                print(
                    f"Aguardando a instancia {instance.id} ser encerrada...\n")
                waiter = client.get_waiter(
                    'instance_terminated')  # instance_stopped
                waiter.wait(InstanceIds=[instance.id])
                print(
                    f"A instancia {instance.id} foi encerrada com sucesso!\n")
            except ClientError as e:
                print(
                    f"Não foi possível terminar nenhuma instância. Erro: {e}\n")
    else:
        print(f"Não há nenhuma instância rodando no momento.\n")


# create security group
def createSecurityGroup(client, group_name, porta):
    print("------------ Creating Security Group ------------\n")
    try:
        # Pega o id do vpc
        describeVPC = client.describe_vpcs()
        vpc_id = describeVPC["Vpcs"][0]["VpcId"]

        # Cria Security Group
        client.create_security_group(
            Description="Security Group Projeto Lucas",
            GroupName=group_name,
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
                        {
                            'Key': 'Owner',
                            'Value': name
                        },
                        {
                            'Key': 'Name',
                            'Value': "SG"
                        },
                    ]
                },
            ]
        )

        try:
            # Permitir porta 5432 ou 8080
            client.authorize_security_group_ingress(
                GroupName=group_name,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                        'FromPort': porta,
                        'ToPort': porta,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                     }]
            )

            # Permitir porta 22
            client.authorize_security_group_ingress(
                GroupName=group_name,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                     }]
            )
            print(
                f"Security group e regra de ingresso criadas com sucesso para {group_name}.\n")

        except ClientError as e:
            print(
                f"Não foi possível criar regra de ingresso para {group_name}. Erro: {e}\n")

    except ClientError as e:
        print(
            f"Não foi possível criar security group {group_name}. Erro: {e}\n")


# delete security group
def deleteSecurityGroup(client, group_name):
    print("------------ Deleting Security Group ------------\n")
    try:
        client.describe_security_groups(GroupNames=[group_name])
        try:
            client.delete_security_group(GroupName=group_name)
            print(f"Security group {group_name} deletado com sucesso.\n")
        except ClientError as e:
            print(
                f"Não foi possível deletar o security group {group_name}. Erro: {e}\n")
    except ClientError as e:
        print(
            f"Security Group com nome de {group_name} não foi encontrado. Erro: {e}\n")


# create load balancer
def createLoadBalancer(client, clientGeral, group_name):
    print("------------ Creating Load Balancer ------------\n")
    try:
        idSecurityGroup = clientGeral.describe_security_groups(
            GroupNames=[group_name])["SecurityGroups"][0]["GroupId"]
        try:
            lb = client.create_load_balancer(
                LoadBalancerName=load_balancer_name,
                Listeners=[
                    {
                        'Protocol': 'tcp',
                        'LoadBalancerPort': 8080,
                        'InstanceProtocol': 'tcp',
                        'InstancePort': 8080,
                    },
                ],
                AvailabilityZones=[
                    'us-east-1a',
                    'us-east-1b',
                    'us-east-1c',
                    'us-east-1d',
                    'us-east-1e',
                    'us-east-1f'
                ],
                SecurityGroups=[
                    idSecurityGroup,
                ],
                Tags=[
                    {
                        'Key': 'Owner',
                        'Value': name
                    },
                    {
                        'Key': 'Name',
                        'Value': "LB"
                    },
                ]
            )
            print(
                f"Load Balancer criado com sucesso com nome de {load_balancer_name}.\n")

            return lb
        except:
            print(
                f"Não foi possível localizar Security Group chamado {group_name}.\n")
    except:
        print(
            f"Não foi possível criar Load Balancer chamado {load_balancer_name}.\n")


# fill load balancer dns in client
def writeLoadBalancerDNS(loadBalancer, clientFile):
    print("------------ Writing Load Balancer DNS on client ------------\n")
    url = f'"http://{loadBalancer.get("DNSName", None)}:8080/tasks/"'
    try:
        with open(clientFile, "r") as f:
            file = f.readlines()
            file[5] = "urlLB =" + url + "\n"

        with open(clientFile, "w") as f:
            f.writelines(file)

        print(
            f"DNS {url} escrito no client com sucesso!\n")
    except:
        print(
            f"Não foi possível escrever o DNS {url} no client.\n")


# delete load balancer
def deleteLoadBalancer(client):
    print("------------ Deleting Load Balancer ------------\n")
    try:
        client.describe_load_balancers(
            LoadBalancerNames=[load_balancer_name]
        )
        client.delete_load_balancer(
            LoadBalancerName=load_balancer_name
        )
        print(f"Load Balancer {load_balancer_name} deletado com sucesso.\n")

    except ClientError as e:
        print(
            f"Load Balancer com nome de {load_balancer_name} não foi encontrado. Erro: {e}\n")


# create auto scaling group
def createAutoScalingGroup(client, instance_id):
    print("------------ Creating Auto Scaling Group ------------\n")
    try:
        client.create_auto_scaling_group(
            AutoScalingGroupName=auto_scaling_group_name,
            InstanceId=instance_id,
            MinSize=1,
            MaxSize=5,
            DesiredCapacity=1,
            LoadBalancerNames=[
                load_balancer_name,
            ],
            Tags=[
                {
                    'Key': 'Owner',
                    'Value': name
                },
                {
                    'Key': 'Name',
                    'Value': "ASG-TEST"
                },
            ]
        )
        print(
            f"Auto Scaling Group criado com sucesso com nome de {auto_scaling_group_name}.\n")
    except ClientError as e:
        print(
            f"Não foi possível criar Auto Scaling Group chamado {auto_scaling_group_name}. Erro: {e}.\n")


# delete auto scaling group
def deleteAutoScalingGroup(client):
    print("------------ Deleting Auto Scaling Group ------------\n")
    try:
        client.delete_auto_scaling_group(
            AutoScalingGroupName=auto_scaling_group_name,
            ForceDelete=True
        )
        print(
            f"Auto Scaling Group {auto_scaling_group_name} deletado com sucesso.\n")
    except ClientError as e:
        print(
            f"Não foi possível deletar o Auto Scaling Group chamado {auto_scaling_group_name}. Erro: {e}\n")


# delete launch configuration
def deleteLauchConfiguration(client, asgName):
    print("------------ Deleting Launch Configuration ------------\n")
    try:
        client.delete_launch_configuration(
            LaunchConfigurationName=asgName
        )
        print(
            f"Launch Configuration {asgName} deletado com sucesso.\n")
    except ClientError as e:
        print(
            f"Não foi possível deletar o Launch Configuration {asgName}. Erro: {e}\n")


# ohio setup
def configOhio():
    print("------------ OHIO ------------\n")
    terminateInstance(ohioResource, ohioClient)
    deleteSecurityGroup(ohioClient, security_group_name_ohio)

    key = createKeyPair(ohioClient, key_pair_name_ohio)
    saveKeyPair(key, key_filename_ohio)
    createSecurityGroup(ohioClient, security_group_name_ohio, 5432)

    databaseID = createInstance(ohioResource, ohioClient, ohioAMI,
                                key_pair_name_ohio, security_group_name_ohio, user_data_db_ohio)
    databaseIP = getInstanceIP(ohioResource, databaseID)
    print("------------ FIM OHIO ------------\n")

    return databaseIP


# north virginia setup
def configNV(ipOhio):
    print("------------ NORTH VIRGINIA ------------\n")
    deleteAutoScalingGroup(asgClient)
    deleteLauchConfiguration(asgClient, auto_scaling_group_name)
    deleteLoadBalancer(lbClient)
    terminateInstance(nvResource, nvClient)
    deleteSecurityGroup(nvClient, security_group_name_nv)

    key = createKeyPair(nvClient, key_pair_name_nv)
    saveKeyPair(key, key_filename_nv)
    createSecurityGroup(nvClient, security_group_name_nv, 8080)

    djangoID = createInstance(nvResource, nvClient, nvAMI,
                              key_pair_name_nv, security_group_name_nv, user_data_django_nv.format(ipOhio))

    lb = createLoadBalancer(lbClient, nvClient, security_group_name_nv)
    writeLoadBalancerDNS(lb, "client.py")
    createAutoScalingGroup(asgClient, djangoID)
    print("------------ FIM NORTH VIRGINIA ------------\n")


# execute all
if __name__ == "__main__":
    start = time.time()
    ipDatabase = configOhio()
    configNV(ipDatabase)
    end = time.time()

    print(
        f"TEMPO DESDE O INÍCIO DA EXECUÇÃO: {round((end - start),2)} segundos.")
