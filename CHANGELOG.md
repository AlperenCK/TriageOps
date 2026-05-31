# Degisiklik Gunlugu

Bu projedeki onemli degisiklikler bu dosyada tutulur.
Bicim [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) temel alir.

## [0.1.0] - 2026-05-31

Ilk surum.

### Eklendi
- Azure DevOps REST katmani: basarisiz build listeleme, build detayi, timeline
  uzerinden basarisiz task tespiti, hedefli log okuma, commit ve artifact
  inceleme, build'e geri yazma (attachment, etiket, summary).
- FastMCP tabanli MCP sunucusu; yedi arac ile interaktif kullanim.
- Yerel LLM istemcisi (OpenAI uyumlu endpoint) ve tool-calling orchestrator.
- Uc tetikleme yolu: pipeline YAML adimi, FastAPI webhook ve MCP sunucusu.
- Azure DevOps on-prem (Server / TFS) destegi.
- Docker imaji, docker-compose ve Kubernetes manifest'leri.
- Birim testler ve ornek veri dosyalari.
