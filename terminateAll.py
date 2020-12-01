from main import terminateInstance, deleteAutoScalingGroup, deleteLauchConfiguration, deleteLoadBalancer, deleteSecurityGroup
import time
from dotenv import load_dotenv
import boto3
import os

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

# ohio setup


def cleanOhio():
    print("------------ LIMPANDO OHIO ------------\n")
    print("Iniciando limpeza do setup de Ohio...\n")
    terminateInstance(ohioResource, ohioClient)
    deleteSecurityGroup(ohioClient, security_group_name_ohio)
    print("Limpeza do setup de Ohio concluída com sucesso!\n")
    print("------------ FIM LIMPEZA OHIO ------------\n")


# north virginia setup
def cleanNV():
    print("------------ LIMPANDO NORTH VIRGINIA ------------\n")
    print("Iniciando limpeza do setup de North Viriginia...\n")
    deleteAutoScalingGroup(asgClient)
    deleteLauchConfiguration(asgClient, auto_scaling_group_name)
    deleteLoadBalancer(lbClient)
    terminateInstance(nvResource, nvClient)
    deleteSecurityGroup(nvClient, security_group_name_nv)
    print("Limpeza do setup de North Virginia concluída com sucesso!\n")
    print("------------ FIM LIMPEZA NORTH VIRGINIA ------------\n")


# execute all
start = time.time()
cleanOhio()
cleanNV()
end = time.time()

print(f"TEMPO DESDE O INÍCIO DA LIMPEZA: {round((end - start),2)} segundos.")
