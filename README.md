# ProjetoCloud
Repositorio de códigos de referência para o projeto final de Computação em Nuvem 2020.2

O projeto consiste em um sistema ORM multi-cloud com Load Balancer e Autoscalling. Ele está dividido em duas etapas. A primeira é a implantação do script `main.py` que faz a preparação e setup dos ambientes em Ohio e North Virginia. A segunda é uma aplicação cliente `client.py` que faz comunicação com o sistema implantado.

O passo 0, é criar um arquivo `.env` e anexá-lo na mesma pasta onde foi clonado este repositório, para permitir trabalhar com os serviços disponibilizados pela AWS. O arquivo deve conter o ACCESS-KEY e a SECRET-KEY geradas com a criação da conta e seguir o seguinte formato:

```
ACCESS-KEY={}
SECRET-KEY={} 
``` 

Antes de executar o serviço, é necessário preparar o ambiente multi-cloud. Para tal, rode o script `main.py` com o comando abaixo e acompanhe a preparação dos ambientes. Ele criará uma instância em Ohio usando a plataforma e instalará um banco de dados POSTGRESQL nela. Em seguida, ele criará uma segunda instância em North Virginia e instalará o ORM nessa máquina apontando para o database criado em Ohio. Por fim, ele subirá um LoadBalancer e um AutoScaling para suportarem o serviço estruturado.

```
python3 main.py
```
Aguarde o ambiente estar 100% preparado e acompanhe por meio do console da AWS. Feito isso, é possível usar o `client.py` para consumir os endpoints do terminal. O DB permite 3 funcionalidades:
* Listar as todas as Tasks existentes no banco de dados (GET);
* Adicionar uma Task nova ao banco de dados (POST);
* Deletar todas as Tasks existentes no banco de dados (DELETE).

Os comandos para usar o client são:

```
python3 client.py -i GET
python3 client.py -i POST -t "{título da task}" -d "{descrição da task}"
python3 client.py -i DELETE
```