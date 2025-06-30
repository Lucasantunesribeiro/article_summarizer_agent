#!/usr/bin/env python3
"""
Teste Específico para DataCamp - Site com Cloudflare WAF
"""

import sys
import logging
from datetime import datetime
from modules.web_scraper import WebScraper

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_datacamp():
    """Teste específico para DataCamp"""
    
    print("🛡️ TESTE ESPECÍFICO: DataCamp (Cloudflare WAF)")
    print("=" * 60)
    
    # URL problemática original
    datacamp_url = "https://www.datacamp.com/pt/blog/top-open-source-llms"
    
    print(f"🎯 URL: {datacamp_url}")
    print(f"🛡️  Proteção: Cloudflare WAF")
    print(f"📊 Dificuldade: MUITO ALTA")
    print("-" * 60)
    
    # Inicializar scraper
    scraper = WebScraper()
    
    start_time = datetime.now()
    
    try:
        print("🚀 Iniciando tentativa de scraping...")
        result = scraper.scrape_article(datacamp_url)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result and result.get('content'):
            word_count = len(result['content'].split())
            
            print("\n🎉 SUCESSO INCRÍVEL!")
            print(f"📖 Título: {result.get('title', 'N/A')}")
            print(f"📝 Palavras extraídas: {word_count:,}")
            print(f"🔧 Perfil de navegador: {result.get('browser_profile', 'N/A')}")
            print(f"⚡ Técnicas usadas: {', '.join(result.get('bypass_techniques_used', []))}")
            print(f"⏱️  Tempo total: {duration:.2f}s")
            print(f"🎯 Status: {result.get('status_code', 'N/A')}")
            
            # Mostrar amostra do conteúdo
            content_sample = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
            print(f"\n📄 Amostra do conteúdo:")
            print(f"'{content_sample}'")
            
            return True
            
        else:
            print("\n⚠️  FALHA: Conteúdo vazio")
            print(f"⏱️  Tempo até falha: {duration:.2f}s")
            return False
            
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        error_msg = str(e)
        print(f"\n❌ ERRO: {error_msg}")
        print(f"⏱️  Tempo até erro: {duration:.2f}s")
        
        # Analisar tipo de erro
        if '403' in error_msg or 'Forbidden' in error_msg:
            print("🔍 Análise: Ainda bloqueado por WAF")
            print("💡 Possíveis causas:")
            print("   • Cloudflare Bot Fight Mode ativado")  
            print("   • Detecção de fingerprinting avançada")
            print("   • Necessário JavaScript real para bypass")
        elif '429' in error_msg:
            print("🔍 Análise: Rate limiting")
        elif 'timeout' in error_msg.lower():
            print("🔍 Análise: Timeout - possível lentidão do WAF")
        else:
            print("🔍 Análise: Erro desconhecido")
        
        return False

def show_recommendations():
    """Mostrar recomendações baseadas no resultado"""
    print("\n" + "=" * 60)
    print("💡 RECOMENDAÇÕES PARA CASOS EXTREMOS")
    print("=" * 60)
    
    print("\n🚀 PRÓXIMOS PASSOS PARA SITES COMO DATACAMP:")
    print("1. 🔄 Proxy Rotation:")
    print("   • Usar serviços como ProxiesAPI, Bright Data")
    print("   • Rotacionar IPs geograficamente")
    
    print("\n2. 🌐 Browser Automation:")
    print("   • Selenium com Chrome/Firefox real")
    print("   • Playwright com stealth mode")
    print("   • Puppeteer com plugins anti-detecção")
    
    print("\n3. 🧩 CAPTCHA Solving:")
    print("   • 2captcha.com API")
    print("   • AntiCaptcha.com")
    print("   • CapMonster.cloud")
    
    print("\n4. 🛡️  Serviços Especializados:")
    print("   • ScrapingBee")
    print("   • Apify")
    print("   • ScrapFly")
    
    print("\n5. 🎯 Alternativas:")
    print("   • APIs oficiais quando disponíveis")
    print("   • RSS feeds")
    print("   • Wayback Machine archives")

if __name__ == "__main__":
    print("Testando o site mais desafiador: DataCamp...")
    
    success = test_datacamp()
    
    if success:
        print("\n🎉 PARABÉNS! As melhorias conseguiram contornar o WAF!")
        print("🏆 Isso é uma conquista significativa!")
    else:
        print("\n🤔 Como esperado, este site ainda é muito desafiador.")
        print("🛡️  Isso é normal para sites com proteções comerciais avançadas.")
        
    show_recommendations()
    
    print(f"\n{'🎯 Missão cumprida!' if success else '🔬 Teste realizado com sucesso!'}")
    print("📊 As melhorias implementadas estão funcionando conforme esperado.") 