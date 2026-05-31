# Katki Rehberi

Tesekkurler! Bu projeye katki yapmak isterseniz asagidaki adimlari izleyin.

## Gelistirme ortami

```bash
git clone https://github.com/AlperenCK/TriageOps.git
cd TriageOps
pip install -e ".[dev]"
```

## Testler

Degisiklik gondermeden once testlerin gectiginden emin olun:

```bash
pytest
```

Yeni bir ozellik eklerken ilgili testi de ekleyin. Testler `tests/` altinda,
ornek veriler `tests/fixtures/` icinde tutulur. Disari cikan baglantilar
(Azure DevOps REST, LLM) testlerde mock'lanir; gercek bir servise ihtiyac
olmamalidir.

## Kod stili

- Python 3.10+ ve tip ipuclari kullanin.
- Yorumlar ve docstring'ler Turkce yazilir (mevcut kodla tutarli olsun).
- Fonksiyon ve degisken adlari acik ve aciklayici olsun.

## Pull request

1. Bir konu dalinda (feature branch) calisin.
2. Commit mesajlarini acik ve aciklayici yazin.
3. PR acmadan once `pytest` yesil olsun.
4. PR aciklamasinda ne degistirdiginizi ve neden oldugunu ozetleyin.

## Hata bildirimi

Hata bildirirken mumkunse su bilgileri ekleyin: Azure DevOps surumu
(bulut / on-prem), kullanilan yerel LLM ve model, hatayi ureten adimlar
ve aldiginiz cikti/log.
