# TriageOps Webhook — Dağıtım

TriageOps webhook servisini konteyner olarak çalıştırma rehberi: yerel
(docker-compose) ve Kubernetes (pod'lar).

## Akış

```
Pipeline başarısız ─► Azure DevOps Service Hook ─HTTPS POST─► Ingress(/hook) ─► Service ─► Pod(uvicorn)
                                                                                              │
                                                          timeline→log→analiz (yerel LLM) ───┘
                                                                                              │
                                                            Build'e attachment + 'ai-analyzed' tag
```

---

## 1) İmajı oluştur ve push et

```bash
docker build -t ghcr.io/alperenck/triageops:latest .
docker push ghcr.io/alperenck/triageops:latest
```

`deploy/k8s/deployment.yaml` içindeki `image:` değerini kendi registry'nize göre güncelleyin.

## 2) Yerel deneme (docker-compose)

```bash
cp .env.example .env        # değerleri doldur
docker compose up --build
curl http://localhost:8080/health     # {"status":"ok"}
```

> Service Hook'lar **HTTPS** ister. Yerel testte servisin önüne `ngrok http 8080`
> gibi bir tünel veya TLS sonlandıran reverse proxy koyun.

## 3) Kubernetes'e dağıt (pod'lar)

**a. Namespace + Secret** (sırrı dosyaya yazmadan, `.env`'den):

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl -n triageops create secret generic triageops-secrets --from-env-file=.env
```

**b. Geri kalan kaynaklar** (Deployment + Service + Ingress):

```bash
kubectl apply -k deploy/k8s
kubectl -n triageops rollout status deploy/triageops-webhook
kubectl -n triageops get pods
```

**c. Erişimi doğrula:**

```bash
# Küme içinden hızlı kontrol:
kubectl -n triageops port-forward svc/triageops-webhook 8080:80
curl http://localhost:8080/health
```

Dışarıdan erişim `ingress.yaml`'daki host (`triageops.sirket.local`) + TLS
üzerinden olur. cert-manager kullanıyorsanız `cluster-issuer` annotation'ını açın;
aksi halde `triageops-tls` adında bir TLS secret'ı kendiniz sağlayın.

## 4) Azure DevOps Service Hook aboneliği

Project Settings → **Service Hooks** → **Web Hooks**:

| Alan | Değer |
|---|---|
| Trigger | **A build completed** veya **Run state changed** |
| Status / Result | **Failed** |
| **Resource details to send** | **All** ← önemli, yoksa payload eksik gelir |
| URL | `https://triageops.sirket.local/hook?token=<WEBHOOK_SECRET>` |

veya API ile:

```bash
curl -u :$AZDO_PAT -X POST \
  "$AZDO_BASE_URL/_apis/hooks/subscriptions?api-version=7.1" \
  -H "Content-Type: application/json" -d '{
    "publisherId":"tfs","eventType":"build.complete",
    "consumerId":"webHooks","consumerActionId":"httpRequest",
    "publisherInputs":{"buildStatus":"Failed","projectId":"<PROJECT_GUID>"},
    "consumerInputs":{"url":"https://triageops.sirket.local/hook?token=<WEBHOOK_SECRET>"}
  }'
```

## 5) Uçtan uca test

- Service Hooks ekranındaki **Test** butonu örnek payload gönderir → pod loglarında
  `analiz baslatiliyor` görünmeli.
- Bilerek bozulan bir pipeline çalıştır → build'in **Attachments** kısmında
  TriageOps raporu ve **`ai-analyzed`** tag'i belirir.

## Notlar

- **Ağ:** Pod'lar hem Azure DevOps Server'a hem de yerel LLM endpoint'ine
  (`LLM_BASE_URL`) erişebilmeli. On-prem'de NetworkPolicy/firewall'a dikkat.
- **Yerel LLM:** Ayrı bir Deployment/Service (örn. Ollama) olarak kümede
  çalışıyorsa `LLM_BASE_URL`'i küme-içi DNS ile verin
  (`http://ollama.triageops.svc.cluster.local:11434/v1`).
- **Güvenlik:** Pod root değil (uid 10001), readOnlyRootFilesystem, tüm
  capability'ler düşürülmüş. `WEBHOOK_SECRET` mutlaka kullanın.
