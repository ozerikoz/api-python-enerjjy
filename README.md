
# EnerJJy API

A **EnerJJy API** é uma aplicação construída com **Flask** que fornece endpoints para gerenciamento de usuários e cálculo de impacto energético, integrando dados de localização e consumo energético para soluções sustentáveis.

---

## 📁 Estrutura do Projeto

```
api-python-enerjjy/
├── api/
│   ├── app.py              # Arquivo principal da aplicação Flask
│   ├── .env                # Variáveis de ambiente (não incluído no repositório)
│   ├── requirements.txt    # Lista de dependências
├── README.md               # Documentação do projeto
├── vercel.json             # Configuração da Vercel para deploy
```

---

## 🚀 Funcionalidades

### **Usuários**
- Criar usuários.
- Listar todos os usuários com seus respectivos endereços.
- Obter dados de um usuário específico.
- Atualizar dados do usuário e endereço.
- Deletar usuários e endereços associados.

### **Energia Solar**
- Calcular o impacto da energia solar com base no consumo energético e localização.
- Avaliar a viabilidade da instalação de painéis solares em determinada localização.

---

## ⚙️ Configuração e Uso

### **1. Acesso Público**
A API está disponível publicamente no seguinte endereço:

**Base URL**: [https://api-enerjjy.vercel.app/](https://api-enerjjy.vercel.app/)

### **1. Configuração Local**

1. Clone o repositório:
   ```bash
   git clone https://github.com/usuario/api-python-enerjjy.git
   cd api-python-enerjjy
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r api/requirements.txt
   ```

4. Configure as variáveis de ambiente no arquivo `.env` dentro da pasta `api`:
   ```plaintext
   ORACLE_DB_USER=seu_usuario
   ORACLE_DB_PASSWORD=sua_senha
   ORACLE_DB_HOST=localhost
   ORACLE_DB_PORT=1521
   ORACLE_DB_SID=seu_sid
   ```

5. Execute a aplicação localmente:
   ```bash
   flask run
   ```

6. Acesse a aplicação em [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 📖 Endpoints

### **Usuários**

- **POST `/users`**: Criar usuário.
  - **Body**:
    ```json
    {
      "cpf": "12345678901",
      "nome": "João Silva",
      "telefone": "11999999999",
      "email": "joao@example.com",
      "senha": "senha123",
      "cep": "01001000"
    }
    ```
  - **Resposta**:
    ```json
    {
      "message": "Usuário criado com sucesso",
      "id_usuario": 1
    }
    ```

- **GET `/users`**: Listar todos os usuários.
  - **Resposta**:
    ```json
    [
      {
        "id_usuario": 1,
        "cpf": "12345678901",
        "nome": "João Silva",
        "telefone": "11999999999",
        "email": "joao@example.com",
        "endereco": [
          {
            "logradouro": "Praça da Sé",
            "cep": "01001000",
            "bairro": "Sé",
            "cidade": "São Paulo",
            "estado": "SP"
          }
        ]
      }
    ]
    ```

- **GET `/users/<id_usuario>`**: Obter um usuário específico.
  - **Resposta**:
    ```json
    {
      "id_usuario": 1,
      "cpf": "12345678901",
      "nome": "João Silva",
      "telefone": "11999999999",
      "email": "joao@example.com",
      "endereco": [
        {
          "logradouro": "Praça da Sé",
          "cep": "01001000",
          "bairro": "Sé",
          "cidade": "São Paulo",
          "estado": "SP"
        }
      ]
    }
    ```

- **PUT `/users/<id_usuario>`**: Atualizar dados de um usuário.
  - **Body**:
    ```json
    {
      "cpf": "12345678901",
      "nome": "João Pedro",
      "telefone": "11999999998",
      "email": "joao.pedro@example.com",
      "senha": "novaSenha123",
      "cep": "01002000"
    }
    ```
  - **Resposta**:
    ```json
    {
      "message": "Usuário atualizado com sucesso"
    }
    ```

- **DELETE `/users/<id_usuario>`**: Remover um usuário.
  - **Resposta**:
    ```json
    {
      "message": "Usuário deletado com sucesso"
    }
    ```

---

### **Impacto Solar**

- **POST `/solar/impact`**: Calcular impacto solar.
  - **Body**:
    ```json
    {
      "energy_consumption": 500,
      "cep": "01001000"
    }
    ```
  - **Resposta**:
    ```json
    {
      "number_of_panels": 10,
      "panel_watts": 400,
      "panel_efficiency": "80%",
      "energy_generated_per_panel_monthly": 300.0,
      "co2_reduction_per_month": 450.0,
      "average_daily_radiation": 5
    }
    ```

- **POST `/solar/viability`**: Avaliar viabilidade solar.
  - **Body**:
    ```json
    {
      "cep": "01001000",
      "panel_efficiency": 0.8,
      "panel_output": 400
    }
    ```
  - **Resposta**:
    ```json
    {
      "start_date": "2024-08-01",
      "end_date": "2024-11-01",
      "month_average_energy_generation": 300.0,
      "day_average_solar_irradiance": 5.0,
      "viability": true
    }
    ```
