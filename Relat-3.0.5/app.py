from flask import Flask, render_template, request
from datetime import datetime
import requests
from html import unescape
from bs4 import BeautifulSoup
import mysql.connector

app = Flask(__name__)

# Variáveis globais
GLPI_API_URL = 'https://suporte.riole.com.br/apirest.php'
APP_TOKEN = 'MrMjQDChr5f8MGJYnqY9AMwpzY1nonqDVcVkm5y4'    
USER_TOKEN = 'ofveJNg4NL298WaEJUrpbWVLtN4LuIgaaL0jPLej'

def iniciar_sessao():
    headers = {
        'Authorization': f'user_token {USER_TOKEN}',
        'App-Token': APP_TOKEN
    }
    response = requests.get(f'{GLPI_API_URL}/initSession', headers=headers)
    if response.status_code != 200:
        raise Exception("Erro ao iniciar sessão: " + str(response.json()))
    return response.json().get("session_token")

def conectar_banco():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='glpi',
            password='Riole001',
            database='glpi'
        )
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None
    
def registrar_data_emissao():
    # Gera a data e hora atuais no formato desejado
    return datetime.now().strftime('%Y/%m/%d - %H:%M')

def buscar_dados_chamado(session_token, id_chamado):
    headers = {
        'Authorization': f'user_token {USER_TOKEN}',
        'App-Token': APP_TOKEN,
        'Session-Token': session_token
    }
    
    
    # Busca os dados do chamado
    response = requests.get(f'{GLPI_API_URL}/Ticket/{id_chamado}', headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar chamado {id_chamado}: {response.json()}")

    ticket_data = response.json()
    
    # Verifica se há um 'users_id_lastupdater'
    users_id_lastupdater = ticket_data.get('users_id_lastupdater', None)
    
    if users_id_lastupdater:
        # Busca o nome do técnico que fez a última alteração
        response_user = requests.get(f'{GLPI_API_URL}/User/{users_id_lastupdater}', headers=headers)
        
        if response_user.status_code == 200:
            user_data = response_user.json()
            # Inclui o nome do técnico nos dados do chamado
            ticket_data['last_updater_name'] = user_data.get('name', 'Não especificado')
        else:
            ticket_data['last_updater_name'] = 'Não especificado'
    else:
        ticket_data['last_updater_name'] = 'Não especificado'
    
    # Verifica se há um 'requesttypes_id'
    requesttypes_id = ticket_data.get('requesttypes_id', None)
    
    if requesttypes_id:
        # Busca o nome do tipo de requisição
        response_request_type = requests.get(f'{GLPI_API_URL}/RequestType/{requesttypes_id}', headers=headers)
        
        if response_request_type.status_code == 200:
            request_type_data = response_request_type.json()
            # Inclui o nome do tipo de requisição nos dados do chamado
            ticket_data['request_type_name'] = request_type_data.get('name', 'Não especificado')
        else:
            ticket_data['request_type_name'] = 'Não especificado'
    else:
        ticket_data['request_type_name'] = 'Não especificado'
    
    return ticket_data




def imprimir_dados_chamado(ticket_id):
    try:
        # Inicia a sessão com o GLPI
        session_token = iniciar_sessao()

        # Obtém os dados do ticket
        ticket_data = buscar_dados_chamado(session_token, ticket_id)

        # Imprime todos os dados retornados pelo GLPI
        print("Dados do Ticket:")
        for key, value in ticket_data.items():
            # Verifica se o valor é um dicionário ou lista para detalhar ainda mais
            if isinstance(value, dict):
                print(f"{key}:")
                for subkey, subvalue in value.items():
                    print(f"    {subkey}: {subvalue}")
            elif isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"    {item}")
            else:
                print(f"{key}: {value}")

    except Exception as e:
        print(f"Erro ao imprimir dados do chamado: {e}")

def buscar_dados_propriedade(ticket_id):
    print(registrar_data_emissao)
    connection = conectar_banco()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM glpi.glpi_plugin_fields_ticketinformaes WHERE items_id = %s", (ticket_id,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return {
                    'Descrição do Técnico': limpar_html(unescape(result[4])) if len(result) > 4 and result[4] else 'Não disponível',
                    'Ação Realizada': limpar_html(unescape(result[5])) if len(result) > 5 and result[5] else 'Não disponível',
                    # 'Causa do Problema': limpar_html(unescape(result[6])) if len(result) > 6 and result[6] else 'Não disponível',
                    'Observação Interna': limpar_html(unescape(result[6])) if len(result) > 6 and result[6] else 'Não disponível',
                    # 'Solução de Contorno': limpar_html(unescape(result[9])) if len(result) > 9 and result[9] else 'Não disponível',
                    'Solução': limpar_html(unescape(result[8])) if len(result) > 8 and result[8] else 'Não disponível'
                }
            else:
                return "Nenhum dado encontrado para o ticket."
        except mysql.connector.Error as err:
            print(f"Erro ao executar a consulta: {err.msg}")
            return "Erro ao buscar dados de propriedade."
        finally:
            connection.close()
    return "Erro de conexão ao banco de dados"

def limpar_html(content):
    # Utiliza BeautifulSoup para remover tags HTML e retornar texto limpo
    soup = BeautifulSoup(content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def extrair_dados_do_html(content):
    # Substitui entidades HTML
    content = content.replace('&lt;', '<').replace('&gt;', '>') 
    content = content.replace('&#60;', '<').replace('&#62;', '>')  
    content = content.replace('&nbsp;', ' ')  # Substitui espaços não quebráveis
    content = unescape(content)  # Desencapsula entidades HTML
    soup = BeautifulSoup(content, 'html.parser')

    print("Conteúdo HTML após limpeza:", content)  # Debugging: exibe conteúdo após a limpeza
    
    campos = {
        # Campos para o primeiro formato
        '1) Cliente: :': 'cliente_nome',  # Ajustado para dois pontos
        '2) Requerente: :': 'requerente_nome',  # Ajustado para dois pontos
        '3) Titulo: :': 'titulo_chamado',  # Ajustado para dois pontos
        '4) Setor que trabalha: :': 'solicitante_setor',  # Ajustado para dois pontos
        '5) Cargo: :': 'solicitante_cargo',  # Ajustado para dois pontos
        '6) Email: :': 'solicitante_email',  # Ajustado para dois pontos
        '7) Celular: :': 'solicitante_celular',  # Ajustado para dois pontos
        '8) Descrição do Solicitante: :': 'descricao_solicitante',  # Ajustado para dois pontos
        # Campos para o segundo formato
        '1) Nome do Requerente:': 'requerente_nome',  # Apenas um ponto
        '2) Setor que trabalha:': 'solicitante_setor',  # Apenas um ponto
        '3) Cargo:': 'solicitante_cargo',  # Apenas um ponto
        '4) Descreva detalhadamente como podemos ajudar:': 'descricao_solicitante',
        '5) Agende o suporte:': 'agendar_suporte'
    }
    
    dados_extraidos = {}

    # Percorre cada campo e extrai os dados
    for div in soup.find_all('div'):
        for texto, chave in campos.items():
            if texto in div.text:
                try:
                    # Pega o conteúdo após o texto específico e remove espaços
                    valor = div.text.split(':', 2)[-1].strip()  # Pega tudo após o segundo ':' e remove espaços
                    dados_extraidos[chave] = valor
                    break  # Se encontrar o campo, não precisa continuar verificando
                except IndexError:
                    print(f"Erro ao processar o texto: {div.text}")  # Log de erro para debugar

    return dados_extraidos

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ticket_id = request.form['ticket_id']
        
        session_token = iniciar_sessao()
        
        try:
            ticket_data = buscar_dados_chamado(session_token, ticket_id)

            # Dados principais do chamado
            dados_chamado = {
                'ticket_id': ticket_data['id'],
                'ticket_name': ticket_data['name'],
                'ticket_creation_date': ticket_data['date'],
                'ticket_request_type': ticket_data.get('requesttypes_id', 'Não especificado'),
                'ticket_last_updater_name': ticket_data.get('last_updater_name', 'Não especificado'),  # Nome do técnico
                'ticket_request_type_name': ticket_data.get('request_type_name', 'Não especificado'),  # Nome do técnico
                'data_emissao': registrar_data_emissao()  # Adiciona a data e hora de emissão
            }

            # Extrair dados do solicitante a partir do HTML
            dados_extraidos = extrair_dados_do_html(ticket_data['content'])

            # Chamar a função para buscar dados de propriedade
            dados_propriedade = buscar_dados_propriedade(ticket_id)

            # Mesclar todos os dados
            dados_extraidos.update(dados_chamado)
            dados_extraidos.update(dados_propriedade)

            return render_template('result.html', ticket_data=dados_extraidos)
        except Exception as e:
            return str(e)    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)