# Setup inicial Python, Django, Django Rest Framework, Postgres e Pytest

## 🥞 Stack
- [Python v3.12](https://www.python.org/doc/)
- [Django v5.1.8](https://www.djangoproject.com/start/)
- [Django Rest Framework v3.16](https://www.django-rest-framework.org/)
- [Postgres v16.4](https://www.postgresql.org/docs/)
- [Pytest v8.3.5](https://docs.pytest.org/en/stable/)

## 🛠️ Configurando o projeto

Primeiro, clone o projeto:

### 🔄 via HTTPS
    $ git clone https://github.com/ollyvergithub/Django-DRF-Setup-Inicial.git

### 🔐 via SSH
    $ git@github.com:ollyvergithub/Django-DRF-Setup-Inicial.git

### 🐍 Criando e ativando uma virtual env
    $ python -m venv venv
    $ source venv/bin/activate  # Linux/macOS
    $ # ou venv\Scripts\activate no Windows

### 📦 Instalando as dependências do projeto
    $ pip install -r requirements/local.txt 

### 🗃️ Criando um banco do dados PostgreSQL usando createdb ou utilizando seu client preferido (pgAdmin, DBeaver...)
    $ createdb --username=postgres <project_slug>

> **_IMPORTANTE:_** Crie na raiz do projeto o arquivo _.env_ com base no .env.sample.
> Depois, em um terminal digite export DJANGO_READ_DOT_ENV_FILE=True e todas as variáveis serão lidas.

### ⚙️ Rodando as migrações
    $ python manage.py migrate

### 🚀 Executando o projeto
    $ python manage.py runserver

Feito tudo isso, o projeto estará executando no endereço [localhost:8000](http://localhost:8000).

### 👑 Opcional: Criando um super usuário
    $ python manage.py createsuperuser

### 🧪 Executando os testes com Pytest
    $ pytest

### 🧪 Executando a cobertura dos testes
    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

### 📄 Licença
Este projeto está sob a licença (sua licença) - veja o arquivo [LICENSE](./LICENSE) para detalhes.
