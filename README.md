# TriageOps

Azure DevOps Pipeline hatalarını otomatik triyaj eden bir araçtır. Bir build
başarısız olduğunda devreye girer, hatanın kaynağını bulur ve somut bir çözüm
önerisi üretir. Analiz işlemini kendi altyapınızda çalışan bir yerel LLM ile
yapar; veriler dışarı çıkmaz.

> Pipeline failure triage, otomatik.

## Proje Özeti

CI/CD pipeline'ları başarısız olduğunda, sorunun nerede olduğunu bulmak için
genelde uzun logları elle taramak gerekir. TriageOps bu adımı otomatikleştirir:

- Başarısız build'in timeline'ını çekerek **tam olarak hangi task'ın**
  başarısız olduğunu tespit eder.
- Sadece o task'ın logunu okur (tüm logları değil), böylece hem doğru yere
  odaklanır hem de LLM'e gönderilen bağlam küçük kalır.
- Gerekirse build'e dahil commit'leri ve yayınlanan artifact'leri inceler.
- Kök neden ve adım adım çözüm önerisini Türkçe bir rapor olarak üretir.

Microsoft'un resmi `azure-devops-mcp` sunucusunda bulunmayan "başarısız task'ı
izole etme" yeteneği bu projenin çekirdek farkıdır.

### Özellikler

- Üç farklı entegrasyon yolu: pipeline içi adım, webhook ve MCP sunucusu.
- Yerel LLM desteği (Ollama, vLLM, LM Studio, llama.cpp gibi OpenAI uyumlu
  endpoint'ler). Bulut bir LLM sağlayıcısına ihtiyaç yoktur.
- Azure DevOps hem bulut (Services) hem de on-prem (Server / TFS) destekler.
- Docker imajı ve Kubernetes manifest'leri ile hazır dağıtım (`deploy/`).

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

Üçüncü kullanım olarak MCP sunucusu (`triageops.mcp_server.server`) tek başına
herhangi bir MCP uyumlu istemciye bağlanıp interaktif de kullanılabilir.

## Kurulum

```bash
pip install -e ".[dev]"
cp .env.example .env   # degerleri doldurun
```

Yapılandırma tamamen ortam değişkenleri (veya `.env`) üzerinden yapılır;
tüm seçenekler için `.env.example` dosyasına bakın.

### Yerel LLM

OpenAI uyumlu ve tool-calling (function calling) destekli bir endpoint gerekir.
Önerilen modeller: `qwen2.5-coder`, `llama3.3`, `mistral`, `deepseek-coder`.
Örnek (Ollama):

```bash
ollama pull qwen2.5-coder:14b
ollama serve            # http://localhost:11434/v1
```

### Azure DevOps On-Prem

Tek fark `AZDO_BASE_URL`'in koleksiyon URL'i olmasıdır, örneğin
`https://tfs.sirket.local/DefaultCollection`. Gerekirse `AZDO_API_VERSION`
değerini sunucu sürümünüze göre düşürün (2022 için 7.0, 2020 için 6.0,
2019 için 5.0). Self-signed sertifika kullanıyorsanız `AZDO_VERIFY_SSL=false`
yapın.

## Kullanım

### 1. Pipeline YAML adımı (başarısızlıkta otomatik)

`azure-pipelines/analyze-on-failure.yml` şablonunu kendi pipeline'ınıza ekleyin:

```yaml
steps:
  - template: azure-pipelines/analyze-on-failure.yml
    parameters:
      llmBaseUrl: 'http://llm-host:11434/v1'
      llmModel: 'qwen2.5-coder:14b'
      apiVersion: '7.0'   # on-prem surumunuze gore
```

Job ayarında "Allow scripts to access the OAuth token" açık olmalıdır
(System.AccessToken gerekir). Sonuç build'in Summary sekmesine yazılır.

### 2. Service Hook / Webhook (pipeline'a dokunmadan otomatik)

```bash
uvicorn triageops.triggers.webhook:app --host 0.0.0.0 --port 8080
```

Project Settings altında Service Hooks ile bir Web Hooks aboneliği oluşturun:
`build.complete` (buildStatus=Failed) veya `run-state-changed-event`
(runResultId=Failed) olayını servisin `/hook` adresine yönlendirin. Rapor
build'e attachment olarak eklenir ve build'e `ai-analyzed` etiketi atanır.

Konteyner ve Kubernetes ile dağıtım için `deploy/README.md` dosyasına bakın.

### 3. MCP sunucusu (interaktif)

```bash
python -m triageops.mcp_server.server                                   # stdio
MCP_TRANSPORT=streamable-http python -m triageops.mcp_server.server     # HTTP
```

MCP istemci yapılandırması örneği:

```json
{ "mcpServers": { "triageops": {
  "command": "python", "args": ["-m", "triageops.mcp_server.server"],
  "env": { "AZDO_BASE_URL": "https://tfs.sirket.local/DefaultCollection",
           "AZDO_PROJECT": "MyProject", "AZDO_PAT": "..." } } } }
```

Sunulan MCP araçları: `list_failed_builds`, `get_build`,
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

## Güvenlik Notları

- Üretimde PAT yerine Entra ID OAuth tercih edin; eski Azure DevOps OAuth
  2026'da kaldırılıyor.
- PAT'i en az yetkiyle oluşturun: log okumak için Build (Read), geri yazma
  işlemleri için ilgili ek kapsamlar.
- Webhook kullanıyorsanız `WEBHOOK_SECRET` belirleyin ve servisi yalnızca
  HTTPS üzerinden yayınlayın.

## Proje Yapısı

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
