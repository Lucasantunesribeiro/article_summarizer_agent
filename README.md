# Article Summarizer Agent

**Resumo automático de artigos da web com bypass avançado de WAF (Cloudflare, DataCamp, etc). 100% open-source, pronto para deploy gratuito.**

---

## ✨ Descrição

O Article Summarizer Agent é uma aplicação Python que extrai, processa e resume artigos de qualquer site, mesmo aqueles protegidos por WAFs avançados (como Cloudflare). Utiliza técnicas modernas de scraping, Selenium stealth, fallback automático e geração de sumário em múltiplos formatos (txt, md, json).

- **Bypass de WAF**: Headers avançados, Selenium stealth, cloudscraper fallback
- **Resumo automático**: Métodos extractive, generative e híbrido
- **API RESTful** e interface web Flask
- **Pronto para deploy gratuito** (Render, Railway, Vercel, Deta, Codespaces)

---

## 🚀 Instalação Local

```bash
git clone https://github.com/Lucasantunesribeiro/article_summarizer_agent.git
cd article_summarizer_agent
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
```

---

## 🖥️ Como Usar Localmente

```bash
python main.py --url "https://www.datacamp.com/pt/blog/top-open-source-llms"
```

Ou rode a interface web:

```bash
python start_app.py
# Acesse http://localhost:5000
```

---

## 🧪 Testes

```bash
python test_datacamp_waf.py
python test_datacamp_selenium.py
python test_advanced_waf_bypass.py
```

---

## ☁️ Deploy Gratuito

### Render.com
1. Crie um novo serviço Web Service (Python)
2. Configure o build command: `pip install -r requirements.txt`
3. Configure o start command: `python start_app.py`
4. Adicione variáveis de ambiente se necessário

### Railway.app
1. Novo projeto > Deploy from GitHub
2. Start command: `python start_app.py`

### Vercel (com Python API)
- Use o Vercel Python template e adapte o start para `start_app.py`

### GitHub Codespaces
- Basta abrir o Codespace e rodar `python start_app.py`

---

## 📦 Estrutura de Pastas

```
article_summarizer_agent/
├── app.py                # Interface web Flask
├── main.py               # CLI principal
├── modules/              # Lógica de scraping, processamento, resumo
├── outputs/              # Saídas geradas (txt, md, json)
├── requirements.txt      # Dependências
├── test_*.py             # Testes automatizados
├── static/, templates/   # Frontend web
├── .cache/               # Cache local
└── ...
```

---

## 🛠️ Principais Dependências
- Flask
- Selenium, undetected-chromedriver, webdriver-manager
- cloudscraper, fake-useragent
- beautifulsoup4, requests, chardet
- scikit-learn, numpy, nltk
- transformers (opcional para resumo generativo)

---

## 🔑 Créditos
- Desenvolvido por [Lucasantunesribeiro](https://github.com/Lucasantunesribeiro)
- Inspiração: projetos open-source de scraping e NLP

## 📄 Licença
MIT License