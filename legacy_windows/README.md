# Legacy Windows Components

## ⚠️ AVISO IMPORTANTE

Esta pasta contém componentes **LEGADO** do piloto Windows antigo.

**NÃO USAR em produção do CNC Telemetry Box v1.**

## Contexto

Estes arquivos foram utilizados no piloto original desenvolvido para ambiente Windows:
- Instalação local em notebooks
- Build de executáveis com PyInstaller
- Serviços Windows via NSSM
- Scripts de deploy manual

## O que está aqui

### Scripts de Instalação e Deploy
- `install_telemetry.ps1` - Script de instalação (esqueleto)
- `install_service_with_nssm.ps1` - Instalação como serviço Windows
- `start_telemetry.bat` - Start manual do backend
- `telemetry_diag.ps1` - Diagnóstico de problemas

### Scripts de Desenvolvimento
- `start_backend_demo.ps1` - Start backend para demo
- `start_frontend_demo.ps1` - Start frontend para demo
- `build_installer.ps1` - Build de instalador
- `test_exe.ps1` - Teste de executável

### Componentes PyInstaller
- `server_entry.py` - Entrypoint para build .exe
- `install_telemetry_online.ps1.bak` - Script de instalação online (backup)

### Field Kit (protótipos)
- `fieldkit/` - Scripts e protótipos iniciais

## Caminho Oficial

Para o **CNC Telemetry Box v1**, use apenas:
- `docker-compose.yml` (deploy oficial)
- `docs/DEPLOY_LINUX_DOCKER.md` (guia de instalação)
- `deploy/linux/cnc-telemetry-box.service` (systemd)

## Suporte

Estes arquivos são mantidos apenas para:
- ✅ Referência do piloto original
- ✅ Debugging de issues antigos
- ✅ Desenvolvimento em ambiente Windows (via Docker Desktop)
- ❌ **NÃO usar em produção**

---

**CNC Telemetry Box v1 = Linux + Docker + systemd**  
**Windows = apenas cliente/browser ou ambiente de dev**
