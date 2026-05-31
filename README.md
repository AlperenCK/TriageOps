# TriageOps — Azure DevOps Pipeline Hata Triyaj Ajanı

> _Pipeline failure triage, otomatik._

Azure DevOps Pipeline'larına entegre olan, **pipeline hatalarını otomatik analiz
edip kök neden + somut çözüm önerisi üreten**, MCP tabanlı ve **yerel LLM** ile
çalışan bir DevOps triyaj ajanı.

> **Azure DevOps On-Prem (Azure DevOps Server / TFS) desteklenir.** Tek fark
> `AZDO_BASE_URL`'in koleksiyon URL'i olması (örn.
> `https://tfs.sirket.local/DefaultCollection`) ve gerekirse `AZDO_API_VERSION`'ın
> sunucu sürümüne göre düşürülmesidir (2022→7.0, 2020→6.0, 2019→5.0).

## Neden Farklı?

Çekirdek değer: Microsoft'un resmi `azure-devops-mcp` server'ında bile olmayan
**"hatalı task'ı izole etme"** yeteneği — build timeline'ı çekip yalnızca
`result==failed` olan task'ın log'unu alır. Bu hem teşhis doğruluğunu artırır hem
de LLM context'ini küçük tutar.

## Mimari

```
Azure DevOps ──(1) YAML failed() / (2) Service Hook)── ► CLI / Webhook
                                                            │
                                              Orchestrator (tool-calling)
                                                  │              │
                                          Yerel LLM        ADO REST katmanı
                                       (Ollama/vLLM/...)   (timeline→log→changes)
                                                  │
                                          Build Summary'ye rapor
```

`(3)` MCP server (`triageops.mcp_server.server`) tek başına herhangi bir MCP
uyumlu istemciye (IDE/Desktop) bağlanıp **interaktif** de kullanılabilir.

## Kurulum

```bash
pip install -e ".[dev]"
cp .env.example .env   # değerleri doldurun
```

### Yerel LLM
OpenAI uyumlu, **tool-calling destekli** bir endpoint gerekir. Önerilen modeller:
`qwen2.5-coder`, `llama3.3`, `mistral`, `deepseek-coder`. Örn. Ollama:

```bash
ollama pull qwen2.5-coder:14b
ollama serve            # http://localhost:11434/v1
```

## Üç Kullanım Yolu

### 1) Pipeline YAML adımı (otomatik, başarısızlıkta)
`azure-pipelines/analyze-on-failure.yml` şablonunu pipeline'ınıza ekleyin:

```yaml
steps:
  - template: azure-pipelines/analyze-on-failure.yml
    parameters:
      llmBaseUrl: 'http://llm-host:11434/v1'
      llmModel: 'qwen2.5-coder:14b'
      apiVersion: '7.0'   # on-prem sürümünüze göre
```

> Job'da **"Allow scripts to access the OAuth token"** açık olmalı (System.AccessToken).
> Sonuç **Build Summary** sekmesine yazılır.

### 2) Service Hook / Webhook (otomatik, pipeline'a dokunmadan)
```bash
uvicorn triageops.triggers.webhook:app --host 0.0.0.0 --port 8080
```
Project Settings → Service Hooks → Web Hooks aboneliği oluşturun:
`build.complete` (buildStatus=Failed) **veya** `run-state-changed-event`
(runResultId=Failed) → URL: `https://<host>:8080/hook`. Rapor build'e attachment
olarak eklenir ve `ai-analyzed` tag'i atanır.

### 3) MCP server (interaktif, MCP uyumlu istemci / IDE)
```bash
python -m triageops.mcp_server.server          # stdio
MCP_TRANSPORT=streamable-http python -m triageops.mcp_server.server  # HTTP
```
MCP istemci config örneği:
```json
{ "mcpServers": { "triageops": {
  "command": "python", "args": ["-m", "triageops.mcp_server.server"],
  "env": { "AZDO_BASE_URL": "https://tfs.sirket.local/DefaultCollection",
           "AZDO_PROJECT": "MyProject", "AZDO_PAT": "..." } } } }
```

**Sunulan MCP araçları:** `list_failed_builds`, `get_build`,
`get_failed_timeline_records`, `get_task_log`, `get_build_changes`,
`list_artifacts` (test sonucu/coverage/build çıktısı artifact'leri), `add_build_tag`.

## CLI

```bash
triageops analyze --build-id 12345              # raporu stdout'a bas
triageops analyze --build-id 12345 --in-pipeline  # Build Summary'ye yaz
triageops analyze --build-id 12345 -o rapor.md
```

## Test

```bash
pytest
```

## Konfigürasyon
Tüm ayarlar `.env` / ortam değişkenleri (bkz. `.env.example`).

## Güvenlik Notları
- Üretimde PAT yerine **Entra ID OAuth** önerilir (eski ADO OAuth 2026'da kaldırılıyor).
- Self-signed sertifikalı on-prem için `AZDO_VERIFY_SSL=false`.
- PAT en az yetkiyle: Build (Read); geri yazma için ilgili scope'lar.
