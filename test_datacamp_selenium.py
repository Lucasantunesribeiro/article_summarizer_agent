#!/usr/bin/env python3
"""
Teste Específico para DataCamp com Selenium Integrado
Sistema com fallback automático para sites com WAF avançado
"""

import sys
import logging
import time
from datetime import datetime
from modules.web_scraper import WebScraper

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('selenium_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_datacamp_selenium():
    """Teste específico para DataCamp com Selenium"""
    
    print("🎯" + "="*80)
    print("🛡️  TESTE DATACAMP COM SELENIUM INTEGRADO")
    print("🚀 Sistema com fallback automático para WAF avançado")
    print("="*80)
    
    # URL problemática original
    datacamp_url = "https://www.datacamp.com/pt/blog/top-open-source-llms"
    
    print(f"\n📊 Detalhes do Teste:")
    print(f"🎯 URL: {datacamp_url}")
    print(f"🛡️  Proteção: Cloudflare WAF")
    print(f"📊 Dificuldade: MUITO ALTA")
    print(f"🔧 Método: Requests → Selenium (fallback automático)")
    print("-" * 80)
    
    # Inicializar scraper
    scraper = WebScraper()
    
    start_time = datetime.now()
    
    try:
        print(f"\n🚀 Iniciando teste às {start_time.strftime('%H:%M:%S')}")
        
        # O sistema tentará requests primeiro, depois Selenium automaticamente
        result = scraper.scrape_article(datacamp_url)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ SUCESSO! Tempo total: {duration:.1f}s")
        print("=" * 80)
        
        # Mostrar resultados
        print(f"📰 Título: {result.get('title', 'N/A')}")
        print(f"👤 Autor: {result.get('author', 'N/A')}")
        print(f"📅 Data: {result.get('publish_date', 'N/A')}")
        print(f"📝 Descrição: {result.get('description', 'N/A')[:100]}...")
        print(f"📊 Palavras: {result.get('word_count', 0)}")
        print(f"🔧 Método: {result.get('extraction_method', 'N/A')}")
        
        # Verificar se usou Selenium
        if 'selenium' in result.get('extraction_method', '').lower():
            print("🎉 SELENIUM FUNCIONOU! WAF foi contornado com sucesso!")
        else:
            print("📡 Requests funcionou! Site não bloqueou.")
        
        print("\n📝 Prévia do conteúdo:")
        print("-" * 40)
        content_preview = result.get('content', '')[:500]
        print(content_preview)
        if len(result.get('content', '')) > 500:
            print("... (truncado)")
        
        return True
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n❌ FALHOU após {duration:.1f}s")
        print(f"🚨 Erro: {str(e)}")
        print("=" * 80)
        
        # Análise do erro
        error_msg = str(e).lower()
        if "403" in error_msg or "forbidden" in error_msg:
            print("🛡️  Diagnóstico: WAF ainda está bloqueando")
            print("💡 Sugestões:")
            print("   - Aguarde alguns minutos e tente novamente")
            print("   - Verifique se o Chrome está instalado")
            print("   - Tente com outro site primeiro")
        elif "selenium" in error_msg:
            print("🔧 Diagnóstico: Problema com Selenium")
            print("💡 Sugestões:")
            print("   - Instale: pip install selenium webdriver-manager undetected-chromedriver")
            print("   - Verifique se o Chrome está instalado")
        else:
            print("🤔 Diagnóstico: Erro desconhecido")
        
        return False

def test_simple_site():
    """Teste com um site mais simples primeiro"""
    
    print("\n🧪 Teste com site simples para verificar funcionamento:")
    print("-" * 50)
    
    simple_url = "https://httpbin.org/user-agent"
    scraper = WebScraper()
    
    try:
        result = scraper.scrape_article(simple_url)
        print(f"✅ Site simples funcionou: {result.get('title', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Site simples falhou: {e}")
        return False

def main():
    """Função principal"""
    
    print("🔧 Verificando sistema...")
    
    # Testar com site simples primeiro
    if not test_simple_site():
        print("⚠️  Sistema com problemas básicos - verifique instalação")
        return
    
    # Testar DataCamp
    success = test_datacamp_selenium()
    
    if success:
        print("\n🎉 MISSÃO CUMPRIDA!")
        print("✅ Sistema funcionando com Selenium integrado")
        print("🛡️  WAF contornado com sucesso")
    else:
        print("\n🤔 Teste não passou completamente")
        print("💡 Veja as sugestões acima")

if __name__ == "__main__":
    main() 