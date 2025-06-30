#!/usr/bin/env python3
"""
Teste das Funcionalidades Avançadas de Contorno de WAF
Script para testar as melhorias implementadas no web scraper
"""

import sys
import logging
from datetime import datetime
from modules.web_scraper import WebScraper

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_advanced_waf_bypass():
    """Teste das funcionalidades avançadas de contorno de WAF"""
    
    print("=" * 80)
    print("🛡️  TESTE DE CONTORNO AVANÇADO DE WAF")
    print("🚀 Testando as novas funcionalidades implementadas")
    print("=" * 80)
    
    # URLs para teste (incluindo sites com proteções rigorosas)
    test_urls = [
        {
            'url': 'https://www.datacamp.com/pt/blog/top-open-source-llms',
            'name': 'DataCamp (Cloudflare WAF)',
            'expected_difficulty': 'MUITO ALTO'
        },
        {
            'url': 'https://realpython.com/python-web-scraping-practical-introduction/',
            'name': 'Real Python',
            'expected_difficulty': 'MÉDIO'
        },
        {
            'url': 'https://httpbin.org/user-agent',
            'name': 'HTTPBin User-Agent Test',
            'expected_difficulty': 'BAIXO'
        },
        {
            'url': 'https://www.cloudflare.com/learning/bots/what-is-a-bot/',
            'name': 'Cloudflare Learning (WAF)',
            'expected_difficulty': 'ALTO'
        },
        {
            'url': 'https://blog.cloudflare.com/bot-management-machine-learning/',
            'name': 'Cloudflare Blog (WAF)',
            'expected_difficulty': 'ALTO'
        }
    ]
    
    # Inicializar o scraper avançado
    scraper = WebScraper()
    
    results = []
    
    for i, test_case in enumerate(test_urls, 1):
        url = test_case['url']
        name = test_case['name']
        difficulty = test_case['expected_difficulty']
        
        print(f"\n🔍 TESTE {i}/5: {name}")
        print(f"🎯 URL: {url}")
        print(f"📊 Dificuldade Esperada: {difficulty}")
        print("-" * 60)
        
        start_time = datetime.now()
        
        try:
            # Tentar fazer o scraping
            result = scraper.scrape_article(url)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Verificar se houve sucesso
            if result and result.get('content'):
                word_count = len(result['content'].split())
                
                print(f"✅ SUCESSO!")
                print(f"📖 Título: {result.get('title', 'N/A')[:80]}...")
                print(f"📝 Palavras extraídas: {word_count:,}")
                print(f"🔧 Perfil de navegador usado: {result.get('browser_profile', 'N/A')}")
                print(f"⚡ Técnicas usadas: {', '.join(result.get('bypass_techniques_used', []))}")
                print(f"⏱️  Tempo: {duration:.2f}s")
                
                results.append({
                    'name': name,
                    'url': url,
                    'status': 'SUCCESS',
                    'words': word_count,
                    'time': duration,
                    'browser_profile': result.get('browser_profile', 'N/A'),
                    'techniques': result.get('bypass_techniques_used', [])
                })
                
            else:
                print(f"⚠️  FALHA: Conteúdo vazio ou inválido")
                results.append({
                    'name': name,
                    'url': url,
                    'status': 'EMPTY_CONTENT',
                    'words': 0,
                    'time': duration,
                    'browser_profile': 'N/A',
                    'techniques': []
                })
                
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            error_msg = str(e)
            print(f"❌ ERRO: {error_msg}")
            print(f"⏱️  Tempo até falha: {duration:.2f}s")
            
            # Classificar o tipo de erro
            if '403' in error_msg or 'Forbidden' in error_msg:
                status = 'WAF_BLOCKED'
            elif '429' in error_msg or 'rate limit' in error_msg.lower():
                status = 'RATE_LIMITED'
            elif 'timeout' in error_msg.lower():
                status = 'TIMEOUT'
            else:
                status = 'OTHER_ERROR'
            
            results.append({
                'name': name,
                'url': url,
                'status': status,
                'words': 0,
                'time': duration,
                'browser_profile': 'N/A',
                'techniques': [],
                'error': error_msg
            })
    
    # Exibir resumo dos resultados
    print("\n" + "=" * 80)
    print("📊 RESUMO DOS RESULTADOS")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    total_count = len(results)
    success_rate = (success_count / total_count) * 100
    
    print(f"🎯 Taxa de Sucesso: {success_count}/{total_count} ({success_rate:.1f}%)")
    print(f"⏱️  Tempo Total: {sum(r['time'] for r in results):.2f}s")
    print(f"📝 Total de Palavras Extraídas: {sum(r['words'] for r in results):,}")
    
    print("\n📈 DETALHES POR TESTE:")
    for i, result in enumerate(results, 1):
        status_emoji = "✅" if result['status'] == 'SUCCESS' else "❌"
        print(f"{i}. {status_emoji} {result['name']}")
        print(f"   Status: {result['status']}")
        if result['status'] == 'SUCCESS':
            print(f"   Palavras: {result['words']:,}")
            print(f"   Navegador: {result.get('browser_profile', 'N/A')}")
        elif 'error' in result:
            print(f"   Erro: {result['error'][:100]}...")
        print(f"   Tempo: {result['time']:.2f}s")
        print()
    
    # Análise de eficácia das técnicas
    print("🔧 ANÁLISE DAS TÉCNICAS DE CONTORNO:")
    
    if success_count > 0:
        print("✅ Técnicas que funcionaram:")
        successful_techniques = set()
        for result in results:
            if result['status'] == 'SUCCESS':
                successful_techniques.update(result.get('techniques', []))
        
        for technique in successful_techniques:
            print(f"   • {technique}")
    else:
        print("❌ Nenhuma técnica foi bem-sucedida nos testes")
    
    # Recomendações
    print("\n💡 RECOMENDAÇÕES:")
    
    if success_rate >= 60:
        print("🎉 Excelente! O sistema está funcionando bem.")
        print("   As melhorias implementadas estão sendo eficazes.")
    elif success_rate >= 40:
        print("⚠️  Resultado moderado. Considere:")
        print("   • Implementar rotação de proxies")
        print("   • Adicionar solução de CAPTCHA")
        print("   • Usar Selenium para sites mais complexos")
    else:
        print("🚨 Baixa taxa de sucesso. Considere:")
        print("   • Implementar proxy rotation premium")
        print("   • Usar serviços de scraping dedicados")
        print("   • Implementar browser automation (Selenium/Playwright)")
        print("   • Integrar serviços de solução de CAPTCHA")
    
    print("\n" + "=" * 80)
    print("🏁 TESTE CONCLUÍDO")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    print("Iniciando teste avançado de contorno de WAF...")
    results = test_advanced_waf_bypass()
    
    # Salvar resultados em arquivo
    import json
    with open('waf_bypass_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Resultados salvos em: waf_bypass_test_results.json") 