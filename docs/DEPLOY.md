# Contabo VPS'e deploy (docker compose)

Servisler: `db` (postgres:18.6), `backend`, `frontend`, `caddy`; tek seferlik `init` (profile). Yalnızca caddy 80/443 açar. Caddy `.env` almaz.

## 1. Dosyaları kopyala
```bash
rsync -avz --delete \
  --exclude '.env' --exclude '.env.*' --exclude '.venv' --exclude '.git' \
  --exclude 'docs/sunumlar' --exclude '__pycache__' --exclude '.pytest_cache' \
  ./ KULLANICI@SUNUCU:/opt/smartschool/
```
(`--delete` sunucudaki `.env`'i silmez; hariç tutulan dosyalar korunur. Emin değilseniz `--delete`'i kaldırın.)

## 2. `.env`'i sunucuda elle oluştur
```bash
cd /opt/smartschool
cp .env.example .env && chmod 600 .env
nano .env   # tüm değerleri doldur
```
- `DATABASE_URL` ve `APP_DATABASE_URL` host'u `db` olmalı.
- `APP_DATABASE_URL` kullanıcısı `school_app`; parolası `init` sırasında role atanır.
- `POSTGRES_*` değerleri `DATABASE_URL` ile tutarlı olmalı (db volume'ü ilk açılışta bunlarla kurulur).
- DNS: `smartschoolassistant.com` ve `www` kayıtları sunucu IP'sine işaret etmeli.

## 3. Build ve başlatma
```bash
docker compose build
docker compose up -d db
docker compose ps          # db "healthy" olmalı
```

## 4. Init (yalnızca ilk kurulumda)
```bash
docker compose --profile init run --rm init
```
Sıra: `init_db.py` → `bootstrap_roles.py` → `enable_rls.py` → `seed_mock.py` (biri hata verirse durur).

> **UYARI: init yalnızca ilk kurulumda çalıştırılır; tekrar çalıştırmak veriyi siler.**
> `seed_mock.py` her çalışmada `TRUNCATE ... RESTART IDENTITY CASCADE` yapar. İlk üç betik yeniden çalıştırılabilir.
> Seed, demo kullanıcı parolalarını çıktıya yazar; init logunu saklamayın.

## 5. Uygulamayı başlat
```bash
docker compose up -d
docker compose ps
```

## Log
```bash
docker compose logs -f backend
docker compose logs -f frontend caddy
docker compose logs db
```

## Güncelleme
```bash
# yeni kodu rsync ile kopyala (1. adım), sonra:
docker compose build
docker compose up -d       # init ÇALIŞTIRILMAZ
docker compose logs -f --tail=100 backend
```
`.env` değiştiyse: `docker compose up -d --force-recreate`.
