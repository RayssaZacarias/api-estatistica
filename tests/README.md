

---

# 📊 API de Estatística e Análise de Dados

API REST desenvolvida em **FastAPI** utilizando **Python 3.12** para cálculos estatísticos, processamento de dados e geração de visualizações gráficas.

---

## 🛠️ Tecnologias Utilizadas

| Categoria | Tecnologias |
| --- | --- |
| **Linguagem** | Python 3.12 |
| **Framework Web** | FastAPI, Uvicorn |
| **Processamento Numérico** | Pandas, NumPy, SciPy |
| **Visualização** | Plotly, Matplotlib |
| **Validação** | Pydantic |

---

## 📋 Pré-requisitos

* **Python 3.12+** instalado
* **Git** instalado

---

## 🚀 Como Configurar e Rodar o Projeto

### 1. Clonar o Repositório

```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd Api-estatistica

```

### 2. Criar o Ambiente Virtual (.venv)

* **Windows:**

```bash
python -m venv .venv

```

* **Linux / macOS:**

```bash
python3 -m venv .venv

```

### 3. Ativar o Ambiente Virtual (.venv)

* **Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1

```

* **Windows (CMD / Prompt de Comando):**

```cmd
.venv\Scripts\activate.bat

```

* **Linux / macOS:**

```bash
source .venv/bin/activate

```

> **Aviso:** O prefixo `(.venv)` deve aparecer no início da linha do terminal após a ativação.

### 4. Instalar as Dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt

```

---

## 💻 Como Iniciar o Servidor

```bash
uvicorn app.main:app --reload

```

> **Nota:** Caso o seu arquivo principal esteja na raiz do projeto (fora de `app/`), use:
> ```bash
> uvicorn main:app --reload
> 
> ```
> 
> 

Acesse a API em: **http://127.0.0.1:8000**

---

## 📖 Documentação Interativa

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Testes Automatizados

```bash
pytest

```

---

## 🛑 Como Desativar a Venv

```bash
deactivate

```
