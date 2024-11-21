from flask import Flask, request, jsonify
import oracledb
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

load_dotenv()

# conexão global ao banco de dados
def get_db_connection():
    connection = oracledb.connect(
        user = os.getenv("ORACLE_DB_USER"),
        password = os.getenv("ORACLE_DB_PASSWORD"),
        host = os.getenv("ORACLE_DB_HOST"),
        port = os.getenv("ORACLE_DB_PORT"),
        sid = os.getenv("ORACLE_DB_SID")
    )
    
    return connection

# função para pegar dados de endereço a partir do CEP usando a API ViaCEP
def fetch_address_from_cep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            address_data = response.json()
            if "erro" in address_data:
                return None
            return {
                "logradouro": address_data.get("logradouro"),
                "bairro": address_data.get("bairro"),
                "cidade": address_data.get("localidade"),
                "estado": address_data.get("uf"),
            }
        return None
    except Exception as e:
        raise Exception(f"Erro ao consultar o ViaCEP: {str(e)}")

@app.route("/")
def home():
    return jsonify({"message": "API EnerJJy - Bem-vindo!"}), 200

# endpoint para criar um usuário
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    # validação de entradas
    required_fields = ["cpf", "nome", "telefone", "email", "senha", "cep"]
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Os seguintes campos são obrigatórios: {', '.join(missing_fields)}"}), 400

    # verificar se o CPF ou email já existe
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1 FROM tbl_usuarios WHERE cpf = :1 OR email = :2
            """,
            [data["cpf"], data["email"]]
        )
        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({"error": "Usuário com este CPF ou email já existe"}), 409

    except Exception as e:
        return jsonify({"error": f"Erro ao verificar usuário existente: {str(e)}"}), 500

    # consulta o ViaCEP para preencher o endereço
    try:
        address = fetch_address_from_cep(data["cep"])
        if not address:
            return jsonify({"error": "CEP inválido ou não encontrado no ViaCEP"}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar endereço no ViaCEP: {str(e)}"}), 500

    try:
        # inserir o usuário
        cursor.execute(
            """
            INSERT INTO tbl_usuarios (cpf, nome, telefone, email, senha) 
            VALUES (:1, :2, :3, :4, :5)
            """,
            [data["cpf"], data["nome"], data["telefone"], data["email"], data["senha"]]
        )
        connection.commit()

        # consultar o ID do usuário recém-inserido
        cursor.execute(
            """
            SELECT id_usuario FROM tbl_usuarios WHERE cpf = :1
            """,
            [data["cpf"]]
        )
        id_usuario = cursor.fetchone()
        if not id_usuario:
            return jsonify({"error": "Erro ao recuperar ID do usuário após inserção"}), 500

        id_usuario_value = id_usuario[0]

        # inserir o endereço associado ao usuário
        cursor.execute(
            """
            INSERT INTO tbl_enderecos (logradouro, cep, bairro, cidade, estado, id_usuario) 
            VALUES (:1, :2, :3, :4, :5, :6)
            """,
            [
                address["logradouro"],
                data["cep"],
                address["bairro"],
                address["cidade"],
                address["estado"],
                id_usuario_value
            ]
        )

        connection.commit()
        return jsonify({"message": "Usuário criado com sucesso", "id_usuario": id_usuario_value}), 201
    except Exception as e:
        return jsonify({"error": f"Erro ao criar usuário: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# endpoint de login para autenticar o usuario
@app.route("/users/login", methods=["POST"])
def login():
    data = request.get_json()

    # Validação de entradas
    if not data.get("email") or not data.get("senha"):
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    email = data["email"]
    senha = data["senha"]

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Verificar se o email e a senha estão corretos
        cursor.execute(
            """
            SELECT u.id_usuario, u.cpf, u.nome, u.telefone, u.email, 
                   e.logradouro, e.cep, e.bairro, e.cidade, e.estado
            FROM tbl_usuarios u
            LEFT JOIN tbl_enderecos e ON u.id_usuario = e.id_usuario
            WHERE u.email = :1 AND u.senha = :2
            """,
            [email, senha]
        )
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": "Email ou senha inválidos"}), 401

        # Construir o objeto do usuário
        user = {
            "id_usuario": rows[0][0],
            "cpf": rows[0][1],
            "nome": rows[0][2],
            "telefone": rows[0][3],
            "email": rows[0][4],
            "endereco": []
        }

        for row in rows:
            if row[5]:  # Verificar se o endereço está presente
                user["endereco"].append({
                    "logradouro": row[5],
                    "cep": row[6],
                    "bairro": row[7],
                    "cidade": row[8],
                    "estado": row[9]
                })

        return jsonify(user), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao processar login: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# endpoint para listar todos os usuários
@app.route("/users", methods=["GET"])
def list_users():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT u.id_usuario, u.cpf, u.nome, u.telefone, u.email, 
                   e.logradouro, e.cep, e.bairro, e.cidade, e.estado
            FROM tbl_usuarios u
            LEFT JOIN tbl_enderecos e ON u.id_usuario = e.id_usuario
        """)
        rows = cursor.fetchall()

        if not rows:
            return jsonify([]), 200

        users = {}
        for row in rows:
            user_id = row[0]
            if user_id not in users:
                users[user_id] = {
                    "id_usuario": row[0],
                    "cpf": row[1],
                    "nome": row[2],
                    "telefone": row[3],
                    "email": row[4],
                    "endereco": []
                }
            if row[5]:
                users[user_id]["endereco"].append({
                    "logradouro": row[5],
                    "cep": row[6],
                    "bairro": row[7],
                    "cidade": row[8],
                    "estado": row[9]
                })

        return jsonify(list(users.values())), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao listar usuários: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# endpoint para buscar um usuário
@app.route("/users/<int:id_usuario>", methods=["GET"])
def get_user(id_usuario):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT u.id_usuario, u.cpf, u.nome, u.telefone, u.email, 
                   e.logradouro, e.cep, e.bairro, e.cidade, e.estado
            FROM tbl_usuarios u
            LEFT JOIN tbl_enderecos e ON u.id_usuario = e.id_usuario
            WHERE u.id_usuario = :1
        """, [id_usuario])
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"error": "Usuário não encontrado"}), 404

        user = {
            "id_usuario": rows[0][0],
            "cpf": rows[0][1],
            "nome": rows[0][2],
            "telefone": rows[0][3],
            "email": rows[0][4],
            "endereco": []
        }
        for row in rows:
            if row[5]:
                user["endereco"].append({
                    "logradouro": row[5],
                    "cep": row[6],
                    "bairro": row[7],
                    "cidade": row[8],
                    "estado": row[9]
                })

        return jsonify(user), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar usuário: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# endpoint para atualizar um usuário
@app.route("/users/<int:id_usuario>", methods=["PUT"])
def update_user(id_usuario):
    data = request.get_json()

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # atualizar dados do usuário
        cursor.execute("""
            UPDATE tbl_usuarios
            SET cpf = :1, nome = :2, telefone = :3, email = :4, senha = :5
            WHERE id_usuario = :6
        """, [
            data.get("cpf"),
            data.get("nome"),
            data.get("telefone"),
            data.get("email"),
            data.get("senha"),
            id_usuario
        ])

        # atualizar endereço, se o CEP foi fornecido
        if "cep" in data:
            address = fetch_address_from_cep(data["cep"])
            if not address:
                return jsonify({"error": "CEP inválido ou não encontrado no ViaCEP"}), 400

            cursor.execute("""
                UPDATE tbl_enderecos
                SET logradouro = :1, cep = :2, bairro = :3, cidade = :4, estado = :5
                WHERE id_usuario = :6
            """, [
                address["logradouro"],
                data["cep"],
                address["bairro"],
                address["cidade"],
                address["estado"],
                id_usuario
            ])

        connection.commit()
        return jsonify({"message": "Usuário atualizado com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar usuário: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# endpoint para deletar um usuário
@app.route("/users/<int:id_usuario>", methods=["DELETE"])
def delete_user(id_usuario):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM tbl_usuarios WHERE id_usuario = :1", [id_usuario])
        if cursor.rowcount == 0:
            return jsonify({"error": "Usuário não encontrado"}), 404

        connection.commit()
        return jsonify({"message": "Usuário deletado com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao deletar usuário: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

# função para pegar as coordenadas (latitude e longitude) de um CEP usando a API Nominatim do OpenStreetMap
def get_coordinates_from_cep(cep):
    url = " https://nominatim.openstreetmap.org/search?"
    
    # parâmetros da API
    params = {
        'format': 'json',
        'postalcode': cep,
        'countrycodes': ['BR'],
        'limit': 1
    }
    
    # cabeçalho para simular um navegador, evitando bloqueio por parte do servidor
    headers = {
        'User-Agent': 'Mozilla/5.0 (EnerJJy - Academic project website; Contact: erik.paschoalatto1@gmail.com)'  
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        results = response.json()
        
        if results:
            lat = float(results[0]['lat'])
            lon = float(results[0]['lon'])
            
            return {"lat": lat, "lon": lon}
        else:
            return None
        
    except Exception as e:
        raise Exception(f"Erro ao obter coordenadas: {str(e)}")

# função para obter a radiação solar diária média em um ponto geográfico
def get_solar_radiation(latitude, longitude, start=None, end=None):
    # configura as datas de início e fim se não forem fornecidas
    if not start or not end:
        today = datetime.now()
        end = today.strftime('%Y%m%d')
        start = (today - timedelta(days=90)).strftime('%Y%m%d')
    
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        'parameters': 'ALLSKY_SFC_SW_DWN',
        'community': 'RE',
        'longitude': longitude,
        'latitude': latitude,
        'start': start,
        'end': end,
        'format': 'JSON'
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            daily_radiation = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
            valid_values = [float(value) for value in daily_radiation.values() if float(value) > -999.0]
            if valid_values:
                avg_radiation = sum(valid_values) / len(valid_values)
                return avg_radiation
            else:
                return None
    except Exception as e:
        raise Exception(f"Erro ao obter média de radiação solar: {str(e)}")

# função para calcular o impacto da energia solar em um local
def calculate_solar_impact(energy_consumption, cep, start=None, end=None):
    try:
        coords = get_coordinates_from_cep(cep)
        
        radiation = get_solar_radiation(coords["lat"], coords["lon"], start, end)

        if radiation is None:
            return {"error": "Não foi possível obter a radiação solar"}
        
        panel_efficiency = 0.8  # 80%
        panel_output = 400  # watts por painel

        # calcula a produção diária e mensal por painel
        daily_output_per_panel = panel_output * radiation / 1000  # convertendo watts para kWh considerando a radiação
        daily_energy_generated_per_panel = daily_output_per_panel * panel_efficiency
        monthly_energy_generated_per_panel = daily_energy_generated_per_panel * 30  # cálculo mensal

        if monthly_energy_generated_per_panel <= 0:
            return {"error": "A radiação solar resultou em produção de energia nula ou negativa."}

        number_of_panels = energy_consumption / monthly_energy_generated_per_panel # cálculo do número de painéis
        co2_reduction_per_month = energy_consumption * 0.9  # kg de CO2 por kWh

        return {
            "number_of_panels": int(number_of_panels),
            "panel_watts": int(panel_output),
            "panel_efficiency": f"{int(panel_efficiency * 100)}%",
            "energy_generated_per_panel_monthly": round(monthly_energy_generated_per_panel, 2),
            "co2_reduction_per_month": round(co2_reduction_per_month, 2),
            "average_daily_radiation": round(radiation)
        }
    except Exception as e:
        return {"error": f"Erro no cálculo da produção de energia: {str(e)}"}

# função para avaliar a viabilidade da energia solar em um local
def evaluate_solar_viability(cep, panel_efficiency, panel_output):
    try:
        # obtém latitude e longitude a partir do CEP
        coords = get_coordinates_from_cep(cep)

        # define o período analisado (últimos 90 dias)
        today = datetime.now()
        start = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        end = today.strftime('%Y-%m-%d')

        # obtém a média de radiação solar para as coordenadas obtidas
        average_radiation = get_solar_radiation(coords["lat"], coords["lon"])

        # realiza o cálculo da geração de energia
        hours_of_sunlight_per_day = 5  # média de horas de sol por dia
        daily_output_per_panel = (panel_output * average_radiation * hours_of_sunlight_per_day * panel_efficiency) / 1000
        monthly_output_per_panel = daily_output_per_panel * 30

        # estabelece o limiar de viabilidade
        minimum_viable_output = 120  # kWh/mês
        viability = monthly_output_per_panel >= minimum_viable_output 

        return {
            "start_date": start,
            "end_date": end,
            "month_average_energy_generation": round(monthly_output_per_panel, 2),
            "day_average_solar_irradiance": round(average_radiation, 2),
            "viability": viability
        }
        
    except Exception as e:
        # Trata exceções inesperadas
        return {"error": f"Unexpected error occurred: {str(e)}"}

# endpoint para calcular o impacto da energia solar
@app.route("/solar/impact", methods=["POST"])
def solar_impact():
    data = request.get_json()
    if not data.get("energy_consumption") or not data.get("cep"):
        return jsonify({"error": "Consumo de energia e CEP são obrigatórios"}), 400

    energy_consumption = data.get("energy_consumption")
    cep = data.get("cep")

    result = calculate_solar_impact(energy_consumption, cep)
    return jsonify(result), 200

# endpoint para avaliar a viabilidade da energia solar
@app.route("/solar/viability", methods=["POST"])
def solar_viability():
    data = request.get_json()
    if not data.get("cep") or not data.get("panel_efficiency") or not data.get("panel_output"):
        return jsonify({"error": "CEP, eficiência do painel e saída do painel são obrigatórios"}), 400

    cep = data.get("cep")
    panel_efficiency = data.get("panel_efficiency")
    panel_output = data.get("panel_output")

    result = evaluate_solar_viability(cep, panel_efficiency, panel_output)
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(debug=True)