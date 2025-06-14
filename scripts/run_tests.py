#!/usr/bin/env python3
"""
Script para executar testes e verificações de qualidade do código
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import time
from typing import List, Dict, Any

# Adicionar o diretório raiz ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Classe para executar testes e verificações de qualidade"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict[str, Any] = {}
    
    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """Executa um comando e retorna o resultado"""
        print(f"\n{'='*60}")
        print(f"Executando: {description}")
        print(f"Comando: {' '.join(command)}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            duration = time.time() - start_time
            
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            success = result.returncode == 0
            
            result_data = {
                'success': success,
                'returncode': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            status = "✅ SUCESSO" if success else "❌ FALHOU"
            print(f"\nStatus: {status} (duração: {duration:.2f}s)")
            
            return result_data
            
        except subprocess.TimeoutExpired:
            print("❌ TIMEOUT - Comando excedeu 5 minutos")
            return {
                'success': False,
                'returncode': -1,
                'duration': time.time() - start_time,
                'stdout': '',
                'stderr': 'Timeout expired'
            }
        except Exception as e:
            print(f"❌ ERRO: {str(e)}")
            return {
                'success': False,
                'returncode': -1,
                'duration': time.time() - start_time,
                'stdout': '',
                'stderr': str(e)
            }
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Executa testes unitários"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'unit',
            '--tb=short',
            '-v'
        ]
        return self.run_command(command, "Testes Unitários")
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Executa testes de integração"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'integration',
            '--tb=short',
            '-v'
        ]
        return self.run_command(command, "Testes de Integração")
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Executa testes de segurança"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'security',
            '--tb=short',
            '-v'
        ]
        return self.run_command(command, "Testes de Segurança")
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Executa testes de performance"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'performance',
            '--tb=short',
            '-v',
            '--benchmark-only'
        ]
        return self.run_command(command, "Testes de Performance")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '--cov=utils',
            '--cov=pages',
            '--cov-report=term-missing',
            '--cov-report=html',
            '--tb=short',
            '-v'
        ]
        return self.run_command(command, "Todos os Testes com Cobertura")
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """Executa testes de smoke (básicos)"""
        command = [
            sys.executable, '-m', 'pytest',
            'tests/',
            '-m', 'smoke',
            '--tb=line',
            '-x'  # Para na primeira falha
        ]
        return self.run_command(command, "Testes de Smoke")
    
    def check_code_style(self) -> Dict[str, Any]:
        """Verifica estilo do código com flake8"""
        command = [
            sys.executable, '-m', 'flake8',
            'utils/',
            'pages/',
            'tests/',
            '--max-line-length=100',
            '--ignore=E203,W503,E501',
            '--statistics'
        ]
        return self.run_command(command, "Verificação de Estilo (flake8)")
    
    def check_security_vulnerabilities(self) -> Dict[str, Any]:
        """Verifica vulnerabilidades de segurança com bandit"""
        command = [
            sys.executable, '-m', 'bandit',
            '-r', 'utils/', 'pages/',
            '-f', 'json',
            '-o', 'security_report.json'
        ]
        return self.run_command(command, "Verificação de Segurança (bandit)")
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Verifica vulnerabilidades nas dependências"""
        command = [
            sys.executable, '-m', 'pip',
            'audit'
        ]
        return self.run_command(command, "Auditoria de Dependências")
    
    def generate_coverage_report(self) -> Dict[str, Any]:
        """Gera relatório de cobertura"""
        command = [
            sys.executable, '-m', 'coverage',
            'html'
        ]
        return self.run_command(command, "Geração de Relatório de Cobertura")
    
    def run_type_checking(self) -> Dict[str, Any]:
        """Executa verificação de tipos com mypy"""
        command = [
            sys.executable, '-m', 'mypy',
            'utils/',
            'pages/',
            '--ignore-missing-imports',
            '--no-strict-optional'
        ]
        return self.run_command(command, "Verificação de Tipos (mypy)")
    
    def print_summary(self):
        """Imprime resumo dos resultados"""
        print(f"\n{'='*80}")
        print("RESUMO DOS RESULTADOS")
        print(f"{'='*80}")
        
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results.values() if result['success'])
        failed_tests = total_tests - successful_tests
        
        print(f"Total de verificações: {total_tests}")
        print(f"Sucessos: {successful_tests} ✅")
        print(f"Falhas: {failed_tests} ❌")
        print(f"Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
        
        print(f"\n{'Verificação':<30} {'Status':<10} {'Duração':<10}")
        print("-" * 60)
        
        for name, result in self.results.items():
            status = "✅ OK" if result['success'] else "❌ FALHA"
            duration = f"{result['duration']:.2f}s"
            print(f"{name:<30} {status:<10} {duration:<10}")
        
        if failed_tests > 0:
            print(f"\n❌ {failed_tests} verificação(ões) falharam. Verifique os logs acima.")
            return False
        else:
            print(f"\n✅ Todas as verificações passaram com sucesso!")
            return True

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Executa testes e verificações de qualidade")
    parser.add_argument('--type', choices=[
        'unit', 'integration', 'security', 'performance', 'all', 'smoke',
        'style', 'security-scan', 'dependencies', 'coverage', 'types', 'quick'
    ], default='quick', help='Tipo de teste a executar')
    parser.add_argument('--verbose', '-v', action='store_true', help='Saída verbosa')
    parser.add_argument('--fail-fast', '-x', action='store_true', help='Para na primeira falha')
    
    args = parser.parse_args()
    
    # Verificar se estamos no diretório correto
    if not (project_root / 'app.py').exists():
        print("❌ Erro: Execute este script a partir do diretório raiz do projeto")
        sys.exit(1)
    
    runner = TestRunner(project_root)
    
    print(f"🚀 Iniciando verificações de qualidade...")
    print(f"📁 Diretório do projeto: {project_root}")
    print(f"🔧 Tipo de verificação: {args.type}")
    
    # Executar verificações baseadas no tipo
    if args.type == 'unit':
        runner.results['unit_tests'] = runner.run_unit_tests()
    
    elif args.type == 'integration':
        runner.results['integration_tests'] = runner.run_integration_tests()
    
    elif args.type == 'security':
        runner.results['security_tests'] = runner.run_security_tests()
    
    elif args.type == 'performance':
        runner.results['performance_tests'] = runner.run_performance_tests()
    
    elif args.type == 'smoke':
        runner.results['smoke_tests'] = runner.run_smoke_tests()
    
    elif args.type == 'style':
        runner.results['code_style'] = runner.check_code_style()
    
    elif args.type == 'security-scan':
        runner.results['security_scan'] = runner.check_security_vulnerabilities()
    
    elif args.type == 'dependencies':
        runner.results['dependencies'] = runner.check_dependencies()
    
    elif args.type == 'coverage':
        runner.results['all_tests'] = runner.run_all_tests()
        runner.results['coverage_report'] = runner.generate_coverage_report()
    
    elif args.type == 'types':
        runner.results['type_checking'] = runner.run_type_checking()
    
    elif args.type == 'quick':
        # Verificações rápidas essenciais
        runner.results['smoke_tests'] = runner.run_smoke_tests()
        if runner.results['smoke_tests']['success'] or not args.fail_fast:
            runner.results['unit_tests'] = runner.run_unit_tests()
        if (runner.results.get('unit_tests', {}).get('success', True) or not args.fail_fast):
            runner.results['security_tests'] = runner.run_security_tests()
    
    elif args.type == 'all':
        # Todas as verificações
        runner.results['smoke_tests'] = runner.run_smoke_tests()
        if runner.results['smoke_tests']['success'] or not args.fail_fast:
            runner.results['unit_tests'] = runner.run_unit_tests()
        if (runner.results.get('unit_tests', {}).get('success', True) or not args.fail_fast):
            runner.results['integration_tests'] = runner.run_integration_tests()
        if (runner.results.get('integration_tests', {}).get('success', True) or not args.fail_fast):
            runner.results['security_tests'] = runner.run_security_tests()
        if (runner.results.get('security_tests', {}).get('success', True) or not args.fail_fast):
            runner.results['performance_tests'] = runner.run_performance_tests()
        
        # Verificações de qualidade
        runner.results['code_style'] = runner.check_code_style()
        runner.results['type_checking'] = runner.run_type_checking()
        runner.results['security_scan'] = runner.check_security_vulnerabilities()
        runner.results['dependencies'] = runner.check_dependencies()
        
        # Gerar relatório de cobertura
        runner.results['coverage_report'] = runner.generate_coverage_report()
    
    # Imprimir resumo
    success = runner.print_summary()
    
    # Sair com código apropriado
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()