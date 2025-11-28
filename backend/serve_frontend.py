#!/usr/bin/env python3
"""
Servidor frontend local para CNC Telemetry Windows.
Serve os arquivos buildados do frontend em localhost:3000
"""

import os
import sys
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import argparse

# Adicionar backend ao path para imports
sys.path.insert(0, os.path.dirname(__file__))

from app.logging_config import get_logger

logger = get_logger("frontend_server")


class FrontendHandler(SimpleHTTPRequestHandler):
    """Handler customizado para servir frontend com CORS e logging."""
    
    def __init__(self, *args, frontend_dir=None, **kwargs):
        self.frontend_dir = frontend_dir
        super().__init__(*args, directory=frontend_dir, **kwargs)
    
    def end_headers(self):
        """Adicionar headers CORS."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def do_GET(self):
        """Tratar requisições GET com logging."""
        client_ip = self.client_address[0]
        path = urlparse(self.path).path
        
        logger.info("frontend_request", client_ip=client_ip, path=path)
        
        # Se for raiz, servir index.html
        if path == '/':
            path = '/index.html'
        
        try:
            # Tentar servir arquivo
            super().do_GET()
        except FileNotFoundError:
            logger.warning("file_not_found", path=path)
            self.send_error(404, f"File not found: {path}")
        except Exception as e:
            logger.error("serve_error", path=path, error=str(e))
            self.send_error(500, f"Internal server error: {e}")
    
    def log_message(self, format, *args):
        """Sobrescrever para usar nosso logger."""
        logger.info("http_access", message=format % args)


def find_frontend_dir():
    """Encontrar diretório do frontend buildado."""
    current_dir = os.path.dirname(__file__)
    
    # Possíveis locais do frontend buildado
    possible_paths = [
        os.path.join(current_dir, '..', 'frontend', 'dist'),
        os.path.join(current_dir, '..', 'frontend', 'build'),
        os.path.join(current_dir, '..', 'frontend'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, 'index.html')):
            return os.path.abspath(path)
    
    return None


def main():
    """Função principal do servidor frontend."""
    parser = argparse.ArgumentParser(description='Servidor Frontend CNC Telemetry')
    parser.add_argument('--host', default='localhost', help='Host para bind (default: localhost)')
    parser.add_argument('--port', type=int, default=3000, help='Porta para bind (default: 3000)')
    parser.add_argument('--frontend-dir', help='Diretório do frontend (auto-detect se não especificado)')
    
    args = parser.parse_args()
    
    # Encontrar diretório do frontend
    if args.frontend_dir:
        frontend_dir = os.path.abspath(args.frontend_dir)
    else:
        frontend_dir = find_frontend_dir()
    
    if not frontend_dir:
        logger.error("frontend_not_found", 
                    searched_paths=possible_paths)
        print("ERRO: Diretório do frontend não encontrado!")
        print("Execute 'npm run build' no frontend primeiro.")
        sys.exit(1)
    
    if not os.path.exists(os.path.join(frontend_dir, 'index.html')):
        logger.error("index_not_found", frontend_dir=frontend_dir)
        print("ERRO: index.html não encontrado em", frontend_dir)
        print("Execute 'npm run build' no frontend primeiro.")
        sys.exit(1)
    
    logger.info("frontend_server_starting", 
                host=args.host, 
                port=args.port, 
                frontend_dir=frontend_dir)
    
    print(f"=== CNC Telemetry - Frontend Server ===")
    print(f"Servindo frontend de: {frontend_dir}")
    print(f"Acesse: http://{args.host}:{args.port}")
    print(f"Pressione CTRL+C para parar")
    print()
    
    # Criar handler com frontend_dir
    def handler_factory(*args, **kwargs):
        return FrontendHandler(*args, frontend_dir=frontend_dir, **kwargs)
    
    # Iniciar servidor
    try:
        server = HTTPServer((args.host, args.port), handler_factory)
        logger.info("frontend_server_started", 
                    server_address=server.server_address)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("frontend_server_stopped", reason="keyboard_interrupt")
        print("\nServidor frontend parado.")
    except OSError as e:
        logger.error("server_error", error=str(e))
        print(f"ERRO: Não foi possível iniciar servidor: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        print(f"ERRO inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
