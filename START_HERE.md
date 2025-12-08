# 🚀 COMECE AQUI - Guia Rápido de Instalação

## ⚡ Instalação Rápida (3 passos)

### Windows:
1. Execute `install.bat` (duplo-clique)
2. Edite `config\config.py` com seus paths
3. Execute `run_app.bat` (duplo-clique)

### Linux/Mac:
1. Execute `./install.sh`
2. Edite `config/config.py` com seus paths
3. Execute `./run_app.sh`

## 🔑 Login Padrão
- Username: `admin`
- Password: `admin123`

## ⚠️ O QUE VOCÊ DEVE EDITAR

Abra o arquivo `config/config.py` e atualize estas 4 linhas:

```python
DIAGNOSIS_PATH = r"SEU_CAMINHO_AQUI\studyinfo_laterality_diagnosis.dta"
NOTES_PATH = r"SEU_CAMINHO_AQUI\ba746f39a1773233.parquet"
CROSS_PATH = r"SEU_CAMINHO_AQUI\slitlamp_crosswalk_complete_12082025.csv"
IMAGE_BASE_PATH = r"L:\SlitLamp"
```

## 📚 Documentação Completa

- **README.md** - Documentação completa do projeto
- **QUICKSTART.md** - Guia de início rápido
- **INSTALLATION_GUIDE.md** - Instruções detalhadas de instalação
- **TESTING_CHECKLIST.md** - Checklist de testes

## ✅ Após Instalar

1. Faça login como admin
2. Vá em Admin Dashboard → User Management
3. Crie contas para seus labelers
4. Atribua estratégias de rota diferentes para cada um
5. Comece a labelar!

## 🐛 Problemas?

- Verifique se editou os paths em `config/config.py`
- Verifique se os arquivos de dados existem
- Veja INSTALLATION_GUIDE.md para troubleshooting completo

Pronto para começar! 🎉
