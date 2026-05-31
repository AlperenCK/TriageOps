# TriageOps

Azure DevOps Pipeline hatalarini otomatik triyaj eden bir aractir. Bir build
basarisiz oldugunda devreye girer, hatanin kaynagini bulur ve somut bir cozum
onerisi uretir. Analiz islemini kendi altyapinizda calisan bir yerel LLM ile
yapar; veriler disari cikmaz.

> Pipeline failure triage, otomatik.

## Proje Ozeti

CI/CD pipeline'lari basarisiz oldugunda, sorunun nerede oldugunu bulmak icin
genelde uzun loglari elle taramak gerekir. TriageOps bu adimi otomatiklestirir:

- Basarisiz build'in timeline'ini cekerek **tam olarak hangi task'in**
  basarisiz oldugunu tespit eder.
- Sadece o task'in logunu okur (tum loglari degil), boylece hem dogru yere
  odaklanir hem de LLM'e gonderilen baglam kucuk kalir.
- Gerekirse build'e dahil commit'leri ve yayinlanan artifact'leri inceler.
- Kok neden ve adim adim cozum onerisini Turkce bir rapor olarak uretir.

Microsoft'un resmi `azure-devops-mcp` sunucusunda bulunmayan "basarisiz task'i
izole etme" yetenegi bu projenin cekirdek farkidir.

### Ozellikler

- Uc farkli entegrasyon yolu: pipeline ici adim, webhook ve MCP sunucusu.
- Yerel LLM destegi (Ollama, vLLM, LM Studio, llama.cpp gibi OpenAI uyumlu
  endpoint'ler). Bulut bir LLM saglayicisina ihtiyac yoktur.
- Azure DevOps hem bulut (Services) hem de on-prem (Server / TFS) destekler.
- Docker imaji ve Kubernetes manifest'leri ile hazir dagitim (`deploy/`).

## Mimari

```
Azure DevOps
  |
  |  (1) Pipeline YAML adimi (failed())   ya da   (2) Service Hook / Webhook
  v
TriageOps (CLI / Webhook)
  |
  |  tool-calling dongusu
  v
Orchestrator ---> Yerel LLM (Ollama / vLLM / ...)
  |
  |  ADO REST katmani (timeline -> log -> changes -> artifacts)
  v
Build Summary'ye rapor
```

Ucuncu kullanim olarak MCP sunucusu (`triageops.mcp_server.server`) tek basina
herhangi bir MCP uyumlu istemciye baglanip interaktif de kullanilabilir.

## Kurulum

```bash
pip install -e ".[dev]"
cp .env.example .env   # degerleri doldurun
```

Yapilandirma tamamen ortam degiskenleri (veya `.env`) uzerinden yapilir;
tum secenekler icin `.env.example` dosyasina bakin.

### Yerel LLM

OpenAI uyumlu ve tool-calling (function calling) destekli bir endpoint gerekir.
Onerilen modeller: `qwen2.5-coder`, `llama3.3`, `mistral`, `deepseek-coder`.
Ornek (Ollama):

```bash
ollama pull qwen2.5-coder:14b
ollama serve            # http://localhost:11434/v1
```

### Azure DevOps On-Prem

Tek fark `AZDO_BASE_URL`'in koleksiyon URL'i olmasidir, ornegin
`https://tfs.sirket.local/DefaultCollection`. Gerekirse `AZDO_API_VERSION`
degerini sunucu surumunuze gore dusurun (2022 icin 7.0, 2020 icin 6.0,
2019 icin 5.0). Self-signed sertifika kullaniyorsaniz `AZDO_VERIFY_SSL=false`
yapin.

## Kullanim

### 1. Pipeline YAML adimi (basarisizlikta otomatik)

`azure-pipelines/analyze-on-failure.yml` sablonunu kendi pipeline'iniza ekleyin:

```yaml
steps:
  - template: azure-pipelines/analyze-on-failure.yml
    parameters:
      llmBaseUrl: 'http://llm-host:11434/v1'
      llmModel: 'qwen2.5-coder:14b'
      apiVersion: '7.0'   # on-prem surumunuze gore
```

Job ayarinda "Allow scripts to access the OAuth token" acik olmalidir
(System.AccessToken gerekir). Sonuc build'in Summary sekmesine yazilir.

### 2. Service Hook / Webhook (pipeline'a dokunmadan otomatik)

```bash
uvicorn triageops.triggers.webhook:app --host 0.0.0.0 --port 8080
```

Project Settings altinda Service Hooks ile bir Web Hooks aboneligi olusturun:
`build.complete` (buildStatus=Failed) veya `run-state-changed-event`
(runResultId=Failed) olayini servisin `/hook` adresine yonlendirin. Rapor
build'e attachment olarak eklenir ve build'e `ai-analyzed` etiketi atanir.

Konteyner ve Kubernetes ile dagitim icin `deploy/README.md` dosyasina bakin.

### 3. MCP sunucusu (interaktif)

```bash
python -m triageops.mcp_server.server                                   # stdio
MCP_TRANSPORT=streamable-http python -m triageops.mcp_server.server     # HTTP
```

MCP istemci yapilandirmasi ornegi:

```json
{ "mcpServers": { "triageops": {
  "command": "python", "args": ["-m", "triageops.mcp_server.server"],
  "env": { "AZDO_BASE_URL": "https://tfs.sirket.local/DefaultCollection",
           "AZDO_PROJECT": "MyProject", "AZDO_PAT": "..." } } } }
```

Sunulan MCP araclari: `list_failed_builds`, `get_build`,
`get_failed_timeline_records`, `get_task_log`, `get_build_changes`,
`list_artifacts`, `add_build_tag`.

### CLI

```bash
triageops analyze --build-id 12345                  # raporu ekrana bas
triageops analyze --build-id 12345 --in-pipeline    # Build Summary'ye yaz
triageops analyze --build-id 12345 -o rapor.md      # dosyaya yaz
```

## Test

```bash
pytest
```

## Guvenlik Notlari

- Uretimde PAT yerine Entra ID OAuth tercih edin; eski Azure DevOps OAuth
  2026'da kaldiriliyor.
- PAT'i en az yetkiyle olusturun: log okumak icin Build (Read), geri yazma
  islemleri icin ilgili ek kapsamlar.
- Webhook kullaniyorsaniz `WEBHOOK_SECRET` belirleyin ve servisi yalnizca
  HTTPS uzerinden yayinlayin.

## Proje Yapisi

```
src/triageops/
  ado/          Azure DevOps REST katmani (client, builds, writeback)
  agent/        orchestrator, prompts, tool semalari
  llm/          yerel LLM istemcisi (OpenAI uyumlu)
  mcp_server/   FastMCP sunucusu
  triggers/     CLI ve webhook
  config.py     ortam degiskeni tabanli ayarlar
  report.py     markdown rapor uretimi
azure-pipelines/  pipeline adim sablonu
deploy/           Docker ve Kubernetes dagitimi
tests/            birim testler
```

## Lisans

MIT. Bkz. [LICENSE](LICENSE).
