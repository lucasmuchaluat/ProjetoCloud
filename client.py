import click
import requests
import json
import datetime

urlLB ="http://LucasMuchaluat-LoadBalancer-505629433.us-east-1.elb.amazonaws.com:8080/tasks/"

@click.command()
@click.option('-i', '--instruction', default="GET")
@click.option('-t', '--title', default="Default Title")
@click.option('-pd', '--pub_date', default=str(datetime.datetime.now()))
@click.option('-d', '--description', default="Default Description")

def main(instruction, title, pub_date, description):
    if instruction == "GET":
        r = requests.get(urlLB + "list")
        print(r.text)
        
    if instruction == "POST":
        payload = {
            "title":title,
            "pub_date":pub_date,
            "description":description
        }
        r = requests.post(urlLB + "add", data=json.dumps(payload))
        print(r.text)

    if instruction == "DELETE":
        r = requests.delete(urlLB + "delete")
        print(r.text)

if __name__ == '__main__':
    main()